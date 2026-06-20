# Notas de exposición — Slide "Propuesta de Solución"

Guion de respaldo para justificar, con fundamento técnico, cada uno de los
6 pasos del diagrama del slide. Pensado para responder preguntas del
profesor/compañeros durante la exposición.

---

## 1. Captura de Video

**Lo que dice el slide:** "La webcam captura el rostro frame por frame."

**Justificación:**
- El sistema no necesita una foto única: la fatiga es un fenómeno que se
  manifiesta **en el tiempo** (parpadeo lento, ojos cerrados varios
  segundos), por eso se procesa un flujo continuo de frames, no una imagen
  aislada.
- Se usa `cv2.VideoCapture` de OpenCV, que entrega frames en formato BGR a
  la tasa de FPS que soporte la cámara (~30 FPS en una webcam estándar).
- No requiere cámara especial ni de profundidad: cualquier webcam RGB
  (laptop, celular) es suficiente — esto es justamente lo que hace la
  solución accesible y de bajo costo.

---

## 2. Localización de puntos faciales

**Lo que dice el slide:** "MediaPipe Face Mesh localiza 468 puntos
faciales (ojos, boca, contorno)."

**Justificación:**
- Se usa **MediaPipe Face Mesh** (Google), un modelo de deep learning
  pre-entrenado que infiere 468 landmarks 3D del rostro a partir de una
  sola imagen 2D, sin necesitar hardware de profundidad (LiDAR/IR).
- Estos 468 puntos siguen una topología **fija y estandarizada**: el punto
  número 33, por ejemplo, siempre corresponde a la esquina del ojo derecho,
  sin importar la persona. Esto permite extraer subconjuntos fijos de
  índices para ojos y boca sin necesidad de detectarlos dinámicamente.
- Corre en tiempo real sobre CPU (no requiere GPU), lo que es clave para
  que la solución funcione en una laptop común o en un celular de gama
  media.
- Es más robusto que alternativas clásicas como Haar Cascades (usadas en
  OpenCV básico), que son más sensibles a cambios de iluminación y ángulo.

---

## 3. Cálculo de métricas (EAR y MAR)

**Lo que dice el slide:** "Se calculan dos métricas geométricas: EAR (qué
tan abiertos están tus ojos) y MAR (qué tan abierta está tu boca, para
detectar bostezos)."

**Justificación:**
- **EAR (Eye Aspect Ratio):** razón entre la distancia vertical y
  horizontal de 6 puntos del contorno del ojo:
  `EAR = (||p2-p6|| + ||p3-p5||) / (2 × ||p1-p4||)`.
  Ojo abierto → EAR alto; ojo cerrado → EAR cae fuertemente.
- **MAR (Mouth Aspect Ratio):** misma lógica aplicada a 8 puntos del
  contorno de la boca, para detectar bostezos sostenidos.
- **Por qué una razón geométrica y no comparar contra una imagen de
  referencia:** al ser una proporción (alto/ancho), el EAR/MAR funciona
  igual sin importar la distancia de la persona a la cámara, el tamaño de
  sus ojos, o si es una persona distinta cada vez — no requiere entrenar
  ni calibrar un modelo por usuario.
- Referencia académica: Soukupová & Čech (2016), *Real-Time Eye Blink
  Detection using Facial Landmarks.*

---

## 4. Medición de tiempo de ojos cerrados (PERCLOS)

**Lo que dice el slide:** "Una métrica acumulada, PERCLOS, mide qué
porcentaje del último 1.5 segundos tuviste los ojos cerrados."

**Justificación:**
- **PERCLOS (PERcentage of eye CLOSure)** es la métrica más usada en la
  literatura clínica y de seguridad vial para medir fatiga (Dinges & Grace,
  1998, FHWA — U.S. Department of Transportation).
- Se calcula sobre una **ventana deslizante** de los últimos 45 frames
  (≈1.5 s a 30 FPS): `PERCLOS = (frames con ojos cerrados) / (total frames
  en la ventana)`.
- Es superior a simplemente "contar frames consecutivos cerrados" porque
  también detecta el patrón de **parpadeo lento repetido** (el ojo se
  cierra y abre varias veces, pasando más tiempo cerrado de lo normal sin
  llegar a un cierre continuo) — un contador de racha simple no vería ese
  patrón porque se resetea en cada apertura del ojo.
- Es la justificación de por qué el sistema no se basa solo en "EAR bajo en
  este frame", sino en una métrica acumulada en el tiempo.

---

## 5. Decisión de nivel de alerta

**Lo que dice el slide:** "Una máquina de estados decide el nivel de
alerta (verde/amarillo/rojo) con histéresis, para no disparar falsas
alarmas por un parpadeo normal."

### ¿Qué es una máquina de estados?

Una **máquina de estados** es un modelo de control donde el sistema solo
puede estar en uno de un número limitado de **estados** en cada momento
(aquí: `GREEN`, `YELLOW`, `RED`), y pasa de uno a otro únicamente cuando se
cumple una **condición de transición** específica — no cambia de estado
"libremente" en cualquier momento.

Analogía simple: es como un **semáforo**. El semáforo no salta de verde a
rojo por capricho; necesita que se cumpla una condición (el temporizador
llega a cierto valor) para cambiar. Mientras esa condición no se cumple,
se queda en el mismo estado, sin importar pequeñas variaciones momentáneas.

En este proyecto:
- **Estados posibles:** `GREEN` (normal), `YELLOW` (somnolencia leve),
  `RED` (peligro / microsueño).
- **Condición para subir de estado:** una racha de varios frames seguidos
  con ojos cerrados/bostezo, o un PERCLOS alto sostenido (no un solo frame
  aislado).
- **Condición para bajar de estado:** una racha de frames "buenos"
  consecutivos (no basta con un solo frame bueno).

Por qué se eligió este modelo y no un simple `if ear < umbral: alarma`:
con un `if` directo, cada frame se evalúa de forma aislada, y como un
parpadeo normal también hace que el EAR baje por 2-4 frames, el sistema
dispararía alarmas constantemente con cualquier parpadeo. La máquina de
estados, al exigir una **racha sostenida** para cambiar de estado, filtra
ese ruido y solo reacciona a patrones que realmente indican fatiga.

**Justificación:**
- Reaccionar a un solo frame "malo" generaría alarmas constantes, ya que un
  parpadeo normal dura 2-4 frames y también tendría EAR bajo en ese
  instante.
- Por eso se usa una **máquina de estados de 3 niveles** (verde = normal,
  amarillo = somnolencia leve, rojo = peligro/microsueño) con reglas
  basadas en **rachas de frames** y en el valor de PERCLOS, no en un frame
  aislado.
- **Histéresis:** para bajar de nivel (ej. de rojo a verde) se exige una
  racha de frames "buenos" consecutivos, no un solo frame bueno. Esto evita
  que el indicador "parpadee" entre estados cuando los valores están justo
  en el límite del umbral.
- Esta es la misma lógica que usan sistemas de control industrial para
  evitar oscilaciones — aplicada aquí a la decisión de alerta.

### ¿Qué umbrales se eligieron y por qué?

Todos los valores asumen ~30 FPS (lo típico de una webcam estándar). Cada
umbral viene de un equilibrio entre **literatura de referencia** y
**pruebas empíricas** para que el sistema sea sensible pero no paranoico:

| Umbral | Valor elegido | Por qué ese valor |
|---|---|---|
| `EAR umbral` (ojo cerrado) | **0.21** | Es el valor reportado en la literatura de referencia (Soukupová & Čech, 2016) como el punto donde un ojo abierto normal (EAR ≈ 0.25–0.35) cae claramente a "cerrado". Se validó con pruebas propias frente a la cámara. |
| `MAR umbral` (bostezo) | **0.60** | Un MAR alto pero breve ocurre al hablar o reír; 0.60 se eligió porque solo se alcanza con la boca claramente muy abierta, como en un bostezo real, evitando falsos positivos al conversar. |
| `Racha de ojos cerrados → RED` | **15 frames (~0.5 s)** | Un parpadeo normal dura 2-4 frames (~0.1 s). Se eligió 15 frames como margen amplio de seguridad: ningún parpadeo natural llega a esa duración, solo un cierre sostenido (microsueño real) la alcanza. |
| `Racha de bostezo → YELLOW` | **20 frames (~0.65 s)** | Similar al anterior: una mueca o risa breve no se sostiene tanto tiempo; un bostezo real sí. |
| `PERCLOS → YELLOW` | **15%** | Significa que en los últimos 1.5 s, el ojo estuvo cerrado el 15% del tiempo. Es un nivel de "alerta temprana" — fatiga incipiente, parpadeo más lento de lo normal, pero el conductor aún reacciona. |
| `PERCLOS → RED` | **30%** | En estudios de PERCLOS (Dinges & Grace, 1998, FHWA) un PERCLOS sostenido por encima de ~30-40% se asocia con niveles de somnolencia que afectan significativamente el tiempo de reacción del conductor. Se tomó el extremo inferior de ese rango para priorizar la seguridad (alertar antes, no después). |
| `Racha de recuperación → GREEN` | **20 frames (~0.65 s)** | Se exige casi el mismo tiempo que toma escalar a alerta, para evitar que el sistema baje de nivel apenas hay un instante de mejora y luego vuelva a subir — eso generaría parpadeo del indicador visual. |
| `Ventana de PERCLOS` | **45 frames (~1.5 s)** | Es la ventana de tiempo en la que se promedia el cierre de ojos. Se eligió 1.5 s porque es lo bastante corta para reaccionar rápido ante un microsueño, pero lo bastante larga para no confundirse con un parpadeo aislado. |

**Idea central para defender en la exposición:** ningún umbral se eligió
"a ojo" sin razón — cada uno tiene un ancla en la literatura de fatiga al
volante (EAR, PERCLOS) o en el comportamiento fisiológico normal (duración
de un parpadeo natural vs. un cierre prolongado), y luego se ajustaron
empíricamente probando frente a la cámara para que no disparen con
comportamiento normal.

---

## 6. Alerta

**Lo que dice el slide:** "Si el nivel sube, el sistema suena una alarma y
habla ('Despierta, toma un descanso ahora'), y al cerrar la app genera un
reporte gráfico de toda la sesión."

**Justificación:**
- La alerta es **progresiva y multimodal** (visual + sonora + voz), porque
  un conductor en estado de fatiga puede no reaccionar a un solo estímulo
  visual (ya tiene los ojos cerrados) — el sonido y la voz son canales
  adicionales para captar su atención.
- El audio corre en **hilos separados** (`threading`) para no congelar el
  video mientras se reproduce el beep o la frase hablada.
- La voz usa síntesis **offline** (`pyttsx3`), por lo que funciona sin
  conexión a internet — relevante para uso real en carretera.
- El **reporte gráfico final** (generado con `matplotlib`) convierte al
  sistema en algo más que una alarma momentánea: deja evidencia auditable
  de la sesión (EAR, PERCLOS y microsueños en el tiempo), útil en un caso
  de uso real como una empresa de transporte supervisando a sus
  conductores.

---

## Posibles preguntas y respuestas rápidas

- **¿Por qué no usar solo EAR sin PERCLOS?** Porque EAR es instantáneo
  (un solo frame) y no distingue un parpadeo normal de un microsueño; PERCLOS
  agrega la dimensión temporal necesaria para esa distinción.
- **¿Funciona con lentes?** Sí en general, porque MediaPipe detecta
  landmarks sobre toda la imagen, no solo el ojo "desnudo". Lentes oscuros
  o reflejos de luz directa sí pueden afectar la precisión.
- **¿Por qué no se usó head pose (inclinación de cabeza)?** Se evaluó, pero
  estimarlo con precisión requiere calibración de cámara (matriz
  intrínseca); sin eso, el resultado con landmarks 2D es ruidoso. Queda como
  trabajo futuro.
- **¿Por qué 30 FPS / 45 frames de ventana?** Es el FPS típico de una
  webcam estándar; la ventana de 45 frames equivale a 1.5 segundos reales,
  un tiempo razonable para diferenciar fatiga sostenida de un parpadeo.
