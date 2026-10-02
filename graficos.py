"""Calcula las métricas y genera los gráficos del proyecto.

Uso:   python graficos.py

Lee todos los archivos resultados/tiempos_<sistema>.csv que haya (uno por
sistema medido) y genera en resultados/:

    resumen.csv              mediana del tiempo, speedup y eficiencia
    intuicion.png            cómo funcionan los dos experimentos
    convergencia.png         las estimaciones se acercan al valor real al crecer N
    error.png                el error baja como 1/raíz(N)
    tiempo_<sistema>.png     tiempo en función de la cantidad de procesos
    speedup_<sistema>.png    speedup en función de la cantidad de procesos
    eficiencia.png           eficiencia, comparando los sistemas
"""
import glob
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CARPETA = "resultados"
REAL = {"pi": math.pi, "e": math.e}
NOMBRE = {"pi": "π", "e": "e"}

# Desvío estándar teórico de una muestra de cada estimador.
# pi: 4 * Bernoulli(p) con p = pi/4.   e: cantidad de sumandos, varianza 3e - e^2.
P_CIRCULO = math.pi / 4
SIGMA = {"pi": 4 * math.sqrt(P_CIRCULO * (1 - P_CIRCULO)),
         "e": math.sqrt(3 * math.e - math.e ** 2)}

AZUL, NARANJA, GRIS = "#2a78d6", "#eb6834", "#898781"
AZULES = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]

plt.rcParams.update({"axes.grid": True, "axes.axisbelow": True, "grid.color": "#e1e0d9", "axes.spines.top": False,
                     "axes.spines.right": False, "lines.linewidth": 2, "legend.frameon": False})


def cargar_datos():
    """Une los CSV de todos los sistemas en una sola tabla."""
    tablas = []
    for archivo in sorted(glob.glob(os.path.join(CARPETA, "tiempos_*.csv"))):
        tabla = pd.read_csv(archivo)
        tabla["sistema"] = os.path.basename(archivo)[len("tiempos_"):-len(".csv")]
        tablas.append(tabla)
    if not tablas:
        raise SystemExit("No hay resultados. Correr antes ./benchmark.sh <sistema>")
    return pd.concat(tablas, ignore_index=True)


def calcular_resumen(datos):
    """Mediana del tiempo de cada configuración, speedup y eficiencia."""
    medianas = (datos.groupby(["sistema", "programa", "constante", "N", "P"])["tiempo_s"]
                .median().reset_index().rename(columns={"tiempo_s": "t_mediana"}))

    serial = medianas[medianas["programa"] == "serial"]
    serial = serial[["sistema", "constante", "N", "t_mediana"]].rename(columns={"t_mediana": "t_serial"})

    resumen = medianas[medianas["programa"] == "mpi"].merge(serial, on=["sistema", "constante", "N"])
    resumen["speedup"] = resumen["t_serial"] / resumen["t_mediana"]     # S = T_serial / T_P
    resumen["eficiencia"] = resumen["speedup"] / resumen["P"]           # E = S / P
    return resumen.sort_values(["sistema", "constante", "N", "P"])


def potencia(n):
    return f"$10^{{{round(math.log10(n))}}}$"


def eje_de_procesos(eje, procesos):
    """Marca en el eje horizontal los valores de P medidos.

    Con pocos procesos se usa escala lineal. Si el barrido llega a muchos procesos
    (más de 32) se usa escala logarítmica, porque en escala lineal los puntos
    1, 2, 4 y 8 quedarían amontonados. Devuelve True si usó escala logarítmica.
    """
    logaritmico = max(procesos) > 32
    if logaritmico:
        eje.set_xscale("log", base=2)
    eje.set_xticks(procesos)
    eje.set_xticklabels([str(p) for p in procesos])
    eje.minorticks_off()
    eje.set_xlabel("P (procesos)")
    return logaritmico


def grafico_intuicion():
    """Los dos experimentos, con pocas muestras para que se vean."""
    rng = np.random.default_rng(1)
    fig, (izq, der) = plt.subplots(1, 2, figsize=(11, 5))

    x, y = rng.random(2000), rng.random(2000)
    dentro = x * x + y * y <= 1
    izq.scatter(x[dentro], y[dentro], s=6, color=AZUL, label=f"Dentro: {dentro.sum()}")
    izq.scatter(x[~dentro], y[~dentro], s=6, color=NARANJA, label=f"Fuera: {(~dentro).sum()}")
    angulo = np.linspace(0, np.pi / 2, 100)
    izq.plot(np.cos(angulo), np.sin(angulo), color="black", linewidth=1.5)
    izq.set_aspect("equal")
    izq.grid(False)
    izq.set_title(f"π ≈ 4 × {dentro.sum()} / 2000 = {4 * dentro.sum() / 2000:.3f}")
    izq.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=2, markerscale=2)

    # Cada fila es un ensayo: la cantidad de sumandos es la posición donde la suma acumulada pasa de 1.
    sumas = rng.random((100000, 15)).cumsum(axis=1)
    cantidad = (sumas > 1).argmax(axis=1) + 1
    valores = np.arange(2, 8)
    der.bar(valores, [(cantidad == v).mean() for v in valores], color=AZUL, label="Observado")
    der.plot(valores, [(v - 1) / math.factorial(v) for v in valores], "o", color="black",
             label="Teórico: (n − 1) / n!")
    der.set_xlabel("Cantidad de números hasta que la suma supera 1")
    der.set_ylabel("Proporción de ensayos")
    der.set_title(f"e ≈ promedio de la cantidad = {cantidad.mean():.3f}")
    der.legend()

    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA, "intuicion.png"), dpi=150)
    plt.close(fig)


def grafico_convergencia(datos):
    fig, ejes = plt.subplots(1, 2, figsize=(11, 4.5))
    for eje, constante, color in zip(ejes, ["pi", "e"], [AZUL, NARANJA]):
        d = datos[datos["constante"] == constante]
        eje.scatter(d["N"], d["estimacion"], s=12, color=color, alpha=0.6, label="Estimaciones")
        eje.axhline(REAL[constante], color="black", linewidth=1.2, label="Valor real")
        margen = 4 * SIGMA[constante] / math.sqrt(d["N"].min())
        eje.set_ylim(REAL[constante] - margen, REAL[constante] + margen)
        eje.set_xscale("log")
        eje.set_xlabel("N (cantidad de muestras)")
        eje.set_ylabel(f"Estimación de {NOMBRE[constante]}")
        eje.set_title(f"Convergencia de {NOMBRE[constante]}")
        eje.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA, "convergencia.png"), dpi=150)
    plt.close(fig)


def grafico_error(datos):
    """Error medido contra la recta teórica sigma / raíz(N), en escala log-log."""
    fig, eje = plt.subplots(figsize=(7, 5))
    for constante, color in zip(["pi", "e"], [AZUL, NARANJA]):
        d = datos[datos["constante"] == constante]
        # Raíz del error cuadrático medio de todas las ejecuciones con cada N
        error = d.groupby("N")["error_abs"].apply(lambda e: math.sqrt((e ** 2).mean()))
        pendiente = np.polyfit(np.log10(error.index), np.log10(error.values), 1)[0]
        eje.plot(error.index, SIGMA[constante] / np.sqrt(error.index), "--", color=color,
                 linewidth=1.5, label=f"{NOMBRE[constante]}: teoría σ/√N")
        eje.plot(error.index, error.values, "o", color=color, markersize=8,
                 label=f"{NOMBRE[constante]}: medido (pendiente {pendiente:.2f})")
        print(f"Pendiente del error de {constante}: {pendiente:.3f} (teoría: -0.5)")
    eje.set_xscale("log")
    eje.set_yscale("log")
    eje.set_xlabel("N (cantidad de muestras)")
    eje.set_ylabel("Error absoluto")
    eje.set_title("El error baja como 1/√N")
    eje.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA, "error.png"), dpi=150)
    plt.close(fig)


def grafico_por_procesos(resumen, sistema, columna, etiqueta, archivo):
    """Tiempo o speedup en función de P: un panel por constante y una línea por cada N."""
    r = resumen[resumen["sistema"] == sistema]
    procesos = sorted(r["P"].unique())
    fig, ejes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for eje, constante in zip(ejes, ["pi", "e"]):
        if columna == "speedup":
            eje.plot(procesos, procesos, "--", color=GRIS, linewidth=1.5, label="Ideal")
        tamanios = sorted(r["N"].unique())
        for n, color in zip(tamanios, AZULES[-len(tamanios):]):
            linea = r[(r["constante"] == constante) & (r["N"] == n)]
            eje.plot(linea["P"], linea[columna], "o-", color=color, label=f"N = {potencia(n)}")
        logaritmico = eje_de_procesos(eje, procesos)
        if columna == "t_mediana":
            eje.set_yscale("log")
        elif logaritmico:
            # Speedup en escala log-log: el ideal S = P sigue siendo una recta.
            eje.set_yscale("log", base=2)
            eje.set_yticks(procesos)
            eje.set_yticklabels([str(p) for p in procesos])
            eje.minorticks_off()
        eje.set_title(f"{NOMBRE[constante]} — sistema: {sistema}")
    ejes[0].set_ylabel(etiqueta)
    ejes[1].legend(loc="center left", bbox_to_anchor=(1, 0.5))
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA, archivo), dpi=150)
    plt.close(fig)


def grafico_eficiencia(resumen):
    """Eficiencia con el N más grande medido en todos los sistemas, una línea por sistema."""
    sistemas = sorted(resumen["sistema"].unique())
    n = min(resumen[resumen["sistema"] == s]["N"].max() for s in sistemas)
    fig, ejes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for eje, constante in zip(ejes, ["pi", "e"]):
        eje.axhline(1, linestyle="--", color=GRIS, linewidth=1.5, label="Ideal")
        for sistema, color in zip(sistemas, [AZUL, NARANJA, "#1baf7a"]):
            linea = resumen[(resumen["sistema"] == sistema) & (resumen["constante"] == constante)
                            & (resumen["N"] == n)]
            eje.plot(linea["P"], linea["eficiencia"], "o-", color=color, label=sistema)
        eje.set_ylim(0, 1.3)
        eje_de_procesos(eje, sorted(resumen["P"].unique()))
        eje.set_title(f"Eficiencia — {NOMBRE[constante]} con N = {potencia(n)}")
    ejes[0].set_ylabel("Eficiencia = speedup / P")
    ejes[1].legend(loc="center left", bbox_to_anchor=(1, 0.5))
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA, "eficiencia.png"), dpi=150)
    plt.close(fig)


def main():
    datos = cargar_datos()
    resumen = calcular_resumen(datos)
    resumen.to_csv(os.path.join(CARPETA, "resumen.csv"), index=False, float_format="%.4f")
    print(resumen.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    grafico_intuicion()
    grafico_convergencia(datos)
    grafico_error(datos)
    for sistema in sorted(resumen["sistema"].unique()):
        grafico_por_procesos(resumen, sistema, "t_mediana", "Tiempo mediano (s)", f"tiempo_{sistema}.png")
        grafico_por_procesos(resumen, sistema, "speedup", "Speedup = T serial / T paralelo",
                             f"speedup_{sistema}.png")
    grafico_eficiencia(resumen)
    print(f"Gráficos guardados en {CARPETA}/")


if __name__ == "__main__":
    main()
