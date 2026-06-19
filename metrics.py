import math
from collections import deque

from landmarks import LEFT_EYE, RIGHT_EYE, MOUTH


def _dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def eye_aspect_ratio(points, eye_idx):
    p = [points[i] for i in eye_idx]
    vertical1 = _dist(p[1], p[5])
    vertical2 = _dist(p[2], p[4])
    horizontal = _dist(p[0], p[3])
    if horizontal == 0:
        return 0.0
    return (vertical1 + vertical2) / (2.0 * horizontal)


def mouth_aspect_ratio(points):
    p = [points[i] for i in MOUTH]
    vertical1 = _dist(p[2], p[3])
    vertical2 = _dist(p[6], p[7])
    horizontal = _dist(p[0], p[1])
    if horizontal == 0:
        return 0.0
    return (vertical1 + vertical2) / (2.0 * horizontal)


def average_ear(points):
    left = eye_aspect_ratio(points, LEFT_EYE)
    right = eye_aspect_ratio(points, RIGHT_EYE)
    return (left + right) / 2.0


class Perclos:
    def __init__(self, window_size=45, ear_threshold=0.21):
        self._window = deque(maxlen=window_size)
        self.ear_threshold = ear_threshold

    def update(self, ear):
        self._window.append(1 if ear < self.ear_threshold else 0)

    @property
    def value(self):
        if not self._window:
            return 0.0
        return sum(self._window) / len(self._window)
