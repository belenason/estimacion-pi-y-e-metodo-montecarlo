"""Procesa los CSV crudos de los benchmarks y calcula las métricas del proyecto.

Uso:   python analysis/analyze.py

Lee    results/raw/*.csv        (una fila por ejecución)
Escribe results/summary/
    tiempos.csv          mediana, mínimo y máximo del tiempo por configuración
    ganancia_serial.csv  cuánto mejora cada versión serial respecto de la anterior
    speedup.csv          speedup y eficiencia de las versiones MPI
    errores.csv          error de las estimaciones en función de N
    pendientes.csv       pendiente ajustada de la recta log(error) vs log(N)
    tablas.md            las mismas tablas en Markdown, listas para el informe

Fórmulas:
    T_mediana = mediana de los tiempos de las repeticiones
    S_p       = T_serial,mediana / T_p,mediana      (speedup)
    E_p       = S_p / P                             (eficiencia)
    error abs = |estimación - valor real|           error rel = error abs / valor real
"""
import numpy as np
import pandas as pd

from common import SIGMA, SUMMARY_DIR, TRUE_VALUE, load_raw

CONFIG = ["system", "program", "constant", "N", "P"]


def median_times(raw):
    """Mediana (y dispersión) del tiempo de cada configuración."""
    return (
        raw.groupby(CONFIG)
        .agg(
            reps=("time_s", "size"),
            t_median=("time_s", "median"),
            t_min=("time_s", "min"),
            t_max=("time_s", "max"),
            wall_median=("wall_s", "median"),
        )
        .reset_index()
    )


def serial_gains(times):
    """Tabla con el tiempo mediano de V0, V1 y V2 y la ganancia entre versiones."""
    serial = times[times["program"].str.startswith("serial_")]
    table = serial.pivot_table(index=["system", "constant", "N"], columns="program", values="t_median")
    table = table.rename(columns=lambda name: name.replace("serial_", "t_")).reset_index()
    table["gain_v0_v1"] = table["t_v0"] / table["t_v1"]
    table["gain_v1_v2"] = table["t_v1"] / table["t_v2"]
    table["gain_v0_v2"] = table["t_v0"] / table["t_v2"]
    table["ns_per_sample_v2"] = table["t_v2"] / table["N"] * 1e9
    return table


def speedup_table(times):
    """Speedup y eficiencia de cada versión MPI contra la versión serial equivalente."""
    serial = times[times["program"].str.startswith("serial_")].copy()
    serial["version"] = serial["program"].str.replace("serial_", "")
    serial = serial[["system", "version", "constant", "N", "t_median"]].rename(columns={"t_median": "t_serial"})

    mpi = times[times["program"].str.startswith("mpi_")].copy()
    mpi["version"] = mpi["program"].str.replace("mpi_", "")

    table = mpi.merge(serial, on=["system", "version", "constant", "N"], how="left")
    table["speedup"] = table["t_serial"] / table["t_median"]
    table["efficiency"] = table["speedup"] / table["P"]
    # Tiempo de arranque de MPI: lo que tarda el lanzamiento completo menos el cómputo cronometrado.
    table["startup_s"] = table["wall_median"] - table["t_median"]
    columns = ["system", "program", "constant", "N", "P", "reps", "t_serial", "t_median",
               "t_min", "t_max", "speedup", "efficiency", "wall_median", "startup_s"]
    return table[columns].sort_values(["system", "program", "constant", "N", "P"])


def error_table(raw):
    """Error de las estimaciones del generador final (serial_v2 y mpi_v2) para cada N.

    La estimación depende solo de (programa, N, P, semilla), no del sistema: las filas
    repetidas entre sistemas son la misma muestra y se cuentan una sola vez.
    """
    runs = raw[raw["program"].isin(["serial_v2", "mpi_v2"])]
    runs = runs.drop_duplicates(subset=["program", "constant", "N", "P", "seed"])

    rows = []
    for (constant, n), group in runs.groupby(["constant", "N"]):
        errors = group["abs_err"].to_numpy()
        rmse = float(np.sqrt(np.mean(errors**2)))
        rows.append({
            "constant": constant,
            "N": n,
            "runs": len(errors),
            "mean_abs_err": float(errors.mean()),
            "rmse": rmse,
            "rel_rmse": rmse / TRUE_VALUE[constant],
            "theory_sigma_over_sqrtN": SIGMA[constant] / np.sqrt(n),
        })
    table = pd.DataFrame(rows)
    table["rmse_over_theory"] = table["rmse"] / table["theory_sigma_over_sqrtN"]
    return table.sort_values(["constant", "N"])


def fitted_slopes(errors):
    """Pendiente de la recta log10(error) = a + b * log10(N). La teoría predice b = -1/2."""
    rows = []
    for constant, group in errors.groupby("constant"):
        slope, intercept = np.polyfit(np.log10(group["N"]), np.log10(group["rmse"]), 1)
        rows.append({"constant": constant, "slope": slope, "sigma_fitted": 10**intercept,
                     "sigma_theory": SIGMA[constant]})
    return pd.DataFrame(rows)


def to_markdown(table, formats=None):
    """Convierte una tabla en texto Markdown. 'formats' indica cómo escribir cada columna."""
    formats = formats or {}
    lines = ["| " + " | ".join(table.columns) + " |", "|" + "---|" * len(table.columns)]
    for _, row in table.iterrows():
        cells = []
        for column in table.columns:
            value = row[column]
            if pd.isna(value):
                cells.append("—")
            elif column in formats:
                cells.append(formats[column].format(value))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_markdown(times, gains, speedup, errors, slopes):
    """Escribe results/summary/tablas.md con todas las tablas del informe."""
    out = ["# Tablas de resultados", "",
           "Generado por `analysis/analyze.py`. Los tiempos son medianas, en segundos.", ""]

    out += ["## 1. Versiones seriales: tiempo mediano y ganancia", ""]
    out.append(to_markdown(gains, {
        "t_v0": "{:.4f}", "t_v1": "{:.4f}", "t_v2": "{:.4f}",
        "gain_v0_v1": "{:.2f}x", "gain_v1_v2": "{:.2f}x", "gain_v0_v2": "{:.2f}x",
        "ns_per_sample_v2": "{:.2f}",
    }))
    out.append("")

    out += ["## 2. Versiones MPI: tiempo, speedup y eficiencia", ""]
    for (system, program, constant), group in speedup.groupby(["system", "program", "constant"]):
        out += [f"### {program} — {constant} — sistema `{system}`", ""]
        columns = ["N", "P", "t_serial", "t_median", "t_min", "t_max", "speedup", "efficiency", "startup_s"]
        out.append(to_markdown(group[columns], {
            "t_serial": "{:.4f}", "t_median": "{:.4f}", "t_min": "{:.4f}", "t_max": "{:.4f}",
            "speedup": "{:.2f}", "efficiency": "{:.2f}", "startup_s": "{:.3f}",
        }))
        out.append("")

    out += ["## 3. Error de la estimación en función de N (serial_v2 y mpi_v2)", ""]
    out.append(to_markdown(errors, {
        "mean_abs_err": "{:.2e}", "rmse": "{:.2e}", "rel_rmse": "{:.2e}",
        "theory_sigma_over_sqrtN": "{:.2e}", "rmse_over_theory": "{:.2f}",
    }))
    out.append("")

    out += ["## 4. Pendiente ajustada del error en escala log-log (teoría: -0,5)", ""]
    out.append(to_markdown(slopes, {"slope": "{:.3f}", "sigma_fitted": "{:.3f}", "sigma_theory": "{:.3f}"}))
    out.append("")

    out += ["## 5. Cantidad de repeticiones por configuración", ""]
    reps = times.groupby(["system", "program"])["reps"].agg(["min", "max"]).reset_index()
    out.append(to_markdown(reps))
    out.append("")

    (SUMMARY_DIR / "tablas.md").write_text("\n".join(out), encoding="utf-8")


def main():
    raw = load_raw()
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    times = median_times(raw)
    gains = serial_gains(times)
    speedup = speedup_table(times)
    errors = error_table(raw)
    slopes = fitted_slopes(errors)

    times.to_csv(SUMMARY_DIR / "tiempos.csv", index=False)
    gains.to_csv(SUMMARY_DIR / "ganancia_serial.csv", index=False)
    speedup.to_csv(SUMMARY_DIR / "speedup.csv", index=False)
    errors.to_csv(SUMMARY_DIR / "errores.csv", index=False)
    slopes.to_csv(SUMMARY_DIR / "pendientes.csv", index=False)
    write_markdown(times, gains, speedup, errors, slopes)

    print(f"Ejecuciones leídas: {len(raw)}  |  sistemas: {', '.join(sorted(raw['system'].unique()))}")
    print(f"Tablas escritas en {SUMMARY_DIR}")
    print(slopes.to_string(index=False))


if __name__ == "__main__":
    main()
