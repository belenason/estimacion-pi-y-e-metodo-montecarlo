#!/usr/bin/env bash
# Guarda la descripción del sistema donde se corren los benchmarks
# (procesador, memoria, compilador, MPI) en results/sysinfo/<SYSTEM>.txt.
#
# Uso:   SYSTEM=pc bash scripts/collect_sysinfo.sh
set -euo pipefail

cd "$(dirname "$0")/.."

SYSTEM=${SYSTEM:-pc}
OUT="results/sysinfo/$SYSTEM.txt"
mkdir -p results/sysinfo

{
    echo "=== Sistema: $SYSTEM ==="
    echo "Fecha: $(date '+%Y-%m-%d %H:%M')"
    echo
    echo "=== Kernel ==="
    uname -srm
    echo
    echo "=== Procesador (lscpu) ==="
    lscpu | grep -E '^(Architecture|CPU\(s\)|Model name|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|NUMA node\(s\)|CPU max MHz|CPU MHz|L1d cache|L1i cache|L2 cache|L3 cache|Hypervisor vendor|Virtualization type)' || true
    echo
    echo "Núcleos físicos: $(lscpu -p=CORE,SOCKET | grep -v '^#' | sort -u | wc -l)"
    echo "CPU lógicas:     $(nproc)"
    echo
    echo "=== Memoria ==="
    free -h | head -n 2
    echo
    echo "=== Compilador y MPI ==="
    gcc --version | head -n 1
    mpicc --version | head -n 1
    mpirun --version | head -n 1
    echo
    echo "=== Flags de compilación ==="
    make -s info | grep CFLAGS
} > "$OUT"

echo "Guardado en $OUT"
cat "$OUT"
