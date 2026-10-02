#!/usr/bin/env bash
# Comprobación previa al benchmark: herramientas instaladas, núcleos realmente
# disponibles y una prueba corta de escalado.
#
# Uso (PC):        bash scripts/check_system.sh
# Uso (clúster):   MPIRUN_FLAGS="--bind-to none --oversubscribe" bash scripts/check_system.sh 24
#
# El argumento es la cantidad de núcleos asignados (por defecto, los núcleos físicos detectados).
set -uo pipefail

cd "$(dirname "$0")/.."

MAX_P=${1:-$(lscpu -p=CORE,SOCKET | grep -v '^#' | sort -u | wc -l)}
MPIRUN_FLAGS=${MPIRUN_FLAGS:-}

echo "== Herramientas =="
missing=0
for tool in gcc make mpicc mpirun python3; do
    if command -v "$tool" > /dev/null; then
        echo "  $tool: $(command -v "$tool")"
    else
        echo "  $tool: NO ESTÁ INSTALADO"
        missing=1
    fi
done
if [ "$missing" -eq 1 ]; then
    echo "Faltan herramientas. Sin permisos de administrador, probar: conda install -c conda-forge openmpi"
    exit 1
fi

echo "== Procesador =="
lscpu | grep -E '^(Model name|CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|Hypervisor vendor)'
echo "  CPU lógicas disponibles (nproc): $(nproc)"
if [ -f /sys/fs/cgroup/cpu.max ]; then
    echo "  Límite de CPU del contenedor (cpu.max): $(cat /sys/fs/cgroup/cpu.max)"
fi
echo "  Usuario: $(whoami)   (si es root, agregar --allow-run-as-root a MPIRUN_FLAGS)"

echo "== Prueba de escalado: mpi_v2, pi, N = 5 x 10^8 =="
make > /dev/null || exit 1
echo "system,program,constant,N,P,seed,estimate,abs_err,rel_err,time_s"
./bin/serial_v2 pi 500000000 1
for p in 1 $((MAX_P / 2)) "$MAX_P"; do
    # shellcheck disable=SC2086  # las opciones deben separarse en palabras
    mpirun $MPIRUN_FLAGS -np "$p" ./bin/mpi_v2 pi 500000000 1
done

echo
echo "Cómo leerlo (la última columna es el tiempo en segundos):"
echo "  - serial_v2 y mpi_v2 con P = 1 deberían tardar casi lo mismo."
echo "  - Si con P = $MAX_P tarda cerca de la mitad que con P = $((MAX_P / 2)), hay $MAX_P núcleos físicos."
echo "  - Si tarda casi igual, son $((MAX_P / 2)) núcleos físicos con dos hilos cada uno. En ese caso,"
echo "    guardar la descripción con: PHYS_CORES=$((MAX_P / 2)) bash scripts/collect_sysinfo.sh"
