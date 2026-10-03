/* Rutinas del experimento de Monte Carlo para estimar pi. */
#ifndef MONTECARLO_PI_H
#define MONTECARLO_PI_H

static long long contar_aciertos_pi(long long n)
{
    long long aciertos = 0;

    for (long long i = 0; i < n; i++) {
        double x = drand48();
        double y = drand48();
        if (x * x + y * y <= 1.0) {
            aciertos++;
        }
    }
    return aciertos;
}

static double calcular_estimacion_pi(long long aciertos, long long n)
{
    return 4.0 * (double)aciertos / (double)n;
}

#endif