#!/bin/bash
# Comprueba, antes de correr el benchmark, que el sistema tiene lo necesario
# y cuántos núcleos hay realmente disponibles.
#
# Uso:
#   ./verificar_sistema.sh                 (PC)
#   OPCIONES_MPI="--bind-to none --oversubscribe" ./verificar_sistema.sh 24     (servidor, 24 núcleos asignados)

MAX_P=${1:-4}
OPCIONES_MPI=${OPCIONES_MPI:-"--oversubscribe"}

echo "== Herramientas =="
for PROGRAMA in gcc make mpicc mpirun python3; do
    if command -v $PROGRAMA > /dev/null; then
        echo "  $PROGRAMA: $(command -v $PROGRAMA)"
    else
        echo "  $PROGRAMA: NO ESTÁ INSTALADO"
    fi
done

echo "== Procesador =="
lscpu | grep -E "Model name|^CPU\(s\)|Thread|Core|Socket"
echo "  CPUs disponibles para este usuario (nproc): $(nproc)"
if [ -f /sys/fs/cgroup/cpu.max ]; then
    echo "  Límite de CPU del contenedor (cpu.max): $(cat /sys/fs/cgroup/cpu.max)"
fi
echo "  Usuario: $(whoami)"

echo "== Prueba de escalado (pi, N = 2 x 10^8) =="
make || exit 1
echo "constante,N,P,semilla,estimacion,error_abs,tiempo_s"
./montecarlo_pi_serial 200000000 1
for P in 1 $((MAX_P / 2)) $MAX_P; do
    mpirun $OPCIONES_MPI -np $P ./montecarlo_pi_mpi 200000000 1
done
echo "Si el tiempo con $MAX_P procesos no es cerca de la mitad que con $((MAX_P / 2)),"
echo "los núcleos asignados son hilos lógicos y no núcleos físicos (o hay menos de $MAX_P)."
