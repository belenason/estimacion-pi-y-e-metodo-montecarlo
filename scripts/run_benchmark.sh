#!/usr/bin/env bash
# Ejecuta el barrido de benchmarks y guarda una fila CSV por ejecución.
#
# Uso básico (PC local):
#     bash scripts/run_benchmark.sh
#
# Prueba rápida de un par de minutos (no pisa los resultados reales):
#     QUICK=1 bash scripts/run_benchmark.sh
#
# Ejemplo en el clúster:
#     SYSTEM=cluster PS="1 2 4 8 16 32" MAX_N=10000000000 \
#     NS="100000 1000000 10000000 100000000 1000000000 10000000000" \
#     MPIRUN_FLAGS="--bind-to core" bash scripts/run_benchmark.sh
#
# Variables de entorno (todas opcionales):
#     SYSTEM          nombre del sistema; define el archivo de salida (por defecto: pc)
#     NS              lista de tamaños N
#     PS              lista de cantidades de procesos P
#     REPS            repeticiones por configuración (impar, para que la mediana sea una medición real)
#     MAX_N           N máximo para serial_v2 y mpi_v2
#     V01_MAX_N       N máximo para serial_v0 y serial_v1 (son lentas)
#     MPI_V0_MAX_N    N máximo para mpi_v0
#     MPIRUN          lanzador MPI (mpirun, srun, ...)
#     MPIRUN_FLAGS    opciones extra para el lanzador, en todas las ejecuciones
#     HWTHREAD_FLAGS  opciones que se agregan solo cuando P supera los núcleos físicos
#     PHYS_CORES      núcleos físicos (por defecto se detectan con lscpu)
#     CONSTANTS, SERIAL_PROGRAMS, MPI_PROGRAMS   para repetir solo una parte del barrido
#     OUT_DIR         carpeta de salida (por defecto results/raw)
set -euo pipefail

cd "$(dirname "$0")/.."

SYSTEM=${SYSTEM:-pc}
NS=${NS:-"100000 1000000 10000000 100000000 1000000000"}
PS=${PS:-"1 2 4 8"}
REPS=${REPS:-7}
MAX_N=${MAX_N:-1000000000}
V01_MAX_N=${V01_MAX_N:-1000000000}
MPI_V0_MAX_N=${MPI_V0_MAX_N:-100000000}
MPIRUN=${MPIRUN:-mpirun}
MPIRUN_FLAGS=${MPIRUN_FLAGS:-}
HWTHREAD_FLAGS=${HWTHREAD_FLAGS:---use-hwthread-cpus}
PHYS_CORES=${PHYS_CORES:-$(lscpu -p=CORE,SOCKET | grep -v '^#' | sort -u | wc -l)}
OUT_DIR=${OUT_DIR:-results/raw}
CONSTANTS=${CONSTANTS:-"pi e"}
SERIAL_PROGRAMS=${SERIAL_PROGRAMS-"serial_v0 serial_v1 serial_v2"}
MPI_PROGRAMS=${MPI_PROGRAMS-"mpi_v0 mpi_v2"}

if [ "${QUICK:-0}" = "1" ]; then
    NS="100000 1000000"
    PS="1 2"
    REPS=3
    OUT_DIR=results/quick
fi

export SYSTEM   # los programas leen esta variable para la primera columna del CSV

# Límites de los contadores int de la versión 0 (ver serial_v0.c).
INT_MAX=2147483647
V0_LIMIT_PI=$INT_MAX
V0_LIMIT_E=$((INT_MAX / 4))

# Devuelve el N máximo permitido para un programa y una constante.
limit_for() {
    local program=$1 constant=$2 limit=$MAX_N
    case $program in
        serial_v0|serial_v1) limit=$V01_MAX_N ;;
        mpi_v0)              limit=$MPI_V0_MAX_N ;;
    esac
    case $program in
        serial_v0|mpi_v0)
            local v0_limit=$V0_LIMIT_PI
            [ "$constant" = "e" ] && v0_limit=$V0_LIMIT_E
            [ "$limit" -gt "$v0_limit" ] && limit=$v0_limit
            ;;
    esac
    echo "$limit"
}

# Ejecuta un programa una vez y agrega su fila al CSV, con el tiempo total de
# lanzamiento (wall_s) como última columna. P = 0 indica ejecución serial.
#
# La semilla es 100 * P + repetición: cada combinación de P y repetición usa
# una semilla distinta, así las estimaciones son muestras independientes y
# sirven también para estudiar el error.
run_one() {
    local p=$1 program=$2 constant=$3 n=$4 rep=$5
    local seed=$((100 * p + rep))
    local start end row wall flags

    start=$(date +%s.%N)
    if [ "$p" -eq 0 ]; then
        row=$("./bin/$program" "$constant" "$n" "$seed")
    else
        flags=$MPIRUN_FLAGS
        if [ "$p" -gt "$PHYS_CORES" ]; then
            flags="$flags $HWTHREAD_FLAGS"
        fi
        # shellcheck disable=SC2086  # las opciones deben separarse en palabras
        row=$($MPIRUN $flags -np "$p" "./bin/$program" "$constant" "$n" "$seed")
    fi
    end=$(date +%s.%N)

    wall=$(awk -v a="$start" -v b="$end" 'BEGIN { printf "%.6f", b - a }')
    echo "$row,$wall" >> "$OUT"
}

make

mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/$SYSTEM.csv"
if [ -f "$OUT" ]; then
    mv "$OUT" "$OUT.$(date +%Y%m%d-%H%M%S).bak"   # no mezclar con una corrida anterior
fi
echo "system,program,constant,N,P,seed,estimate,abs_err,rel_err,time_s,wall_s" > "$OUT"

echo "Sistema: $SYSTEM | núcleos físicos: $PHYS_CORES | repeticiones: $REPS" >&2
echo "N: $NS" >&2
echo "P: $PS" >&2

for constant in $CONSTANTS; do
    # --- versiones seriales ---
    for program in $SERIAL_PROGRAMS; do
        limit=$(limit_for "$program" "$constant")
        for n in $NS; do
            [ "$n" -gt "$limit" ] && continue
            echo "[$(date +%H:%M:%S)] $program $constant N=$n" >&2
            for rep in $(seq 1 "$REPS"); do
                run_one 0 "$program" "$constant" "$n" "$rep"
            done
        done
    done

    # --- versiones MPI ---
    for program in $MPI_PROGRAMS; do
        limit=$(limit_for "$program" "$constant")
        for n in $NS; do
            [ "$n" -gt "$limit" ] && continue
            for p in $PS; do
                echo "[$(date +%H:%M:%S)] $program $constant N=$n P=$p" >&2
                for rep in $(seq 1 "$REPS"); do
                    run_one "$p" "$program" "$constant" "$n" "$rep"
                done
            done
        done
    done
done

echo "Listo: $OUT ($(($(wc -l < "$OUT") - 1)) ejecuciones)" >&2
