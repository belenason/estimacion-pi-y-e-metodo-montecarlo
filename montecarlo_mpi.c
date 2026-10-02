/*
 * montecarlo_mpi.c
 * Estimación de pi y e por el método de Monte Carlo, versión paralela con MPI.
 *
 * Las N muestras se reparten entre los P procesos. Cada proceso hace su parte
 * sin comunicarse con los demás y al final se suman los contadores.
 *
 * Uso:  mpirun -np P ./montecarlo_mpi <pi|e> <N> [semilla]
 */
#include <mpi.h>

#include "montecarlo.h"

int main(int argc, char *argv[])
{
    int rank, procesos;
    long long datos[3] = {0, 0, 0};     /* constante, N, semilla */

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &procesos);

    /* El proceso 0 lee los argumentos y se los envía a todos. */
    if (rank == 0) {
        if (!leer_argumentos(argc, argv, datos)) {
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
    }
    MPI_Bcast(datos, 3, MPI_LONG_LONG, 0, MPI_COMM_WORLD);

    int constante = (int)datos[0];
    long long n = datos[1];
    long long semilla = datos[2];

    /* Reparto: N / P muestras para cada proceso. Si la división no es exacta,
     * los primeros (N % P) procesos hacen una muestra más. */
    long long n_local = n / procesos;
    if (rank < n % procesos) {
        n_local++;
    }

    /* Cada proceso usa una semilla distinta para no repetir los mismos números. */
    srand48(semilla + rank);

    /* La barrera hace que todos empiecen a la vez antes de tomar el tiempo. */
    MPI_Barrier(MPI_COMM_WORLD);
    double inicio = MPI_Wtime();

    long long cuenta_local;
    if (constante == CONSTANTE_PI) {
        cuenta_local = contar_aciertos_pi(n_local);
    } else {
        cuenta_local = contar_sumandos_e(n_local);
    }

    /* Se suman los contadores de todos los procesos en el proceso 0. */
    long long cuenta_total = 0;
    MPI_Reduce(&cuenta_local, &cuenta_total, 1, MPI_LONG_LONG, MPI_SUM, 0, MPI_COMM_WORLD);

    double fin = MPI_Wtime();

    if (rank == 0) {
        double estimacion = calcular_estimacion(constante, cuenta_total, n);
        imprimir_resultado(constante, n, procesos, semilla, estimacion, fin - inicio);
    }

    MPI_Finalize();
    return 0;
}
