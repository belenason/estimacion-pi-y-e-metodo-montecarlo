# Estimación de π y e con el método de Monte Carlo y MPI

Proyecto 1 — Evaluación Parcial 1 — Computación Científica

## El problema

El método de Monte Carlo resuelve un problema determinista usando muestreo aleatorio: se repite
muchas veces un experimento al azar y de la frecuencia de los resultados se obtiene el valor
buscado. En este proyecto se usa para estimar π y e, se estudia cómo baja el error al aumentar la
cantidad de simulaciones, y se paraleliza con MPI para medir el speedup.

### Estimación de π

Se generan puntos (x, y) al azar en el cuadrado [0,1] × [0,1] y se cuenta cuántos caen dentro del
cuarto de círculo de radio 1 (los que cumplen x² + y² ≤ 1). Como el área del cuarto de círculo es
π/4 y la del cuadrado es 1, la proporción de puntos que cae dentro tiende a π/4:

    π ≈ 4 × aciertos / N

### Estimación de e

Se suman números al azar entre 0 y 1 hasta que la suma supera 1, y se anota cuántos números
hicieron falta. El promedio de esa cantidad tiende a e:

    e ≈ total de números generados / N        (N = cantidad de ensayos)

Esto sale de que la probabilidad de que n números uniformes sumen como mucho 1 es 1/n!, entonces la
probabilidad de necesitar más de n números es 1/n!, y la cantidad esperada es la suma de 1/n!, que es e.

### Convergencia

En los dos casos el error baja como 1/√N: para ganar un decimal más hay que usar 100 veces más
muestras. Por eso hacen falta N muy grandes y tiene sentido paralelizar.

## Cómo se paralelizó

Cada muestra es independiente de las demás, así que el problema es "embarazosamente paralelo":

1. El proceso 0 lee los argumentos y los envía a todos con `MPI_Bcast`.
2. Las N muestras se reparten: cada proceso hace N / P, y si la división no es exacta los primeros
   N % P procesos hacen una más. Así se hacen exactamente N muestras.
3. Cada proceso inicializa el generador de números aleatorios con una semilla distinta
   (semilla + número de proceso) y hace su parte sin comunicarse con los demás.
4. Los contadores de todos los procesos se suman con una sola `MPI_Reduce`.
5. El tiempo se mide con `MPI_Wtime()` después de una `MPI_Barrier()`, para que todos los procesos empiecen juntos.

La única comunicación es un envío al principio y una suma al final, sin importar el valor de N.

## Decisiones de implementación

- **Generador de números aleatorios:** `drand48()` en lugar de `rand()`. Usa 48 bits (período
  2⁴⁸ ≈ 2,8 × 10¹⁴) y devuelve directamente un real en [0, 1). `rand()` solo garantiza 15 bits
  (`RAND_MAX` puede ser 32767) y su calidad depende de la plataforma.
- **Contadores `long long`:** un `int` llega hasta unos 2,1 × 10⁹ y se desbordaría con los N más grandes.
- **Sin raíz cuadrada:** se compara x² + y² con 1 directamente, que es equivalente a comparar la distancia.
- **Se suman contadores enteros y no estimaciones:** la suma de enteros es exacta y no hay que
  ponderar cuando los procesos hacen distinta cantidad de muestras.
- **Mediana de varias ejecuciones:** cada configuración se corre 5 veces y se usa la mediana del
  tiempo, que no se ve afectada si alguna ejecución sale lenta por otra tarea del sistema.

## Archivos

| Archivo | Contenido |
|---|---|
| `montecarlo.h` | Los dos experimentos, lectura de argumentos y salida |
| `montecarlo_serial.c` | Versión serial (referencia para el speedup) |
| `montecarlo_mpi.c` | Versión paralela con MPI |
| `Makefile` | Compilación |
| `benchmark.sh` | Corre todas las pruebas y guarda los tiempos en un CSV |
| `verificar_sistema.sh` | Comprueba que estén las herramientas y cuántos núcleos hay disponibles |
| `graficos.py` | Calcula mediana, speedup, eficiencia y error, y genera los gráficos |
| `resultados/` | Tiempos medidos, tabla resumen y gráficos |

## Cómo compilar y ejecutar

Requisitos: gcc, make, Open MPI, y Python 3 con numpy, pandas y matplotlib
(`pip install -r requirements.txt`).

```bash
make

./montecarlo_serial pi 100000000
./montecarlo_serial e 100000000
mpirun -np 4 ./montecarlo_mpi pi 100000000
```

Cada programa imprime una línea: `constante,N,P,semilla,estimacion,error_abs,tiempo_s`.

## Pruebas

```bash
./benchmark.sh pc                # en la PC
./benchmark.sh cluster_boogie    # en el servidor (ver opciones más abajo)
python graficos.py          # tabla resumen y gráficos, con todos los sistemas medidos
```

Por defecto se prueba N = 10⁵, 10⁶, 10⁷, 10⁸ y 10⁹ con P = 1, 2, 4 y 8 procesos, 5 repeticiones de
cada una, para π y para e. Se puede cambiar con variables de entorno:

```bash
PROCESOS="1 2 4 8 12 16 24" OPCIONES_MPI="--bind-to none --oversubscribe" ./benchmark.sh cluster_boogie
```

Métricas:

- Speedup: S = T serial (mediana) / T con P procesos (mediana)
- Eficiencia: E = S / P
- Error: |estimación − valor real|

## Resultados

Los tiempos medidos (`tiempos_<sistema>.csv`), la tabla con medianas, speedup y eficiencia
(`resumen.csv`) y los gráficos están en la carpeta `resultados/`:

| Gráfico | Qué muestra |
|---|---|
| `intuicion.png` | Los dos experimentos con pocas muestras |
| `convergencia.png` | Las estimaciones se acercan al valor real al aumentar N |
| `error.png` | El error medido frente a la recta teórica σ/√N |
| `tiempo_<sistema>.png` | Tiempo en función de la cantidad de procesos |
| `speedup_<sistema>.png` | Speedup en función de la cantidad de procesos |
| `eficiencia.png` | Eficiencia, comparando los sistemas |

## Limitaciones y mejoras futuras

- Las semillas distintas por proceso hacen que cada uno use otra parte de la secuencia de
  `drand48`, pero no garantizan que esas partes no se solapen. Una mejora es usar un generador
  pensado para paralelo, con secuencias independientes garantizadas por proceso (por ejemplo
  xoshiro256\*\* con su función de salto, o generadores basados en contador como Philox).
- Combinar MPI con OpenMP para usar hilos dentro de cada nodo.
- Usar secuencias de baja discrepancia (cuasi-Monte Carlo, Sobol o Halton), que bajan el error
  cerca de 1/N en lugar de 1/√N.
- Vectorizar el cálculo (SIMD) o llevarlo a GPU, ya que todas las muestras son independientes.

## Guías de estudio

En `apuntes_defensa/` hay apuntes para preparar la defensa oral, y en `docs/` un borrador del informe:

| Archivo | Contenido | Se refiere a |
|---|---|---|
| [01_introduccion_y_planteo.md](apuntes_defensa/01_introduccion_y_planteo.md) | Guion de apertura, los dos experimentos, ejemplos a mano y demostraciones | Las dos ramas |
| [02_codigo_linea_por_linea.md](apuntes_defensa/02_codigo_linea_por_linea.md) | El código explicado bloque por bloque; conceptos de C y funciones de MPI | Rama `main` |
| [03_graficos_speedup_y_conclusiones.md](apuntes_defensa/03_graficos_speedup_y_conclusiones.md) | Cómo leer cada gráfico, resultados medidos, conclusiones y mejoras futuras | Rama `main` |
| [04_version_simple.md](apuntes_defensa/04_version_simple.md) | Diferencias entre las dos ramas, justificación de cada decisión y cómo correr las pruebas | Rama `version-simple` |
| [05_ideas_de_mejora.md](apuntes_defensa/05_ideas_de_mejora.md) | Mejoras candidatas para la versión simple, ordenadas por conveniencia | Rama `version-simple` |
| [ANALYSIS_AND_CONCLUSIONS.md](docs/ANALYSIS_AND_CONCLUSIONS.md) | Borrador del informe: metodología, tablas y conclusiones | Rama `main` |

El repositorio tiene dos ramas: `main` (versión completa, con tres versiones seriales y generador
xoshiro256\*\*) y `version-simple` (versión reducida, con un programa serial y uno MPI).

## Bibliografía

- N. Metropolis, S. Ulam. *The Monte Carlo Method*. Journal of the American Statistical Association, 1949.
- P. Pacheco. *An Introduction to Parallel Programming*. Morgan Kaufmann.
- W. Gropp, E. Lusk, A. Skjellum. *Using MPI*. MIT Press.
- Documentación de Open MPI: <https://www.open-mpi.org/doc/>
- Página de manual de `drand48(3)` (generador congruencial lineal de 48 bits).
- G. Amdahl. *Validity of the single processor approach to achieving large scale computing capabilities*. 1967.
- J. Gustafson. *Reevaluating Amdahl's Law*. Communications of the ACM, 1988.
