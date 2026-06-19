import datetime

import matplotlib.pyplot as plt


def save_session_report(timestamps, ear_log, perclos_log, state_log, microsleep_count,
                         output_path=None):
    if not timestamps:
        return None

    output_path = output_path or f"reporte_sesion_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"

    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    axes[0].plot(timestamps, ear_log, color="tab:blue", label="EAR")
    axes[0].axhline(0.21, color="gray", linestyle="--", linewidth=1, label="Umbral ojos cerrados")
    axes[0].set_ylabel("EAR")
    axes[0].legend(loc="upper right")
    axes[0].set_title(f"Resumen de sesion - microsuenos detectados: {microsleep_count}")

    axes[1].plot(timestamps, [p * 100 for p in perclos_log], color="tab:orange", label="PERCLOS (%)")
    state_colors = {"GREEN": "tab:green", "YELLOW": "gold", "RED": "tab:red"}
    for t, s in zip(timestamps, state_log):
        axes[1].axvspan(t, t + 0.04, color=state_colors.get(s, "white"), alpha=0.15, linewidth=0)
    axes[1].set_ylabel("PERCLOS (%)")
    axes[1].set_xlabel("Tiempo (s)")
    axes[1].legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path
