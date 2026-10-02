#!/usr/bin/env bash
# Instala en Ubuntu (WSL2 o nativo) las herramientas que necesita el proyecto:
# compilador C, make, OpenMPI y el módulo venv de Python.
#
# Uso:   bash scripts/setup_wsl.sh
#
# Pide la contraseña de sudo. Se puede ejecutar más de una vez sin problema:
# apt no reinstala lo que ya está.
set -euo pipefail

sudo apt-get update
sudo apt-get install -y build-essential openmpi-bin libopenmpi-dev python3-venv python3-pip

echo
echo "=== Versiones instaladas ==="
gcc --version     | head -n 1
make --version    | head -n 1
mpicc --version   | head -n 1
mpirun --version  | head -n 1
python3 --version
echo
echo "Núcleos visibles: $(nproc)"
echo "Listo. Compilar con: make"
