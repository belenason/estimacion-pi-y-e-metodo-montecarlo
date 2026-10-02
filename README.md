# Estimación de π y e por el método de Monte Carlo con MPI

Proyecto 1 de la Evaluación Parcial 1 — Computación Científica.

Se estiman las constantes π y e con el método de Monte Carlo, primero en serie (tres versiones, cada
una con una optimización sobre la anterior) y luego en paralelo con MPI. Se mide tiempo, speedup y
eficiencia usando la mediana de varias ejecuciones, en dos sistemas distintos.

## Los dos experimentos

- **π:** se generan puntos al azar en el cuadrado unitario. La fracción que cae dentro del cuarto
  de círculo de radio 1 tiende a π/4, así que π ≈ 4 × aciertos / N.
- **e:** se suman números uniformes en [0, 1] hasta que la suma supera 1. La cantidad promedio de
  números necesarios tiende a e, así que e ≈ números generados / N.

En ambos casos el error decae como 1/√N.

## Versiones

| Programa | Qué cambia respecto de la anterior |
|---|---|
| `serial_v0` | Línea de base ingenua: `rand()`, `sqrt()`, `pow()`, `if`, contadores `int` |
| `serial_v1` | Sin `sqrt` ni `pow`, multiplicación en lugar de división, sin `if`, contadores `uint64_t` |
| `serial_v2` | Generador xoshiro256\*\* en lugar de `rand()` |
| `mpi_v0` | `serial_v0` repartido entre P procesos (referencia ingenua, semilla + rango) |
| `mpi_v2` | `serial_v2` repartido entre P procesos; cada proceso usa un tramo propio del generador (`jump`) |

Diseño de las versiones MPI:

- El proceso 0 lee los argumentos y los difunde con `MPI_Bcast`.
- Reparto: `local_n = N / P + (rank < N % P ? 1 : 0)`. La suma es exactamente N y el desbalance máximo es de una muestra.
- Cada proceso cuenta sin comunicarse; los contadores se suman con una sola `MPI_Reduce`.
- El tiempo se mide con `MPI_Wtime()` después de una `MPI_Barrier()`, e incluye la reducción.

## Estructura

```
Makefile                 compila todo con las mismas flags
src/common/prng.h        generador xoshiro256** (semilla con splitmix64, función jump)
src/common/util.h        lectura de argumentos, cronómetro y salida CSV
src/serial/              serial_v0.c  serial_v1.c  serial_v2.c
src/mpi/                 mpi_v0.c  mpi_v2.c
scripts/                 instalación, benchmarks e información del sistema
analysis/                cálculo de métricas y gráficos (Python)
results/raw/             una fila CSV por ejecución, un archivo por sistema
results/sysinfo/         descripción de cada sistema medido
results/summary/         tablas con medianas, speedup, eficiencia y errores
results/figures/         figuras en PNG y PDF
```

## Requisitos

Linux (o Windows con WSL2), gcc, make, Open MPI y Python 3 con numpy, pandas y matplotlib.

```bash
bash scripts/setup_wsl.sh                       # instala gcc, make y Open MPI en Ubuntu
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r analysis/requirements.txt
```

## Compilación

```bash
make          # compila todo en bin/
make info     # muestra compiladores y flags
make clean
```

Flags, iguales para todas las versiones:
`-std=c11 -O3 -march=native -Wall -Wextra -Wpedantic -D_POSIX_C_SOURCE=200809L`.
Como `-march=native` genera código para el procesador donde se compila, hay que recompilar en cada sistema.

## Uso

Todos los programas reciben la constante, N y la semilla, e imprimen una línea CSV:

```bash
./bin/serial_v2 pi 100000000 1
mpirun -np 4 ./bin/mpi_v2 e 100000000 1
```

```
sistema,programa,constante,N,P,semilla,estimacion,error_abs,error_rel,tiempo_s
```

## Benchmarks

```bash
SYSTEM=pc bash scripts/collect_sysinfo.sh       # guarda la descripción del sistema
SYSTEM=pc bash scripts/run_benchmark.sh         # barrido completo → results/raw/pc.csv
QUICK=1 bash scripts/run_benchmark.sh           # prueba corta → results/quick/
```

El barrido se configura con variables de entorno (`NS`, `PS`, `REPS`, `MAX_N`, `MPIRUN`,
`MPIRUN_FLAGS`, …), documentadas en el encabezado del script. En el clúster (contenedor con 24
núcleos asignados y `mpirun` directo):

```bash
MPIRUN_FLAGS="--bind-to none --oversubscribe" bash scripts/check_system.sh 24   # comprobación previa
SYSTEM=cluster_boogie bash scripts/collect_sysinfo.sh

SYSTEM=cluster_boogie PS="1 2 4 8 12 16 24" \
MPIRUN_FLAGS="--bind-to none --oversubscribe" HWTHREAD_FLAGS="" \
bash scripts/run_benchmark.sh
```

`--bind-to none` evita que Open MPI intente fijar cada proceso a un núcleo, algo que dentro de un
contenedor puede fallar. El encabezado de `run_benchmark.sh` incluye una segunda pasada opcional con N = 10¹⁰.

Cada configuración se ejecuta 7 veces. La última columna del CSV (`wall_s`) es el tiempo total del
lanzamiento, incluido el arranque de MPI, que queda fuera del tiempo cronometrado por el programa.

## Análisis y gráficos

```bash
python analysis/analyze.py            # → results/summary/*.csv y tablas.md
python analysis/plot_intuicion.py     # → results/figures/
python analysis/plot_convergencia.py
python analysis/plot_rendimiento.py
```

Métricas:

- Tiempo mediano: mediana de los tiempos de las repeticiones de cada configuración.
- Speedup: S_p = T_serial,mediana / T_p,mediana, contra la versión serial equivalente.
- Eficiencia: E_p = S_p / P.
- Error absoluto: |estimación − valor real|. Error relativo: error absoluto / valor real.

Figuras generadas:

| Figura | Qué muestra |
|---|---|
| `intuicion_pi`, `intuicion_e` | Los dos experimentos aleatorios |
| `convergencia` | Estimaciones frente al valor real, con la banda teórica del 95 % |
| `error_vs_n` | Error en escala log-log frente a la recta teórica σ/√N |
| `serial_versiones_<sistema>` | Costo por muestra de V0, V1 y V2 |
| `tiempo_vs_p_<sistema>` | Tiempo mediano de `mpi_v2` en función de P |
| `speedup_<sistema>` | Speedup de `mpi_v2` en función de P, para cada N |
| `speedup_v0_v2_<sistema>` | Speedup de la versión ingenua frente a la final |
| `arranque_<sistema>` | Tiempo de cómputo frente a tiempo total del lanzamiento |
| `eficiencia_sistemas` | Eficiencia paralela, comparando los sistemas medidos |

## Verificación

- Compilación sin advertencias con `-Wall -Wextra -Wpedantic`.
- Ejecución con `-fsanitize=address,undefined` sin hallazgos.
- `mpi_v2` con P = 1 produce exactamente el mismo resultado que `serial_v2`.
- El reparto suma N también cuando N no es divisible por P.
- `serial_v0` y `mpi_v0` rechazan los N que desbordarían sus contadores `int`.

## Referencias

- D. Blackman y S. Vigna, *Scrambled Linear Pseudorandom Number Generators*, ACM TOMS, 2021. Generador xoshiro256\*\* y función de salto: <https://prng.di.unimi.it/>
- Message Passing Interface Forum, *MPI: A Message-Passing Interface Standard*.
