"""Constantes, estilo y funciones compartidas por los scripts de análisis y gráficos."""
import math
import os
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # genera archivos sin abrir ventanas
import matplotlib.pyplot as plt
import pandas as pd

# --- Carpetas -----------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", ROOT / "results"))
RAW_DIR = RESULTS_DIR / "raw"
SUMMARY_DIR = RESULTS_DIR / "summary"
FIG_DIR = RESULTS_DIR / "figures"
SYSINFO_DIR = RESULTS_DIR / "sysinfo"

# --- Valores teóricos ---------------------------------------------------------
TRUE_VALUE = {"pi": math.pi, "e": math.e}
SYMBOL = {"pi": "π", "e": "e"}

# Desvío estándar de UNA muestra de cada estimador (ver la teoría del proyecto):
#   pi: 4 * Bernoulli(p) con p = pi/4      e: cantidad de sumandos hasta superar 1
_P = math.pi / 4
SIGMA = {"pi": 4 * math.sqrt(_P * (1 - _P)), "e": math.sqrt(3 * math.e - math.e**2)}

# --- Colores (paleta validada para daltonismo; el orden es fijo) ---------------
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
VERSION_COLOR = {"v0": BLUE, "v1": ORANGE, "v2": AQUA}
SYSTEM_COLORS = [BLUE, ORANGE, AQUA, YELLOW]
# Un solo tono de claro a oscuro, para series ordenadas por tamaño (N creciente).
SEQUENTIAL_BLUE = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]

INK, INK_SECONDARY, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"


def apply_style():
    """Estilo común: fondo claro, grilla tenue, líneas de 2 px, sin marcos superiores."""
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
        "font.size": 10,
        "text.color": INK,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelcolor": INK_SECONDARY,
        "axes.edgecolor": AXIS,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": AXIS,
        "ytick.color": AXIS,
        "xtick.labelcolor": INK_SECONDARY,
        "ytick.labelcolor": INK_SECONDARY,
        "lines.linewidth": 2,
        "lines.markersize": 6,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "mathtext.default": "regular",
    })


def save(fig, name):
    """Guarda la figura en PNG (para diapositivas) y PDF (para el informe)."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png", dpi=200, bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  figura: {FIG_DIR / (name + '.png')}")


def load_raw():
    """Lee y une todos los CSV de results/raw (uno por sistema)."""
    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise SystemExit(f"No hay archivos CSV en {RAW_DIR}. Ejecutar antes scripts/run_benchmark.sh")
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def load_summary(name):
    """Lee una tabla generada por analyze.py."""
    path = SUMMARY_DIR / f"{name}.csv"
    if not path.exists():
        raise SystemExit(f"Falta {path}. Ejecutar antes: python analysis/analyze.py")
    return pd.read_csv(path)


def physical_cores(system):
    """Núcleos físicos del sistema, leídos de results/sysinfo/<sistema>.txt (None si no está)."""
    path = SYSINFO_DIR / f"{system}.txt"
    if path.exists():
        match = re.search(r"Núcleos físicos:\s*(\d+)", path.read_text(encoding="utf-8"))
        if match:
            return int(match.group(1))
    return None


def power_label(n):
    """Escribe 1000000 como 10^6 (en notación matemática) cuando N es potencia exacta de 10."""
    exponent = round(math.log10(n))
    if 10**exponent == n:
        return f"$10^{{{exponent}}}$"
    return f"{n:.3g}"
