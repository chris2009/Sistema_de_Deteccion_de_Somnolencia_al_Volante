# Arquitectura técnica del sistema

Este documento explica **cómo funciona internamente** el sistema: el
algoritmo de detección, las fórmulas usadas, la máquina de estados, y cómo
se conectan los módulos del código entre sí.

---

## 1. Visión general del pipeline

```
┌──────────┐   ┌───────────────────┐   ┌────────────────────┐   ┌──────────────────┐
│  Webcam  │──▶│ FaceLandmarkDetector│──▶│  metrics.py          │──▶│  AlertEngine       │
│ (OpenCV) │   │  (MediaPipe Face   │   │  EAR, MAR, PERCLOS  │   │  GREEN/YELLOW/RED  │
│ 1 frame  │   │   Mesh, 468 pts)   │   │                      │   │  (con histéresis)  │
└──────────┘   └───────────────────┘   └────────────────────┘   └─────────┬──────────┘
                                                                            │
                              ┌─────────────────────────────────────────────┤
                              ▼                                              ▼
                     ┌────────────────┐                            ┌─────────────────┐
                     │  hud_overlay.py │                            │  audio_voice.py   │
                     │  dibuja gauge,  │                            │  beep (winsound) + │
                     │  sparkline,     │                            │  voz (pyttsx3) en  │
                     │  barra de estado│                            │  hilos separados   │
                     └────────────────┘                            └─────────────────┘
                              │
                              ▼
                     ┌────────────────┐
                     │  cv2.imshow()   │   (al presionar 'q')──▶ session_report.py ──▶ PNG
                     └────────────────┘
```

Cada módulo tiene **una sola responsabilidad** (principio de
responsabilidad única), lo que permite explicar o modificar cada parte de
forma aislada.

---

## 2. Detección facial — `landmarks.py`

Usa `mediapipe.solutions.face_mesh.FaceMesh`, que con un solo frame RGB
entrega **468 landmarks 3D** del rostro (sin necesitar cámara de
profundidad — es un modelo entrenado que infiere geometría 3D desde una
imagen 2D).

De esos 468 puntos, el proyecto solo usa 3 subconjuntos de índices fijos:

```python
LEFT_EYE  = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
MOUTH     = [61, 291, 39, 181, 0, 17, 269, 405]
```

Estos índices son **fijos y estándar** en la topología de MediaPipe Face
Mesh (no cambian entre personas ni entre frames); por eso se pueden
"hardcodear" sin necesidad de detectarlos dinámicamente.

`FaceLandmarkDetector.process(frame)` devuelve una lista de 468 tuplas
`(x, y)` en coordenadas de píxel, o `None` si no se detectó ningún rostro en
ese frame.

---

## 3. Métricas — `metrics.py`

### 3.1 EAR (Eye Aspect Ratio)

Para cada ojo (6 puntos: 2 extremos horizontales + 2 pares verticales):

```
EAR = ( ||p2 − p6|| + ||p3 − p5|| ) / ( 2 × ||p1 − p4|| )
```

```
        p2   p3
         •───•
   p1 •           • p4      EAR alto  → ojo abierto
         •───•               EAR bajo  → ojo cerrado
        p6   p5
```

- Es una razón (alto/ancho del ojo), por lo que **no depende de la distancia
  a la cámara ni del tamaño absoluto del ojo de la persona** — solo de su
  proporción de apertura.
- Se calcula para ambos ojos y se promedia (`average_ear`), para que un
  guiño de un solo ojo no dispare una falsa alarma.

### 3.2 MAR (Mouth Aspect Ratio)

Misma idea, aplicada a 8 puntos del contorno de la boca:

```
MAR = ( ||v1|| + ||v2|| ) / ||h||
```

Un MAR alto sostenido en el tiempo (no un pico de una sola fracción de
segundo, que sería hablar/reír) indica un bostezo.

### 3.3 PERCLOS (PERcentage of eye CLOSure)

Implementado en la clase `Perclos`, que mantiene una **cola de tamaño fijo**
(`collections.deque(maxlen=45)`, ≈ 1.5 s a 30 FPS):

```python
class Perclos:
    def update(self, ear):
        self._window.append(1 if ear < self.ear_threshold else 0)

    @property
    def value(self):
        return sum(self._window) / len(self._window)
```

Esto es deliberadamente distinto de "contar frames consecutivos cerrados":
una ventana deslizante también captura el patrón de **parpadeo lento
repetido** (ojos que se cierran y abren varias veces, pasando más tiempo
cerrados de lo normal), que un contador de racha no detectaría porque se
resetea en cada apertura.

---

## 4. Máquina de estados — `alert_engine.py`

### 4.1 Por qué una máquina de estados y no un `if` simple

Reaccionar a un solo frame "malo" generaría falsas alarmas constantes (un
parpadeo normal dura 2-4 frames). La solución es un sistema con:

1. **Umbrales basados en rachas** (cuántos frames consecutivos malos antes
   de escalar), no en un frame aislado.
2. **Histéresis de recuperación**: para bajar de alerta se exige una racha
   de frames *buenos*, no un solo frame bueno — evita que el estado
   "parpadee" entre verde/amarillo en cada frame límite.

### 4.2 Reglas de transición

| Transición | Condición |
|---|---|
| `* → RED` | `PERCLOS ≥ 30%` **o** racha de ojos cerrados ≥ 15 frames (~0.5 s) |
| `* → YELLOW` | `PERCLOS ≥ 15%` **o** racha de bostezo ≥ 20 frames |
| `YELLOW/RED → GREEN` | racha de frames "buenos" (sin ojos cerrados ni bostezo) ≥ 20 frames |

```python
target = GREEN
if perclos >= self.perclos_red or self._closed_streak >= self.closed_frames_for_red:
    target = RED
elif perclos >= self.perclos_yellow or self._yawn_streak >= self.yawn_frames_for_yellow:
    target = YELLOW
```

El **contador de microsueños** (`microsleep_count`) se incrementa solo en
la **transición** de "no estaba en RED" a "RED" (no en cada frame que se
mantiene en RED), usando una bandera `_was_red`:

```python
if target == RED:
    if not self._was_red:
        self.microsleep_count += 1
    self._was_red = True
```

### 4.3 Parámetros configurables

| Parámetro | Default | Qué controla |
|---|---|---|
| `ear_threshold` | 0.21 | EAR por debajo del cual se considera "ojo cerrado" |
| `mar_threshold` | 0.60 | MAR por encima del cual se considera "bostezo" |
| `closed_frames_for_red` | 15 | Frames consecutivos de ojos cerrados → `RED` |
| `yawn_frames_for_yellow` | 20 | Frames consecutivos de bostezo → `YELLOW` |
| `recovery_frames` | 20 | Frames buenos consecutivos para volver a `GREEN` |
| `perclos_yellow` | 0.15 | PERCLOS mínimo para `YELLOW` |
| `perclos_red` | 0.30 | PERCLOS mínimo para `RED` |

Todos están pensados para ~30 FPS; si la webcam corre a otro FPS, hay que
escalar los conteos de frames proporcionalmente (ej. a 15 FPS, dividir entre
2 para mantener el mismo tiempo real en segundos).

---

## 5. Alertas — `audio_voice.py`

El reto de diseño aquí es que **reproducir audio no debe bloquear el loop de
video** (si `engine.runAndWait()` de `pyttsx3` tardara 1.5 segundos en el
hilo principal, el video se congelaría ese tiempo). Solución: cada alerta
se dispara en su propio hilo `daemon`:

```python
threading.Thread(target=self._play_beep, args=(state,), daemon=True).start()
threading.Thread(target=self._speak, args=(state,), daemon=True).start()
```

- **Beep** (`winsound.Beep`): nativo de Windows, sin dependencias.
  Amarillo = 1 beep corto; Rojo = 3 beeps agudos.
- **Voz** (`pyttsx3`): motor de TTS offline (no requiere internet). Tiene un
  *cooldown* de 4 segundos (`MIN_SECONDS_BETWEEN_VOICE`) para no disparar
  una frase nueva en cada uno de los ~30 frames por segundo que el estado
  se mantiene en alerta.
- Un `threading.Lock` (`_engine_lock`) evita que dos hilos llamen al motor
  de `pyttsx3` al mismo tiempo (no es thread-safe por sí mismo).

---

## 6. HUD visual — `hud_overlay.py`

Todo se dibuja directamente sobre el array NumPy del frame usando
primitivas de OpenCV (`cv2.circle`, `cv2.ellipse`, `cv2.line`, `cv2.putText`):

- **Gauge circular**: un arco (`cv2.ellipse` con ángulo de inicio/fin) que se
  llena de 0° a 360° proporcionalmente al valor de PERCLOS.
- **Sparkline**: se normalizan los últimos N valores de EAR al rango del
  recuadro y se conectan con `cv2.line` punto a punto — es, en esencia, un
  gráfico de líneas dibujado a mano sin librería de gráficos.
- **Overlay rojo de peligro**: en estado `RED`, se mezcla una capa roja
  semitransparente sobre todo el frame con `cv2.addWeighted` (alpha blending),
  más un borde grueso — para que la alerta sea perceptible incluso si el
  usuario no está mirando directamente la barra de texto.

---

## 7. Reporte de sesión — `session_report.py`

Al cerrar la aplicación, se llama a `save_session_report(...)` con todo el
historial acumulado de la sesión (`timestamps`, `ear_log`, `perclos_log`,
`state_log`). Usa `matplotlib` para generar dos subplots (EAR en el tiempo,
PERCLOS en el tiempo con franjas de color de fondo según el estado) y los
guarda como PNG con timestamp en el nombre.

Esto convierte al sistema en algo más que una alarma en vivo: deja
**evidencia auditable** de la sesión, útil para un caso de uso real (una
empresa de transporte revisando el historial de fatiga de sus conductores).

---

## 8. `main.py` — orquestación

El loop principal por cada frame:

```python
points = detector.process(frame)
if points is not None:
    ear = average_ear(points)
    mar = mouth_aspect_ratio(points)
    perclos.update(ear)
    state = engine.update(ear, mar, perclos.value)
    sound.notify(state)
    hud.push(ear, perclos.value)
    hud.draw(frame, state, ear, mar, perclos.value, engine.microsleep_count)
```

Si no se detecta rostro en un frame (`points is None`), se omite el cálculo
de métricas y solo se muestra un aviso en pantalla — el estado de alerta no
se actualiza con datos inválidos.

Al salir (tecla `q`), el bloque `finally` garantiza que la cámara se libere
(`cap.release()`), las ventanas se cierren (`cv2.destroyAllWindows()`), el
detector de MediaPipe se cierre (`detector.close()`) y el reporte se guarde
— incluso si ocurre una excepción durante el loop.

---

## 9. Limitaciones conocidas

- **Lentes:** MediaPipe detecta landmarks sobre la imagen completa, así que
  lentes normales no impiden la detección. Reflejos de luz directa sobre el
  cristal o armazones muy gruesos pueden introducir ruido en el EAR. Lentes
  de sol degradan bastante la precisión del iris.
- **Iluminación:** luz lateral o insuficiente reduce la calidad de los
  landmarks. Se recomienda luz frontal.
- **Head pose (cabeceo):** se evaluó añadir la inclinación de cabeza como
  señal adicional de microsueño, pero se descartó en esta versión porque
  estimarla con precisión desde landmarks 2D sin calibrar la cámara (sin
  matriz intrínseca) da resultados ruidosos. Queda como trabajo futuro.
- **Una sola persona:** `max_num_faces=1`, pensado para monitorear solo al
  conductor.
- **Falsos positivos:** hablar/reír puede generar picos de MAR; se mitiga
  exigiendo que el bostezo sea sostenido (20 frames), aunque no es 100%
  infalible.

## 10. Trabajo futuro

- Calibración de cámara para head pose confiable (pitch/yaw/roll).
- Calibración por usuario: medir el EAR "normal" de cada conductor en los
  primeros segundos en vez de usar un umbral fijo para todos.
- Notificación remota (Telegram/SMS) a un supervisor de flota.
- Persistencia en base de datos en vez de solo PNG, para análisis histórico
  multi-sesión.
