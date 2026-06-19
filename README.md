# 😴 Sistema de Detección de Somnolencia al Volante

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.12-5C3EE8?logo=opencv&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.14-00B6FF?logo=google&logoColor=white)
![Estado](https://img.shields.io/badge/Estado-Funcional-success)
![Plataforma](https://img.shields.io/badge/Plataforma-Windows-0078D6?logo=windows&logoColor=white)

> Sistema de visión computacional que usa **una webcam común** para detectar
> en tiempo real signos de fatiga y microsueño en un conductor, y emite
> alertas visuales, sonoras y de voz **antes** de que ocurra un accidente.

Proyecto del Laboratorio 03 — Visión Computacional (Maestría, Ciclo IV) —
inspirado en accidentes de tránsito reales causados por conductores que se
quedan dormidos al volante.

📄 Para el detalle técnico profundo del algoritmo y la arquitectura interna,
ver **[ARQUITECTURA.md](ARQUITECTURA.md)**.

---

## 🎬 Demo

```
┌──────────────────────────────────────────────┐
│  🟢 FATIGA   ╭─ EAR en vivo ─╮                │
│   ╭───╮      │  ╱╲    ╱╲     │                │
│   │15%│      │ ╱  ╲  ╱  ╲    │   [tu cara]    │
│   ╰───╯      ╰────────────╯                  │
├──────────────────────────────────────────────┤
│ ALERTA: NORMAL                                │
│ EAR:0.29  MAR:0.21  PERCLOS:15%  Microsuenos:0│
└──────────────────────────────────────────────┘
```

El sistema dibuja un **HUD estilo tablero deportivo** sobre el video en
vivo: un gauge circular de "fatiga" (PERCLOS), un mini-gráfico tipo
electrocardiograma del EAR, y una barra de estado que cambia de
🟢 Verde → 🟡 Amarillo → 🔴 Rojo según el nivel de somnolencia detectado.

---

## ❓ ¿Cómo funciona? (resumen)

1. La webcam captura tu rostro frame por frame.
2. **MediaPipe Face Mesh** localiza 468 puntos faciales (ojos, boca, contorno).
3. Se calculan dos métricas geométricas: **EAR** (qué tan abiertos están tus
   ojos) y **MAR** (qué tan abierta está tu boca, para detectar bostezos).
4. Una métrica acumulada, **PERCLOS**, mide qué porcentaje del último 1.5
   segundos tuviste los ojos cerrados.
5. Una máquina de estados decide el nivel de alerta (verde/amarillo/rojo)
   con histéresis, para no disparar falsas alarmas por un parpadeo normal.
6. Si el nivel sube, el sistema **suena una alarma y habla** ("Despierta,
   toma un descanso ahora"), y al cerrar la app genera un **reporte gráfico**
   de toda la sesión.

¿Quieres saber el detalle matemático y de diseño de cada paso? → 
**[ARQUITECTURA.md](ARQUITECTURA.md)**

---

## 🧰 Tecnologías y librerías

| Tecnología | Rol en el proyecto |
|---|---|
| [Python 3.11](https://www.python.org/) | Lenguaje del proyecto |
| [OpenCV](https://opencv.org/) | Captura de la webcam y dibujo del HUD sobre el video |
| [MediaPipe](https://ai.google.dev/edge/mediapipe) (Face Mesh) | Detección de 468 landmarks faciales en tiempo real |
| [NumPy](https://numpy.org/) | Soporte numérico |
| [Matplotlib](https://matplotlib.org/) | Generación del reporte gráfico al cerrar la sesión |
| [pyttsx3](https://pypi.org/project/pyttsx3/) | Síntesis de voz offline para las alertas habladas |
| `winsound` (estándar de Python en Windows) | Beeps de alarma sin dependencias externas |

---

## 📁 Estructura del repositorio

```
.
├── main.py             # punto de entrada: loop de la webcam
├── landmarks.py         # wrapper de MediaPipe Face Mesh
├── metrics.py           # cálculo de EAR, MAR y PERCLOS
├── alert_engine.py       # máquina de estados verde/amarillo/rojo
├── hud_overlay.py        # dibuja el HUD sobre el video
├── audio_voice.py        # alarma sonora + voz (en hilos)
├── session_report.py     # genera el PNG resumen al cerrar
├── requirements.txt
├── ARQUITECTURA.md        # documentación técnica profunda
└── trabajo.md             # enunciado original del laboratorio
```

---

## 🚀 Instalación

> Requiere Python 3.11 (MediaPipe tiene los wheels más estables en esa
> versión sobre Windows).

```bash
git clone https://github.com/chris2009/Sistema_de_Deteccion_de_Somnolencia_al_Volante.git
cd Sistema_de_Deteccion_de_Somnolencia_al_Volante

py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r requirements.txt
```

## ▶️ Uso

```bash
python main.py
```

- Se abre una ventana con tu webcam y el HUD superpuesto.
- Presiona **`q`** para salir.
- Al cerrar, se genera automáticamente `reporte_sesion_<fecha>.png` con el
  resumen de tu sesión (EAR, PERCLOS y microsueños detectados en el tiempo).

### Ajustar la sensibilidad

Los umbrales (qué tan cerrados deben estar los ojos, cuánto tiempo, etc.) se
configuran en `alert_engine.py`. Ver la tabla completa de parámetros en
[ARQUITECTURA.md](ARQUITECTURA.md#parámetros-configurables).

---

## 🎯 Contexto del proyecto

- **Problema:** accidentes de tránsito causados por microsueños al volante.
- **ODS relacionados:** ODS 3 (Salud y bienestar, meta 3.6 — reducir muertes
  por accidentes de tráfico) y ODS 11 (Ciudades sostenibles, meta 11.2 —
  transporte seguro).
- **Enfoque:** una solución de bajo costo, que solo requiere una laptop con
  webcam, sin hardware adicional.

## ⚠️ Limitaciones conocidas

- Lentes normales funcionan bien; lentes oscuros/de sol degradan la
  precisión.
- Poca luz o luz muy lateral reduce la calidad de la detección.
- No estima la inclinación de cabeza (head pose) — queda como trabajo futuro.
- Pensado para un solo conductor a la vez (`max_num_faces=1`).

Detalle completo en [ARQUITECTURA.md](ARQUITECTURA.md#limitaciones-conocidas).

## 📚 Referencias

- Soukupová & Čech (2016) — *Real-Time Eye Blink Detection using Facial
  Landmarks.*
- Dinges & Grace (1998) — *PERCLOS: A valid psychophysiological measure of
  alertness.*
- [MediaPipe Face Landmarker — Google AI Edge](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker)
- [Objetivos de Desarrollo Sostenible — ONU](https://www.un.org/sustainabledevelopment/es/)
