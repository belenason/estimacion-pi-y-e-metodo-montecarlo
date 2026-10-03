/* Estimacion de pi por el metodo de Monte Carlo, paralela con MPI. */
#include <mpi.h>

#include "montecarlo.h"
#include "montecarlo_pi.h"

int main(int argc, char *argv[])
{
    int rank, procesos;
    long long datos[2] = {0, 0};

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &procesos);

    if (rank == 0 && !leer_argumentos(argc, argv, datos)) {
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    MPI_Bcast(datos, 2, MPI_LONG_LONG, 0, MPI_COMM_WORLD);

    long long n = datos[0];
    long long semilla = datos[1];
    long long n_local = n / procesos;
    if (rank < n % procesos) {
        n_local++;
    }

    srand48(semilla + rank);

    MPI_Barrier(MPI_COMM_WORLD);
    double inicio = MPI_Wtime();

    long long aciertos_local = contar_aciertos_pi(n_local);
    long long aciertos_total = 0;
    MPI_Reduce(&aciertos_local, &aciertos_total, 1, MPI_LONG_LONG, MPI_SUM, 0, MPI_COMM_WORLD);

    double fin = MPI_Wtime();

    if (rank == 0) {
        double estimacion = calcular_estimacion_pi(aciertos_total, n);
        imprimir_resultado(CONSTANTE_PI, n, procesos, semilla, estimacion, fin - inicio);
    }

    MPI_Finalize();
    return 0;
}