import threading
import time
import winsound

import pyttsx3

from alert_engine import GREEN, YELLOW, RED

VOICE_PHRASES = {
    YELLOW: "Atencion, signos de cansancio detectados.",
    RED: "Despierta, toma un descanso ahora.",
}

MIN_SECONDS_BETWEEN_VOICE = 4.0


class AlertSound:
    """Runs beeps/voice on background threads so the OpenCV video
    loop never blocks waiting on audio playback."""

    def __init__(self):
        self._last_voice_time = 0.0
        self._lock = threading.Lock()
        self._engine_lock = threading.Lock()

    def notify(self, state):
        if state == GREEN:
            return
        threading.Thread(target=self._play_beep, args=(state,), daemon=True).start()

        now = time.time()
        with self._lock:
            if now - self._last_voice_time < MIN_SECONDS_BETWEEN_VOICE:
                return
            self._last_voice_time = now
        threading.Thread(target=self._speak, args=(state,), daemon=True).start()

    def _play_beep(self, state):
        try:
            if state == YELLOW:
                winsound.Beep(700, 150)
            elif state == RED:
                for _ in range(3):
                    winsound.Beep(1200, 120)
                    time.sleep(0.05)
        except RuntimeError:
            pass

    def _speak(self, state):
        phrase = VOICE_PHRASES.get(state)
        if not phrase:
            return
        with self._engine_lock:
            engine = pyttsx3.init()
            engine.setProperty("rate", 165)
            engine.say(phrase)
            engine.runAndWait()
            engine.stop()
