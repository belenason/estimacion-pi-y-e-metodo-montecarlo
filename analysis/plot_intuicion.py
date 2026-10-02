"""Gráficos de intuición: qué hace cada experimento de Monte Carlo.

Uso:   python analysis/plot_intuicion.py

No usa los resultados de los benchmarks: genera sus propias muestras con numpy.
Figuras:
    intuicion_pi   puntos al azar dentro y fuera del cuarto de círculo
    intuicion_e    cuántos números uniformes hacen falta para que la suma supere 1
"""
import math

import matplotlib.pyplot as plt
import numpy as np

from common import AXIS, BLUE, INK, INK_SECONDARY, ORANGE, SURFACE, apply_style, save

SEED = 2024


def plot_pi(points=3000):
    rng = np.random.default_rng(SEED)
    x = rng.random(points)
    y = rng.random(points)
    inside = x * x + y * y <= 1.0
    hits = int(inside.sum())
    estimate = 4 * hits / points

    fig, ax = plt.subplots(figsize=(5.4, 5.6))
    ax.scatter(x[inside], y[inside], s=7, color=BLUE, linewidths=0, label=f"Dentro: {hits}")
    ax.scatter(x[~inside], y[~inside], s=7, color=ORANGE, linewidths=0, label=f"Fuera: {points - hits}")

    angle = np.linspace(0, np.pi / 2, 200)
    ax.plot(np.cos(angle), np.sin(angle), color=INK, linewidth=1.5)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(f"Estimación de π con {points} puntos al azar\n"
                 f"π ≈ 4 × {hits} / {points} = {estimate:.4f}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, markerscale=2.5)
    save(fig, "intuicion_pi")


def plot_e(trials=100_000, max_draws=12):
    rng = np.random.default_rng(SEED)
    # Cada fila es un ensayo: sumas acumuladas de uniformes. La cantidad de sumandos
    # necesarios es la posición de la primera suma acumulada que supera 1.
    sums = rng.random((trials, max_draws)).cumsum(axis=1)
    draws = (sums > 1.0).argmax(axis=1) + 1
    estimate = draws.mean()

    values = np.arange(2, 8)
    empirical = np.array([(draws == n).mean() for n in values])
    theory = np.array([(n - 1) / math.factorial(n) for n in values])

    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    bars = ax.bar(values, empirical, width=0.62, color=BLUE, label="Frecuencia observada")
    ax.plot(values, theory, linestyle="none", marker="o", markersize=7, color=INK,
            markeredgecolor=SURFACE, markeredgewidth=1.5, label="Probabilidad teórica (n − 1) / n!")
    for bar, value in zip(bars, empirical):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.012, f"{value:.3f}",
                ha="center", va="bottom", fontsize=9, color=INK_SECONDARY)

    ax.set_xticks(values)
    ax.set_ylim(0, 0.58)
    ax.grid(axis="x", visible=False)
    ax.spines["bottom"].set_color(AXIS)
    ax.set_xlabel("Cantidad de números uniformes hasta que la suma supera 1")
    ax.set_ylabel("Proporción de ensayos")
    ax.set_title(f"Estimación de e con {trials:,} ensayos\n".replace(",", ".")
                 + f"e ≈ promedio de la cantidad = {estimate:.4f}")
    ax.legend(loc="upper right")
    save(fig, "intuicion_e")


def main():
    apply_style()
    plot_pi()
    plot_e()


if __name__ == "__main__":
    main()
