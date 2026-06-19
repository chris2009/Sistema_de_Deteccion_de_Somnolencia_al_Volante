# Sistema de Detección de Somnolencia al Volante (Laboratorio 03)

Sistema de visión computacional en tiempo real que usa la **webcam** para detectar
signos de fatiga y microsueño en un conductor, y emite alertas progresivas
(visuales, sonoras y de voz) antes de que ocurra un accidente.

---

## 1. Contexto y motivación

El video de referencia del laboratorio
(`https://www.youtube.com/watch?v=H2PP_LxqYaE`) muestra accidentes de tránsito
causados por conductores que se quedan dormidos al volante (microsueños). El
microsueño es un episodio de pérdida de consciencia de 1 a 30 segundos en el
que la persona sigue con los ojos parcial o totalmente abiertos pero no
reacciona — por eso una solución basada en cámara que mida el **comportamiento
de los ojos y la boca en el tiempo** (no solo una foto puntual) es la
estrategia correcta.

### Causas típicas del accidente (narrativa)
- Conducción nocturna o en turnos largos sin descanso.
- Privación de sueño acumulada del conductor.
- Ausencia de un sistema de monitoreo/alerta dentro del vehículo.
- El propio conductor no percibe que está cayendo en microsueño hasta que ya
  perdió el control.

### Propuesta de solución
Un sistema de bajo costo (solo una laptop/webcam, sin hardware adicional) que:
1. Monitorea continuamente el rostro del conductor.
2. Calcula métricas objetivas de fatiga ocular y bucal.
3. Clasifica el estado en 3 niveles de alerta con histéresis (para evitar
   falsas alarmas por un parpadeo normal).
4. Alerta de forma creciente: visual → sonora → voz hablada.
5. Al finalizar la sesión, genera un reporte gráfico con la evolución de la
   fatiga, útil para análisis posterior (ej. una empresa de transporte
   revisando el historial de sus conductores).

### Vínculo con los Objetivos de Desarrollo Sostenible (ODS)
- **ODS 3 — Salud y bienestar**, meta **3.6**: *"De aquí a 2030, reducir a la
  mitad el número de muertes y lesiones causadas por accidentes de tráfico en
  el mundo."* Es el ODS más directo: el sistema previene muertes/lesiones por
  accidentes viales causados por fatiga.
- **ODS 11 — Ciudades y comunidades sostenibles**, meta **11.2**: *"proporcionar
  acceso a sistemas de transporte seguros"* — un sistema de asistencia al
  conductor contribuye a un transporte más seguro.

---

## 2. Fundamento técnico (cómo funciona)

### 2.1 Detección facial — MediaPipe Face Mesh
Se usa `mediapipe.solutions.face_mesh`, que entrega **468 landmarks (puntos)
3D del rostro** a partir de una sola imagen RGB de la webcam, sin necesitar
hardware de profundidad. De ahí extraemos subconjuntos de puntos relevantes
para los ojos y la boca.

### 2.2 EAR — Eye Aspect Ratio (Apertura del ojo)
Para cada ojo se toman 6 puntos (4 horizontales/verticales del contorno) y se
calcula:

```
EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
```

- Ojo bien abierto → EAR alto (~0.25–0.35).
- Ojo cerrado → EAR cae fuertemente (~< 0.21, umbral usado en el código).
- Se promedia el EAR del ojo izquierdo y derecho para mayor estabilidad.

**Por qué EAR y no comparar contra una imagen de "ojo cerrado":** es una
métrica geométrica relativa a la propia cara de la persona, así que funciona
igual de bien sin importar el tamaño del ojo, distancia a la cámara o
identidad del conductor — no requiere entrenar un modelo por persona.

### 2.3 MAR — Mouth Aspect Ratio (Bostezo)
Misma idea que el EAR pero aplicada a la boca, usando puntos del contorno
labial:

```
MAR = (||boca_v1|| + ||boca_v2||) / ||boca_h||
```

Un MAR alto y sostenido en el tiempo (no solo hablar o reír, que son picos
breves) indica un bostezo, otra señal de fatiga.

### 2.4 PERCLOS — PERcentage of eye CLOSure
Es la métrica clínicamente más usada en literatura de fatiga al volante.
A diferencia de "contar frames seguidos con ojos cerrados", PERCLOS mide el
**porcentaje de tiempo con ojos cerrados dentro de una ventana deslizante**
(en este proyecto, los últimos 45 frames ≈ 1.5 segundos a 30 FPS):

```
PERCLOS = (frames con EAR < umbral) / (total de frames en la ventana)
```

Esto permite detectar tanto:
- **Microsueño franco**: ojos cerrados varios frames consecutivos.
- **Fatiga por parpadeo lento**: ojos que se cierran y abren repetidamente
  pero con más tiempo cerrado de lo normal (un contador de racha simple no
  detectaría este segundo patrón).

### 2.5 Máquina de estados con histéresis (`alert_engine.py`)
El sistema no salta directo de "todo bien" a "alarma" con un solo frame malo
(eso generaría falsas alarmas por un parpadeo normal). Usa 3 estados:

| Estado | Color | Condición de entrada |
|---|---|---|
| `GREEN` (Normal) | Verde | PERCLOS bajo, sin racha de ojos cerrados ni bostezo sostenido |
| `YELLOW` (Somnolencia leve) | Amarillo | PERCLOS ≥ 15% **o** bostezo sostenido ≥ 20 frames |
| `RED` (Peligro / microsueño) | Rojo | PERCLOS ≥ 30% **o** ojos cerrados ≥ 15 frames consecutivos (~0.5 s) |

**Histéresis de recuperación:** para volver a `GREEN` desde `YELLOW`/`RED` se
exige una racha de **20 frames "buenos" consecutivos** (`recovery_frames`),
no un solo frame bueno — esto evita que el semáforo "parpadee" entre estados
en cada frame.

Cada vez que el sistema entra en `RED` (transición, no frame a frame) se
incrementa un contador de **microsueños detectados en la sesión**.

### 2.6 Alertas progresivas (`audio_voice.py`)
- **Visual**: el HUD cambia de color, se dibuja un borde rojo parpadeante y un
  tinte rojo translúcido sobre todo el frame en estado `RED`.
- **Sonora**: `winsound.Beep` (nativo de Windows, sin dependencias externas)
  — un beep corto en amarillo, una serie de beeps agudos en rojo.
- **Voz hablada**: `pyttsx3` (síntesis de voz offline) dice frases como
  *"Atención, signos de cansancio detectados"* (amarillo) o *"Despierta, toma
  un descanso ahora"* (rojo).
- Todo el audio corre en **hilos separados** (`threading.Thread`) para que la
  reproducción de sonido/voz nunca bloquee ni ralentice el video en vivo.
- Hay un *cooldown* de 4 segundos entre frases de voz para no saturar al
  usuario con audio repetido en cada frame que sigue en alerta.

### 2.7 HUD (interfaz visual en vivo) (`hud_overlay.py`)
Inspirado en un tablero de auto deportivo, dibujado directamente sobre el
frame de OpenCV:
- **Gauge circular de "FATIGA"**: un arco que se llena de 0 a 360° según el
  valor de PERCLOS, coloreado según el estado (verde/amarillo/rojo).
- **Sparkline (mini-gráfico en vivo)** del histórico reciente de EAR, como un
  monitor de electrocardiograma.
- **Barra inferior** con el estado textual (`ALERTA: NORMAL` /
  `SOMNOLENCIA LEVE` / `PELIGRO - MICROSUEÑO`) y las métricas numéricas
  (EAR, MAR, PERCLOS %, contador de microsueños).

### 2.8 Reporte de sesión (`session_report.py`)
Al cerrar la aplicación (tecla `q`), se genera automáticamente un PNG
(`reporte_sesion_AAAAMMDD_HHMMSS.png`) con:
- Gráfico de EAR a lo largo del tiempo, con la línea de umbral de "ojos
  cerrados" marcada.
- Gráfico de PERCLOS (%) a lo largo del tiempo, con franjas de color de fondo
  indicando en qué estado estuvo el conductor en cada momento.
- Total de microsueños detectados en la sesión, en el título.

Este reporte es ideal para mostrarlo en la demo en vivo como "evidencia" de
que el sistema detectó y registró los eventos de fatiga simulados.

---

## 3. Arquitectura del código

```
Laboratorio_03_20-06-26/
├── venv/                  # entorno virtual de Python (no se sube a entrega, solo es local)
├── requirements.txt       # dependencias exactas usadas
├── landmarks.py           # wrapper de MediaPipe Face Mesh + índices de ojos/boca
├── metrics.py             # cálculo de EAR, MAR y PERCLOS (ventana deslizante)
├── alert_engine.py        # máquina de estados GREEN/YELLOW/RED con histéresis
├── hud_overlay.py         # dibuja el HUD (gauge, sparkline, barra de estado) sobre el frame
├── audio_voice.py         # alarma (winsound) y voz (pyttsx3) en hilos no bloqueantes
├── session_report.py      # genera el PNG resumen de la sesión con matplotlib
├── main.py                # loop principal: captura webcam y orquesta todo lo anterior
└── README.md               # este documento
```

**Flujo de datos por cada frame** (dentro de `main.py`):

```
webcam → frame (BGR)
   → landmarks.FaceLandmarkDetector.process()  → 468 puntos (x,y)
   → metrics.average_ear() / mouth_aspect_ratio() → EAR, MAR
   → metrics.Perclos.update()                  → PERCLOS (ventana de 45 frames)
   → alert_engine.AlertEngine.update()         → estado GREEN/YELLOW/RED
   → audio_voice.AlertSound.notify()           → beep + voz (en hilos, no bloquea)
   → hud_overlay.Hud.draw()                    → frame con overlays dibujado
   → cv2.imshow()                              → se muestra en pantalla
   → (al salir) session_report.save_session_report() → PNG resumen
```

Cada módulo tiene una responsabilidad única (detección, métricas, lógica de
alerta, presentación visual, audio, reporte), lo que facilita explicar el
código en la exposición módulo por módulo.

---

## 4. Instalación y ejecución

### 4.1 Crear el entorno (ya hecho en este proyecto, pasos para replicar)
```powershell
cd Laboratorio_03_20-06-26
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

> Se usó **Python 3.11** específicamente porque `mediapipe` tiene los wheels
> precompilados más estables en esa versión en Windows.

### 4.2 Dependencias (`requirements.txt`)
| Paquete | Uso |
|---|---|
| `opencv-python` | Captura de webcam y dibujo del HUD sobre el video |
| `mediapipe` | Detección de los 468 landmarks faciales (Face Mesh) |
| `numpy` | Soporte numérico (dependencia de los anteriores) |
| `matplotlib` | Generación del reporte gráfico de sesión |
| `pyttsx3` | Síntesis de voz offline para las alertas habladas |

(`winsound` para los beeps no está en `requirements.txt` porque es un módulo
nativo incluido en Python para Windows, no requiere instalación.)

### 4.3 Ejecutar
```powershell
.\venv\Scripts\python.exe main.py
```
- Se abre una ventana con el video de la webcam y el HUD superpuesto.
- Presiona **`q`** para salir.
- Al salir se imprime en consola la ruta del PNG de reporte generado.

---

## 5. Parámetros configurables (para ajustar sensibilidad)

Todos están como argumentos del constructor de `AlertEngine` en
`alert_engine.py`, con valores por defecto pensados para ~30 FPS:

| Parámetro | Valor por defecto | Significado |
|---|---|---|
| `ear_threshold` | 0.21 | EAR por debajo del cual se considera "ojo cerrado" |
| `mar_threshold` | 0.60 | MAR por encima del cual se considera "bostezo" |
| `closed_frames_for_red` | 15 (~0.5 s) | Frames consecutivos con ojos cerrados para pasar a `RED` |
| `yawn_frames_for_yellow` | 20 | Frames consecutivos de bostezo para pasar a `YELLOW` |
| `recovery_frames` | 20 | Frames "buenos" consecutivos para poder volver a `GREEN` |
| `perclos_yellow` | 0.15 (15%) | Umbral de PERCLOS para `YELLOW` |
| `perclos_red` | 0.30 (30%) | Umbral de PERCLOS para `RED` |

Si en las pruebas el sistema se siente muy sensible (alarmas con parpadeo
normal) o muy laxo (no detecta cierres reales), estos son los valores a
ajustar primero.

---

## 6. Limitaciones conocidas (importante para la sección "Conclusiones" del PPT)

- **Lentes (anteojos):** funciona en la mayoría de casos porque MediaPipe
  detecta landmarks sobre la imagen completa, no depende de "ver el ojo
  desnudo". Sin embargo:
  - Reflejos de luz directa sobre el cristal pueden generar lecturas
    erráticas de EAR momentáneamente.
  - Armazones muy gruesos pueden subestimar levemente la apertura del ojo.
  - Lentes de sol/oscuros sí degradan bastante la precisión (no recomendado).
- **Iluminación:** poca luz o luz muy lateral reduce la calidad de los
  landmarks faciales. Se recomienda iluminación frontal para la demo.
- **Head pose / cabeceo:** se evaluó incluirlo (inclinación de cabeza hacia
  adelante como señal adicional de microsueño) pero se descartó en esta
  versión porque estimarlo con precisión requiere calibración de la cámara
  (matriz intrínseca); con landmarks 2D sin calibrar el resultado es ruidoso.
  Queda como trabajo futuro.
- **Una sola persona a la vez:** el sistema está configurado para
  `max_num_faces=1` (el conductor). No está pensado para monitorear pasajeros.
- **Falsos positivos posibles:** hablar, reír o estornudar pueden generar
  picos de MAR; se mitigó exigiendo que el bostezo sea **sostenido** (20
  frames), pero no es 100% infalible.

---

## 7. Posibles mejoras futuras
- Calibración de cámara para estimar head pose (pitch/yaw/roll) de forma
  confiable y sumarlo como señal adicional.
- Modo de calibración inicial por usuario (medir el EAR "normal" de cada
  conductor en los primeros segundos, en vez de un umbral fijo para todos).
- Integración con notificación remota (ej. enviar alerta a un supervisor de
  flota vía Telegram/SMS si se detectan múltiples microsueños).
- Registro en base de datos en vez de solo PNG, para análisis histórico de
  varios viajes/conductores.

---

## 8. Referencias bibliográficas
- Soukupová, T., & Čech, J. (2016). *Real-Time Eye Blink Detection using
  Facial Landmarks.* 21st Computer Vision Winter Workshop.
- Dinges, D. F., & Grace, R. (1998). *PERCLOS: A valid psychophysiological
  measure of alertness as assessed by psychomotor vigilance.* U.S. Department
  of Transportation, Federal Highway Administration.
- Google AI Edge / MediaPipe Documentation — Face Landmarker:
  https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker
- Naciones Unidas — Objetivos de Desarrollo Sostenible, ODS 3 y ODS 11:
  https://www.un.org/sustainabledevelopment/es/
