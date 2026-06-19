import math
from collections import deque

import cv2

from alert_engine import GREEN, YELLOW, RED

STATE_COLOR = {
    GREEN: (0, 200, 0),
    YELLOW: (0, 200, 255),
    RED: (0, 0, 255),
}

STATE_LABEL = {
    GREEN: "ALERTA: NORMAL",
    YELLOW: "ALERTA: SOMNOLENCIA LEVE",
    RED: "ALERTA: PELIGRO - MICROSUEÑO",
}


class Hud:
    def __init__(self, history_len=120):
        self._ear_history = deque(maxlen=history_len)
        self._perclos_history = deque(maxlen=history_len)

    def push(self, ear, perclos):
        self._ear_history.append(ear)
        self._perclos_history.append(perclos)

    def draw(self, frame, state, ear, mar, perclos, microsleep_count):
        h, w = frame.shape[:2]
        color = STATE_COLOR[state]

        if state == RED:
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), color, -1)
            cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)
            cv2.rectangle(frame, (0, 0), (w, h), color, 8)

        self._draw_gauge(frame, center=(80, 80), radius=55, perclos=perclos, color=color)
        self._draw_sparkline(frame, top_left=(160, 30), size=(220, 60),
                              values=self._ear_history, color=(255, 255, 255))

        cv2.rectangle(frame, (0, h - 70), (w, h), (20, 20, 20), -1)
        cv2.putText(frame, STATE_LABEL[state], (15, h - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA)
        cv2.putText(frame, f"EAR:{ear:.2f}  MAR:{mar:.2f}  PERCLOS:{perclos*100:.0f}%  "
                            f"Microsuenos:{microsleep_count}",
                    (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        return frame

    @staticmethod
    def _draw_gauge(frame, center, radius, perclos, color):
        cx, cy = center
        cv2.circle(frame, center, radius, (60, 60, 60), 6)
        start_angle = -90
        end_angle = start_angle + int(360 * min(perclos, 1.0))
        cv2.ellipse(frame, center, (radius, radius), 0, start_angle, end_angle, color, 8)
        cv2.putText(frame, f"{int(min(perclos,1.0)*100)}%", (cx - 22, cy + 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "FATIGA", (cx - 32, cy + radius + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    @staticmethod
    def _draw_sparkline(frame, top_left, size, values, color):
        x0, y0 = top_left
        w, h = size
        cv2.rectangle(frame, (x0, y0), (x0 + w, y0 + h), (40, 40, 40), -1)
        if len(values) < 2:
            return
        vmin, vmax = min(values), max(values)
        span = max(vmax - vmin, 1e-6)
        n = len(values)
        points = []
        for i, v in enumerate(values):
            x = x0 + int(i / (n - 1) * w)
            y = y0 + h - int((v - vmin) / span * h)
            points.append((x, y))
        for p1, p2 in zip(points, points[1:]):
            cv2.line(frame, p1, p2, color, 1, cv2.LINE_AA)
        cv2.putText(frame, "EAR (tiempo real)", (x0, y0 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
