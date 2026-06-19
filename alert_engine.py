GREEN = "GREEN"
YELLOW = "YELLOW"
RED = "RED"


class AlertEngine:
    """State machine with hysteresis: PERCLOS sets the baseline fatigue
    level, sustained eye closure or yawning escalates it to RED."""

    def __init__(self,
                 ear_threshold=0.21,
                 mar_threshold=0.6,
                 closed_frames_for_red=15,
                 yawn_frames_for_yellow=20,
                 recovery_frames=20,
                 perclos_yellow=0.15,
                 perclos_red=0.30):
        self.ear_threshold = ear_threshold
        self.mar_threshold = mar_threshold
        self.closed_frames_for_red = closed_frames_for_red
        self.yawn_frames_for_yellow = yawn_frames_for_yellow
        self.recovery_frames = recovery_frames
        self.perclos_yellow = perclos_yellow
        self.perclos_red = perclos_red

        self.state = GREEN
        self._closed_streak = 0
        self._yawn_streak = 0
        self._good_streak = 0
        self.microsleep_count = 0
        self._was_red = False

    def update(self, ear, mar, perclos):
        eyes_closed = ear < self.ear_threshold
        yawning = mar > self.mar_threshold

        self._closed_streak = self._closed_streak + 1 if eyes_closed else 0
        self._yawn_streak = self._yawn_streak + 1 if yawning else 0
        self._good_streak = 0 if (eyes_closed or yawning) else self._good_streak + 1

        target = GREEN
        if perclos >= self.perclos_red or self._closed_streak >= self.closed_frames_for_red:
            target = RED
        elif perclos >= self.perclos_yellow or self._yawn_streak >= self.yawn_frames_for_yellow:
            target = YELLOW

        if target == RED:
            if not self._was_red:
                self.microsleep_count += 1
            self._was_red = True
            self.state = RED
        elif target == YELLOW:
            self._was_red = False
            self.state = YELLOW
        else:
            self._was_red = False
            if self._good_streak >= self.recovery_frames:
                self.state = GREEN
            # else: keep previous state (hysteresis, avoids flicker back to GREEN)

        return self.state
