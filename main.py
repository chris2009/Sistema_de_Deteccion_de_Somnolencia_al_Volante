import time

import cv2

from alert_engine import AlertEngine
from audio_voice import AlertSound
from hud_overlay import Hud
from landmarks import FaceLandmarkDetector
from metrics import Perclos, average_ear, mouth_aspect_ratio
from session_report import save_session_report


def main(camera_index=0):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir la camara web.")

    detector = FaceLandmarkDetector()
    perclos = Perclos(window_size=45, ear_threshold=0.21)
    engine = AlertEngine()
    sound = AlertSound()
    hud = Hud()

    start_time = time.time()
    timestamps, ear_log, perclos_log, state_log = [], [], [], []

    print("Presiona 'q' para salir.")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)

            points = detector.process(frame)
            if points is not None:
                ear = average_ear(points)
                mar = mouth_aspect_ratio(points)
                perclos.update(ear)
                state = engine.update(ear, mar, perclos.value)
                sound.notify(state)

                hud.push(ear, perclos.value)
                hud.draw(frame, state, ear, mar, perclos.value, engine.microsleep_count)

                t = time.time() - start_time
                timestamps.append(t)
                ear_log.append(ear)
                perclos_log.append(perclos.value)
                state_log.append(state)
            else:
                cv2.putText(frame, "Rostro no detectado", (15, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

            cv2.imshow("Deteccion de somnolencia - Lab 03", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()
        report_path = save_session_report(timestamps, ear_log, perclos_log, state_log,
                                            engine.microsleep_count)
        if report_path:
            print(f"Reporte de sesion guardado en: {report_path}")


if __name__ == "__main__":
    main()
