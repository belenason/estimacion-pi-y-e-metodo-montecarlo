#!/bin/bash
# Plantilla para correr los benchmarks en un clúster con SLURM.
# Si el clúster no usa SLURM, alcanza con ejecutar run_benchmark.sh directamente
# (ver el ejemplo en su encabezado).
#
# Uso:   sbatch scripts/slurm_job.sh        (desde la carpeta del proyecto)
#
# AJUSTAR antes de enviar: --ntasks, --time, la partición y el módulo de MPI.

#SBATCH --job-name=montecarlo-pi-e
#SBATCH --nodes=1
#SBATCH --ntasks=32
#SBATCH --time=03:00:00
#SBATCH --output=slurm-%j.out
##SBATCH --partition=NOMBRE_DE_LA_PARTICION

set -euo pipefail

# module load openmpi        # descomentar y ajustar si el clúster usa módulos

cd "${SLURM_SUBMIT_DIR:-.}"

export SYSTEM=cluster

# -march=native: hay que recompilar en la máquina donde se ejecuta.
make clean
make

bash scripts/collect_sysinfo.sh

# Dentro de un trabajo SLURM, mpirun toma los núcleos asignados por --ntasks.
PS="1 2 4 8 16 32" \
NS="100000 1000000 10000000 100000000 1000000000 10000000000" \
MAX_N=10000000000 \
MPIRUN_FLAGS="--bind-to core" \
bash scripts/run_benchmark.sh
