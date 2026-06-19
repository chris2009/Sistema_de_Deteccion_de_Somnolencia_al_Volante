import mediapipe as mp

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
MOUTH = [61, 291, 39, 181, 0, 17, 269, 405]
NOSE_TIP = 1
CHIN = 152
LEFT_EYE_OUTER = 263
RIGHT_EYE_OUTER = 33


class FaceLandmarkDetector:
    def __init__(self, max_faces=1, refine_landmarks=True,
                 min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self._mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=max_faces,
            refine_landmarks=refine_landmarks,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def process(self, frame_bgr):
        rgb = frame_bgr[:, :, ::-1]
        results = self._mesh.process(rgb)
        if not results.multi_face_landmarks:
            return None
        h, w = frame_bgr.shape[:2]
        landmarks = results.multi_face_landmarks[0].landmark
        return [(int(p.x * w), int(p.y * h)) for p in landmarks]

    def close(self):
        self._mesh.close()
