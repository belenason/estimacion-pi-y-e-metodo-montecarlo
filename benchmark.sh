#!/bin/bash
# Corre todas las pruebas y guarda los resultados en resultados/tiempos_<sistema>.csv
#
# Uso:
#   ./benchmark.sh pc
#   ./benchmark.sh servidor
#
# Se puede cambiar qué se prueba con variables de entorno, por ejemplo:
#   PROCESOS="1 2 4 8 16 32" ./benchmark.sh servidor
#   TAMANIOS="100000 1000000" REPETICIONES=3 ./benchmark.sh prueba

SISTEMA=${1:-pc}
TAMANIOS=${TAMANIOS:-"100000 1000000 10000000 100000000 1000000000"}
PROCESOS=${PROCESOS:-"1 2 4 8"}
REPETICIONES=${REPETICIONES:-5}
# --oversubscribe permite lanzar más procesos que núcleos físicos (por ejemplo 8 en una PC de 4 núcleos)
OPCIONES_MPI=${OPCIONES_MPI:-"--oversubscribe"}

make || exit 1

mkdir -p resultados
SALIDA=resultados/tiempos_$SISTEMA.csv

# Se guarda la descripción del sistema para el informe
lscpu > resultados/sistema_$SISTEMA.txt

echo "programa,constante,N,P,semilla,estimacion,error_abs,tiempo_s" > $SALIDA

for CONSTANTE in pi e; do
    for N in $TAMANIOS; do
        echo "$CONSTANTE con N = $N"
        for REP in $(seq 1 $REPETICIONES); do
            # Cada ejecución usa una semilla distinta. En la versión MPI cada
            # proceso le suma su número de proceso, por eso se dejan "huecos"
            # entre semillas: así ninguna ejecución repite la semilla de otra.
            SEMILLA=$((REP * 1000))
            echo "serial,$(./montecarlo_serial $CONSTANTE $N $SEMILLA)" >> $SALIDA

            for P in $PROCESOS; do
                SEMILLA=$((REP * 1000 + P * 100))
                echo "mpi,$(mpirun $OPCIONES_MPI -np $P ./montecarlo_mpi $CONSTANTE $N $SEMILLA)" >> $SALIDA
            done
        done
    done
done

echo "Listo. Resultados en $SALIDA"
