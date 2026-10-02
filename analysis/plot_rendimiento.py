"""Gráficos de rendimiento: tiempos, speedup y eficiencia (siempre con medianas).

Uso:   python analysis/analyze.py            (antes, para generar las tablas)
       python analysis/plot_rendimiento.py

Figuras (una por sistema salvo la última):
    serial_versiones_<sistema>   costo por muestra de V0, V1 y V2
    tiempo_vs_p_<sistema>        tiempo mediano de mpi_v2 en función de P
    speedup_<sistema>            speedup de mpi_v2 en función de P, para cada N
    speedup_v0_v2_<sistema>      speedup de la versión ingenua frente a la final
    arranque_<sistema>           tiempo de cómputo frente a tiempo total del lanzamiento
    eficiencia_sistemas          eficiencia de mpi_v2, comparando los sistemas medidos
"""
import matplotlib.pyplot as plt
import numpy as np

from common import (AQUA, AXIS, BLUE, INK_SECONDARY, MUTED, ORANGE, SEQUENTIAL_BLUE, SYMBOL,
                    SYSTEM_COLORS, VERSION_COLOR, apply_style, load_summary, physical_cores,
                    power_label, save)

CONSTANTS = ["pi", "e"]


def wide_sweep(p_values):
    """True si el barrido llega a muchos procesos (más de 32).

    En ese caso los gráficos usan escala logarítmica en P: en escala lineal los puntos
    1, 2, 4 y 8 quedarían amontonados. En log-log el speedup ideal S = P sigue siendo una recta.
    """
    return max(p_values) > 32


def set_p_axis(ax, p_values, log=False):
    """Eje horizontal para P, con una marca por cada valor medido.

    Lineal por defecto (así el speedup ideal S = P es una recta); logarítmico para los
    tiempos y para los barridos con muchos procesos.
    """
    if log or wide_sweep(p_values):
        ax.set_xscale("log", base=2)
    ax.set_xticks(p_values)
    ax.set_xticklabels([str(p) for p in p_values])
    ax.minorticks_off()
    ax.set_xlabel("P (procesos MPI)")


def mark_physical_cores(ax, system, p_values):
    """Línea vertical donde se acaban los núcleos físicos (más allá, P usa hilos lógicos)."""
    cores = physical_cores(system)
    if cores is not None and min(p_values) < cores < max(p_values):
        ax.axvline(cores, color=MUTED, linewidth=1, linestyle=":")
        ax.text(cores, 0.02, f" {cores} núcleos físicos", transform=ax.get_xaxis_transform(),
                fontsize=8.5, color=INK_SECONDARY, ha="left", va="bottom")


def set_speedup_axis(ax, p_values):
    """Eje vertical del speedup: desde 0 en escala lineal, o logarítmico si el barrido es amplio."""
    if wide_sweep(p_values):
        ax.set_yscale("log", base=2)
        ax.set_yticks(p_values)
        ax.set_yticklabels([str(p) for p in p_values])
        ax.minorticks_off()
    else:
        ax.set_ylim(bottom=0)


def plot_serial_versions(gains, system):
    """Barras: nanosegundos por muestra de cada versión serial, en el mayor N medido para las tres."""
    data = gains[gains["system"] == system].dropna(subset=["t_v0", "t_v1", "t_v2"])
    if data.empty:
        return      # en este sistema no se midieron las tres versiones seriales
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    width = 0.25
    notes = []

    for group, constant in enumerate(CONSTANTS):
        rows = data[data["constant"] == constant]
        if rows.empty:
            continue
        row = rows.loc[rows["N"].idxmax()]
        notes.append(f"{SYMBOL[constant]}: N = {power_label(row['N'])}")
        for offset, version in enumerate(["v0", "v1", "v2"]):
            ns = row[f"t_{version}"] / row["N"] * 1e9
            x = group + (offset - 1) * (width + 0.02)
            ax.bar(x, ns, width=width, color=VERSION_COLOR[version],
                   label=f"serial_{version}" if group == 0 else None)
            ax.text(x, ns, f"{ns:.1f}", ha="center", va="bottom", fontsize=9, color=INK_SECONDARY)

    ax.set_xticks(range(len(CONSTANTS)))
    ax.set_xticklabels([f"Estimación de {SYMBOL[c]}" for c in CONSTANTS])
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Nanosegundos por muestra (mediana)")
    ax.set_title(f"Costo por muestra de cada versión serial — sistema: {system}\n" + "   ".join(notes))
    ax.legend(loc="upper right", ncol=3)
    ax.margins(y=0.15)
    fig.tight_layout()
    save(fig, f"serial_versiones_{system}")


def lines_by_n(ax, data, column, p_values, log=False):
    """Una línea por cada N, del azul claro (N chico) al azul oscuro (N grande)."""
    n_values = sorted(data["N"].unique())
    colors = SEQUENTIAL_BLUE[-len(n_values):] if len(n_values) <= len(SEQUENTIAL_BLUE) else SEQUENTIAL_BLUE
    for index, n in enumerate(n_values):
        rows = data[data["N"] == n].sort_values("P")
        ax.plot(rows["P"], rows[column], marker="o", color=colors[index % len(colors)],
                label=f"N = {power_label(n)}")
    set_p_axis(ax, p_values, log=log)


def plot_time_vs_p(speedup, system):
    data = speedup[(speedup["system"] == system) & (speedup["program"] == "mpi_v2")]
    p_values = sorted(data["P"].unique())
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3), sharey=True)

    for ax, constant in zip(axes, CONSTANTS):
        lines_by_n(ax, data[data["constant"] == constant], "t_median", p_values, log=True)
        ax.set_yscale("log")
        ax.set_title(f"Tiempo de mpi_v2 — {SYMBOL[constant]}")
        mark_physical_cores(ax, system, p_values)
    axes[0].set_ylabel("Tiempo mediano (s)")
    axes[1].legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.suptitle(f"Tiempo de ejecución en función de P — sistema: {system}", x=0.02, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    save(fig, f"tiempo_vs_p_{system}")


def plot_speedup(speedup, system):
    data = speedup[(speedup["system"] == system) & (speedup["program"] == "mpi_v2")]
    p_values = sorted(data["P"].unique())
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3), sharey=True)

    for ax, constant in zip(axes, CONSTANTS):
        ax.plot(p_values, p_values, color=MUTED, linestyle="--", linewidth=1.5, label="Ideal: S = P")
        lines_by_n(ax, data[data["constant"] == constant], "speedup", p_values)
        ax.set_title(f"Speedup de mpi_v2 — {SYMBOL[constant]}")
        set_speedup_axis(ax, p_values)
        mark_physical_cores(ax, system, p_values)
    axes[0].set_ylabel("Speedup  S = T serial / T con P procesos")
    axes[1].legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.suptitle(f"Speedup (con medianas) en función de P — sistema: {system}", x=0.02, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    save(fig, f"speedup_{system}")


def plot_speedup_v0_v2(speedup, system, serial_fraction=0.05):
    """Compara el escalado de la versión ingenua y de la final, en el mayor N medido para ambas."""
    data = speedup[speedup["system"] == system]
    if "mpi_v0" not in set(data["program"]):
        return      # en este sistema no se midió la versión ingenua
    p_values = sorted(data["P"].unique())
    p_line = np.linspace(min(p_values), max(p_values), 100)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3), sharey=True)

    for ax, constant in zip(axes, CONSTANTS):
        rows = data[data["constant"] == constant]
        common_n = set(rows[rows["program"] == "mpi_v0"]["N"]) & set(rows[rows["program"] == "mpi_v2"]["N"])
        if not common_n:
            continue
        n = max(common_n)
        ax.plot(p_line, p_line, color=MUTED, linestyle="--", linewidth=1.5, label="Ideal: S = P")
        amdahl = 1 / (serial_fraction + (1 - serial_fraction) / p_line)
        ax.plot(p_line, amdahl, color=MUTED, linestyle=":", linewidth=1.5,
                label=f"Ley de Amdahl con {serial_fraction:.0%} serial (referencia)")
        for program, color in [("mpi_v0", BLUE), ("mpi_v2", AQUA)]:
            line = rows[(rows["program"] == program) & (rows["N"] == n)].sort_values("P")
            ax.plot(line["P"], line["speedup"], marker="o", color=color, label=program)
        set_p_axis(ax, p_values)
        set_speedup_axis(ax, p_values)
        ax.set_title(f"{SYMBOL[constant]} con N = {power_label(n)}")
        mark_physical_cores(ax, system, p_values)
    axes[0].set_ylabel("Speedup")
    axes[1].legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.suptitle(f"Speedup de la versión ingenua y de la final — sistema: {system}", x=0.02, ha="left",
                 fontweight="bold")
    fig.tight_layout()
    save(fig, f"speedup_v0_v2_{system}")


def plot_startup(speedup, system):
    """Tiempo de cómputo cronometrado frente al tiempo total del lanzamiento (incluye MPI_Init)."""
    data = speedup[(speedup["system"] == system) & (speedup["program"] == "mpi_v2")
                   & (speedup["constant"] == "pi")]
    cores = physical_cores(system)
    p_values = sorted(data["P"].unique())
    p = max([value for value in p_values if cores is None or value <= cores] or p_values)
    rows = data[data["P"] == p].sort_values("N")

    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    ax.plot(rows["N"], rows["wall_median"], marker="o", color=ORANGE,
            label="Tiempo total del lanzamiento (mpirun completo)")
    ax.plot(rows["N"], rows["t_median"], marker="o", color=BLUE,
            label="Tiempo de cómputo cronometrado (MPI_Wtime)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("N (cantidad de muestras)")
    ax.set_ylabel("Tiempo mediano (s)")
    ax.set_title(f"Costo fijo de arrancar MPI — mpi_v2, π, P = {p} — sistema: {system}")
    ax.legend(loc="upper left")
    fig.tight_layout()
    save(fig, f"arranque_{system}")


def plot_efficiency_systems(speedup):
    """Eficiencia de mpi_v2 en el mayor N medido en todos los sistemas, una línea por sistema."""
    data = speedup[speedup["program"] == "mpi_v2"]
    systems = sorted(data["system"].unique())
    p_values = sorted(data["P"].unique())
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3), sharey=True)

    for ax, constant in zip(axes, CONSTANTS):
        rows = data[data["constant"] == constant]
        common_n = set.intersection(*[set(rows[rows["system"] == s]["N"]) for s in systems])
        n = max(common_n)
        ax.axhline(1.0, color=MUTED, linestyle="--", linewidth=1.5, label="Ideal: E = 1")
        for index, system in enumerate(systems):
            line = rows[(rows["system"] == system) & (rows["N"] == n)].sort_values("P")
            ax.plot(line["P"], line["efficiency"], marker="o",
                    color=SYSTEM_COLORS[index % len(SYSTEM_COLORS)], label=f"Sistema: {system}")
        set_p_axis(ax, p_values)
        ax.set_ylim(0, 1.25)
        ax.set_title(f"Eficiencia de mpi_v2 — {SYMBOL[constant]} con N = {power_label(n)}")
        ax.spines["bottom"].set_color(AXIS)
    axes[0].set_ylabel("Eficiencia  E = S / P")
    axes[1].legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.suptitle("Eficiencia paralela por sistema", x=0.02, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "eficiencia_sistemas")


def main():
    apply_style()
    gains = load_summary("ganancia_serial")
    speedup = load_summary("speedup")

    for system in sorted(speedup["system"].unique()):
        plot_serial_versions(gains, system)
        plot_time_vs_p(speedup, system)
        plot_speedup(speedup, system)
        plot_speedup_v0_v2(speedup, system)
        plot_startup(speedup, system)
    plot_efficiency_systems(speedup)


if __name__ == "__main__":
    main()
