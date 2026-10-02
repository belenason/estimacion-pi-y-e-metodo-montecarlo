"""Gráficos de convergencia y de error en función de N.

Uso:   python analysis/analyze.py            (antes, para generar las tablas)
       python analysis/plot_convergencia.py

Figuras:
    convergencia   cada estimación obtenida frente al valor real, con la banda teórica del 95 %
    error_vs_n     error en escala log-log, comparado con la recta teórica sigma / raíz(N)
"""
import matplotlib.pyplot as plt
import numpy as np

from common import (BLUE, INK, INK_SECONDARY, MUTED, ORANGE, SIGMA, SYMBOL, TRUE_VALUE,
                    apply_style, load_raw, load_summary, save)

COLOR = {"pi": BLUE, "e": ORANGE}


def estimates_v2(raw):
    """Estimaciones del generador final, sin contar dos veces la misma muestra."""
    runs = raw[raw["program"].isin(["serial_v2", "mpi_v2"])]
    return runs.drop_duplicates(subset=["program", "constant", "N", "P", "seed"])


def plot_convergence(runs):
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))

    for ax, constant in zip(axes, ["pi", "e"]):
        data = runs[runs["constant"] == constant]
        true = TRUE_VALUE[constant]
        n_line = np.logspace(np.log10(data["N"].min()) - 0.15, np.log10(data["N"].max()) + 0.15, 200)
        half_width = 1.96 * SIGMA[constant] / np.sqrt(n_line)

        ax.fill_between(n_line, true - half_width, true + half_width, color=COLOR[constant],
                        alpha=0.15, linewidth=0, label="Banda teórica del 95 %")
        ax.axhline(true, color=INK, linewidth=1.2, label=f"Valor real de {SYMBOL[constant]}")
        ax.scatter(data["N"], data["estimate"], s=14, color=COLOR[constant], linewidths=0,
                   alpha=0.75, label="Una estimación")

        ax.set_xscale("log")
        limit = 1.6 * 1.96 * SIGMA[constant] / np.sqrt(data["N"].min())
        ax.set_ylim(true - limit, true + limit)
        ax.set_xlabel("N (cantidad de muestras)")
        ax.set_ylabel(f"Estimación de {SYMBOL[constant]}")
        ax.set_title(f"Convergencia de la estimación de {SYMBOL[constant]}")
        ax.legend(loc="upper right")

    fig.tight_layout()
    save(fig, "convergencia")


def plot_error(runs, errors, slopes):
    fig, ax = plt.subplots(figsize=(7.2, 4.8))

    for constant in ["pi", "e"]:
        data = runs[runs["constant"] == constant]
        table = errors[errors["constant"] == constant]
        slope = float(slopes.loc[slopes["constant"] == constant, "slope"].iloc[0])
        color = COLOR[constant]

        # Cada punto tenue es el error de una ejecución; el punto grande resume todas las de ese N.
        ax.scatter(data["N"], data["abs_err"], s=10, color=color, alpha=0.25, linewidths=0)
        ax.plot(table["N"], table["theory_sigma_over_sqrtN"], color=color, linestyle="--", linewidth=1.5,
                label=f"{SYMBOL[constant]}: teoría σ/√N (σ = {SIGMA[constant]:.3f})")
        ax.plot(table["N"], table["rmse"], linestyle="none", marker="o", markersize=8, color=color,
                markeredgecolor="white", markeredgewidth=1.5,
                label=f"{SYMBOL[constant]}: error medido (pendiente {slope:.2f})")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("N (cantidad de muestras)")
    ax.set_ylabel("Error absoluto")
    ax.set_title("El error decae como 1/√N: pendiente −1/2 en escala log-log")
    ax.legend(loc="upper right")
    ax.text(0.02, 0.04, "Puntos tenues: error de cada ejecución individual.\n"
            "Puntos grandes: error cuadrático medio de todas las ejecuciones con ese N.",
            transform=ax.transAxes, fontsize=8.5, color=INK_SECONDARY, va="bottom")
    ax.tick_params(which="minor", color=MUTED)
    fig.tight_layout()
    save(fig, "error_vs_n")


def main():
    apply_style()
    runs = estimates_v2(load_raw())
    plot_convergence(runs)
    plot_error(runs, load_summary("errores"), load_summary("pendientes"))


if __name__ == "__main__":
    main()
