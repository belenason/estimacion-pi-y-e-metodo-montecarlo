# Estimación de π y *e* mediante el Método de Monte Carlo: implementación paralela con MPI y análisis de rendimiento

**Computación Científica — Evaluación Parcial 1, Proyecto 1**

**Facultad de Ciencias Exactas y Tecnología (FACET) — Universidad Nacional de Tucumán**

**Integrantes:** Ason, Belén · Caballero, Leonardo · Cano Arce, Valentina

**Repositorio:** <https://github.com/belenason/pi-y-e-metodo-montecarlo>

**Fecha:** octubre de 2026

---

## Resumen

Se estiman las constantes π y *e* con el Método de Monte Carlo y se estudia el comportamiento de una implementación paralela en C con MPI. Para π se usa el método de aciertos sobre un cuarto de círculo; para *e*, el promedio de la cantidad de números uniformes necesarios para que su suma supere 1. El trabajo se reparte de forma equilibrada entre los procesos, que no se comunican durante el cálculo y combinan sus resultados con una única reducción.

Se midieron cinco tamaños de problema, de 10⁵ a 10⁹ muestras, con 10 repeticiones por configuración y usando la mediana de los tiempos, en dos sistemas: una notebook de 4 núcleos y un nodo de clúster con 48 núcleos. El error medido sigue la ley teórica σ/√N, con pendientes de −0,50 en escala log-log para ambas constantes, y no muestra una dependencia clara con la cantidad de procesos.

En el clúster el speedup es prácticamente ideal: con N = 10⁹ la eficiencia se mantiene en 0,98 o más hasta 32 procesos, y con 48 procesos se alcanzan speedups de 46,9 para π y 38,7 para *e*. En la notebook, el mismo programa obtiene con 4 procesos speedups de 2,1 y 3,3. Como el costo por muestra en un núcleo es prácticamente el mismo en ambos sistemas, la diferencia se atribuye a la capacidad de cada sistema para sostener varios núcleos trabajando a la vez, y no al programa. Con tamaños de problema pequeños, la eficiencia queda limitada por un costo fijo de sincronización, medido en unos 0,14 ms con 48 procesos.

---

## 1. Introducción

El Método de Monte Carlo resuelve problemas deterministas mediante muestreo aleatorio: se plantea un experimento cuyo valor esperado coincide con la cantidad buscada, se lo repite muchas veces y se promedian los resultados (Metropolis y Ulam, 1949). En este proyecto se lo aplica a la estimación de π y *e*.

El interés del problema para la Computación de Alto Rendimiento surge de dos propiedades. La primera es que el método converge lentamente: el error disminuye como 1/√N, de modo que cada dígito decimal adicional exige multiplicar por 100 la cantidad de muestras. La segunda es que las muestras son independientes entre sí, por lo que pueden repartirse entre procesos sin que estos necesiten comunicarse durante el cálculo. La primera propiedad hace necesario el paralelismo y la segunda lo hace sencillo.

El objetivo del trabajo no es obtener muchos dígitos de las constantes, para lo cual existen métodos mucho más eficientes, sino usar el problema como caso de estudio: verificar experimentalmente la convergencia, diseñar una estrategia de paralelización, medir su rendimiento en sistemas distintos y explicar las diferencias entre el comportamiento ideal y el observado.

El informe se organiza así: la sección 3 resume el fundamento teórico; las secciones 4 y 5 describen las decisiones de diseño y la implementación; la sección 6 detalla el diseño experimental; las secciones 7 y 8 presentan y analizan los resultados; las secciones 9 y 10 contienen las conclusiones y las mejoras propuestas.

## 2. Objetivos

### Objetivo general

Desarrollar una implementación paralela del Método de Monte Carlo para estimar π y *e*, y analizar la precisión de las estimaciones y el rendimiento del programa en distintos sistemas de cómputo.

### Objetivos específicos

- Verificar experimentalmente la convergencia de las estimaciones y la tasa teórica del error, 1/√N.
- Diseñar e implementar una estrategia de paralelización con MPI que reparta las simulaciones de forma equilibrada.
- Comprobar que la precisión depende de la cantidad total de muestras y no de la cantidad de procesos.
- Medir tiempos de ejecución de las versiones serial y paralela, y calcular speedup y eficiencia a partir de la mediana de múltiples ejecuciones.
- Comparar el comportamiento de la implementación en una computadora personal y en un clúster.
- Identificar las limitaciones de la implementación y proponer mejoras.

## 3. Marco teórico

### 3.1. Método de Monte Carlo

Sea θ la cantidad a estimar y X una variable aleatoria con E[X] = θ y varianza σ². El estimador de Monte Carlo es el promedio de N realizaciones independientes (Robert y Casella, 2004):

$$\hat{\theta}_N = \frac{1}{N}\sum_{i=1}^{N} X_i$$

La Ley Fuerte de los Grandes Números garantiza que el estimador converge a θ cuando N crece. El Teorema Central del Límite indica a qué velocidad: para N grande, el estimador se distribuye aproximadamente como una normal centrada en θ con desvío estándar

$$SE = \frac{\sigma}{\sqrt{N}}$$

llamado error estándar. De aquí se obtienen dos consecuencias que se usan en el resto del informe. La primera es que el error es del orden O(1/√N): reducirlo diez veces requiere cien veces más muestras. La segunda es que alrededor del 95 % de las ejecuciones debe tener un error menor que 1,96·σ/√N, lo que da un criterio cuantitativo para validar la implementación.

Como cada ejecución usa muestras distintas, el error de una ejecución individual es aleatorio y no decrece de forma monótona con N. La tendencia se observa al resumir varias ejecuciones.

### 3.2. Estimación de π

Se generan puntos (x, y) con coordenadas uniformes en [0, 1), es decir, uniformes en el cuadrado unitario del primer cuadrante. El cuarto de círculo de radio 1 centrado en el origen tiene área π/4 y el cuadrado tiene área 1, así que la probabilidad de que un punto caiga dentro del cuarto de círculo es p = π/4. Un punto está dentro cuando x² + y² ≤ 1; no hace falta calcular la raíz cuadrada porque ambos lados de la desigualdad son no negativos.

Si M de los N puntos caen dentro, el estimador es

$$\hat{\pi}_N = 4\,\frac{M}{N}$$

Trabajar con un cuarto de círculo en lugar del círculo completo no cambia la proporción de áreas y permite usar directamente los números del generador, sin reescalarlos al intervalo [−1, 1].

Cada punto es un ensayo de Bernoulli con probabilidad p, por lo que M sigue una distribución binomial y

$$\operatorname{Var}(\hat{\pi}_N) = \frac{16\,p\,(1-p)}{N} = \frac{\pi(4-\pi)}{N}, \qquad \sigma_\pi = \sqrt{\pi(4-\pi)} \approx 1{,}642$$

### 3.3. Estimación de *e*

Se suman números uniformes en [0, 1) hasta que la suma supera 1 y se registra la cantidad K de números utilizados. El valor esperado de K es exactamente *e* (Russell, 1991).

La justificación es la siguiente. Se necesitan más de k números cuando la suma de los primeros k no supera 1. Esa probabilidad es el volumen del símplex {x₁ + … + x_k ≤ 1, x_i ≥ 0}, que vale 1/k!. Para una variable que toma valores enteros no negativos, el valor esperado es la suma de las probabilidades de cola:

$$E[K] = \sum_{k=0}^{\infty} P(K > k) = \sum_{k=0}^{\infty} \frac{1}{k!} = e$$

El estimador es el promedio de K en N experimentos:

$$\hat{e}_N = \frac{1}{N}\sum_{j=1}^{N} K_j$$

con

$$\operatorname{Var}(K) = e(3-e) \approx 0{,}766, \qquad \sigma_e = \sqrt{e(3-e)} \approx 0{,}875$$

A diferencia de π, el costo de cada experimento es variable: K vale como mínimo 2 y en promedio 2,718. Esto tiene consecuencias sobre el rendimiento que se discuten en las secciones 8 y 10.

La Figura 1 ilustra los dos experimentos con pocas muestras.

![Los dos experimentos de Monte Carlo](resultados/comparacion/intuicion.png)

**Figura 1.** Izquierda: 2000 puntos uniformes en el cuadrado unitario, clasificados según caigan dentro o fuera del cuarto de círculo. Derecha: distribución de la cantidad de números necesarios para que la suma supere 1, observada en 100 000 experimentos y teórica, P(K = n) = (n − 1)/n!.

### 3.4. Métricas de error

Se usa el error absoluto respecto del valor de referencia, |θ̂ − θ|, con π = 3,14159265358979… y *e* = 2,71828182845904…. Para resumir el error de varias ejecuciones con un mismo N se usa la raíz del error cuadrático medio (RMSE), que es la magnitud directamente comparable con el error estándar teórico σ/√N.

### 3.5. Métricas de rendimiento paralelo

Sea T_s el tiempo de la versión serial y T_P el de la versión paralela con P procesos (Pacheco, 2011).

- **Speedup:** S(P) = T_s / T_P. El valor ideal es S(P) = P.
- **Eficiencia:** E(P) = S(P) / P. El valor ideal es 1.
- **Ley de Amdahl** (Amdahl, 1967): si una fracción f del tiempo de ejecución es paralelizable, el speedup está acotado por

$$S(P) \le \frac{1}{(1-f) + f/P}$$

- **Fracción serial experimental** (Karp y Flatt, 1990): a partir del speedup medido se despeja la fracción serial que lo explicaría según la Ley de Amdahl:

$$\epsilon(P) = \frac{1/S(P) - 1/P}{1 - 1/P}$$

Esta métrica sirve como diagnóstico. Si ε coincide con la fracción serial real del código, la pérdida de speedup se debe al algoritmo. Si es mucho mayor, la pérdida tiene otro origen: sobrecarga de comunicación, competencia por recursos o límites del hardware.

En todos los experimentos se mantiene N fijo y se varía P, es decir, se estudia escalabilidad fuerte.

## 4. Diseño de la solución paralela

### 4.1. Análisis de la versión serial

En ambos problemas, prácticamente todo el tiempo de ejecución se consume en el bucle de simulación. La lectura de argumentos, el cálculo final de la estimación y la impresión del resultado tienen costo constante, independiente de N. La fracción paralelizable del programa es, por lo tanto, cercana a 1, y la Ley de Amdahl no impone un límite relevante al speedup para los valores de P considerados.

Además, las iteraciones del bucle no comparten datos: cada una solo incrementa un contador. No hay arreglos ni estructuras de datos, por lo que el programa está limitado por cómputo y no por acceso a memoria.

### 4.2. Estrategia de paralelización

El problema es de tipo *embarrassingly parallel*. Se adoptó un modelo SPMD (*Single Program, Multiple Data*) con MPI: todos los procesos ejecutan el mismo programa, cada uno realiza una parte de las N simulaciones con su propia secuencia de números aleatorios y al final se suman los contadores parciales.

Se eligió una descomposición estática. Como el costo de cada muestra es el mismo en promedio para todos los procesos, no se justifica un esquema maestro-trabajador con reparto dinámico, que agregaría comunicación sin mejorar el balance de carga.

El uso de procesos MPI tiene una ventaja adicional en este problema: el generador `drand48` mantiene un estado global, y cada proceso tiene su propia copia de ese estado. Con hilos sería necesario cambiar de generador para evitar que compartan el estado.

### 4.3. Distribución del trabajo

Cada proceso calcula localmente cuántas simulaciones le corresponden, a partir de N, P y su número de proceso (`rank`):

```c
long long n_local = n / procesos;
if (rank < n % procesos) {
    n_local++;
}
```

Cuando N no es múltiplo de P, el resto se reparte de a una simulación entre los primeros procesos. La diferencia de carga entre dos procesos es de una simulación como máximo y la suma de las cargas locales es exactamente N. No se necesita comunicación para repartir el trabajo: ningún proceso envía a otro su cantidad de simulaciones.

### 4.4. Comunicación entre procesos

El programa realiza solo dos operaciones colectivas de MPI (Message Passing Interface Forum, 2021), y el volumen de datos transmitidos no depende de N (Tabla 1).

**Tabla 1.** Operaciones de comunicación del programa paralelo.

| Operación | Momento | Datos | Propósito |
|---|---|---|---|
| `MPI_Bcast` | Antes del cálculo | 2 enteros de 64 bits (N y semilla) | El proceso 0 lee los argumentos y los difunde |
| `MPI_Reduce` con `MPI_SUM` | Después del cálculo | 1 entero de 64 bits por proceso | Sumar los contadores parciales en el proceso 0 |

Decisiones asociadas:

- **Un solo `MPI_Bcast`.** N y la semilla se envían juntos en un arreglo de dos elementos, en lugar de hacer una difusión por cada dato.
- **Validación en el proceso 0.** Solo el proceso 0 valida los argumentos. Si son inválidos llama a `MPI_Abort`, que detiene a todos los procesos y evita que queden bloqueados esperando la difusión.
- **Se reducen contadores enteros, no estimaciones.** Cada proceso envía su cantidad de aciertos (o de sumandos) y la división por N se hace una sola vez en el proceso 0. El resultado es exacto y no depende de que todos los procesos hayan hecho la misma cantidad de simulaciones.
- **Contadores de 64 bits.** Se usa `long long` y `MPI_LONG_LONG`. Con N = 10⁹, el contador de sumandos de *e* llega a 2,7 × 10⁹ aproximadamente, valor que supera el máximo de un entero de 32 bits.

### 4.5. Números aleatorios en paralelo

La validez estadística del resultado exige que los procesos usen secuencias distintas: si dos procesos generaran los mismos números, se repetirían muestras y el error real sería mayor que σ/√N. La generación de números aleatorios es, por eso, el punto delicado de cualquier Monte Carlo paralelo (L'Ecuyer et al., 2017).

Se usa `drand48`, un generador congruencial lineal de 48 bits que devuelve números uniformes en [0, 1). Cada proceso inicializa su generador con `srand48(semilla + rank)`. La semilla es un argumento del programa, lo que hace reproducibles las ejecuciones.

Este esquema es simple y asegura que los procesos partan de estados distintos, pero no garantiza que sus secuencias sean independientes: todos recorren el mismo ciclo del generador, de período 2⁴⁸. Por eso la decisión se contrastó con los datos experimentales (sección 7.2), y sus limitaciones se analizan en la sección 8.1.

### 4.6. Límite teórico del speedup

La región del programa cuyo tiempo se mide (sección 5.3) contiene únicamente el bucle de simulación y la reducción. Como el costo de la reducción es independiente de N, la fracción serial tiende a cero al crecer N y el modelo de Amdahl predice un speedup prácticamente lineal. De aquí surgen dos predicciones que se contrastan con las mediciones en la sección 8: con N grande, cualquier apartamiento apreciable del speedup lineal debe atribuirse al sistema donde se ejecuta y no a la estructura del programa; con N pequeño, el speedup debe quedar limitado por el costo fijo de la comunicación.

## 5. Implementación

### 5.1. Organización del código

El código está escrito en C. Hay un programa serial y uno paralelo por cada constante. El núcleo de cálculo de cada constante está en un archivo de cabecera que incluyen ambas versiones, de modo que la versión serial y la paralela ejecutan exactamente el mismo bucle y la comparación de tiempos es justa (Tabla 2).

**Tabla 2.** Archivos del proyecto.

| Archivo | Contenido |
|---|---|
| `montecarlo_pi.h` | Bucle de simulación y estimador de π |
| `montecarlo_e.h` | Bucle de simulación y estimador de *e* |
| `montecarlo.h` | Lectura de argumentos y formato de salida |
| `montecarlo_pi_serial.c`, `montecarlo_e_serial.c` | Programas seriales |
| `montecarlo_pi_mpi.c`, `montecarlo_e_mpi.c` | Programas paralelos |
| `Makefile` | Compilación |
| `benchmark.sh` | Ejecución de todos los experimentos |
| `graficos.py` | Cálculo de medianas, speedup y eficiencia, y generación de gráficos |

Se optó por un programa por constante, en lugar de uno que calcule ambas, para medir y analizar cada problema por separado.

### 5.2. Núcleos de cálculo

Estimación de π (`montecarlo_pi.h`):

```c
static long long contar_aciertos_pi(long long n)
{
    long long aciertos = 0;

    for (long long i = 0; i < n; i++) {
        double x = drand48();
        double y = drand48();
        if (x * x + y * y <= 1.0) { // punto dentro del circulo
            aciertos++;
        }
    }
    return aciertos;
}
```

Estimación de *e* (`montecarlo_e.h`):

```c
static long long contar_sumandos_e(long long n)
{
    long long sumandos = 0;

    for (long long i = 0; i < n; i++) {
        double suma = 0.0;
        while (suma <= 1.0) {
            suma += drand48();
            sumandos++;
        }
    }
    return sumandos;
}
```

### 5.3. Programa paralelo y medición del tiempo

La estructura es la misma para las dos constantes. Se muestra la parte central del programa de π:

```c
if (rank == 0 && !leer_argumentos(argc, argv, datos)) {
    MPI_Abort(MPI_COMM_WORLD, 1);
}
MPI_Bcast(datos, 2, MPI_LONG_LONG, 0, MPI_COMM_WORLD);

/* ... cálculo de n_local (sección 4.3) ... */

srand48(semilla + rank);

MPI_Barrier(MPI_COMM_WORLD);
double inicio = MPI_Wtime();

long long aciertos_local = contar_aciertos_pi(n_local);
long long aciertos_total = 0;
MPI_Reduce(&aciertos_local, &aciertos_total, 1, MPI_LONG_LONG, MPI_SUM, 0, MPI_COMM_WORLD);

double fin = MPI_Wtime();
```

Sobre la medición del tiempo:

- **Versión paralela.** Se usa `MPI_Wtime`. El `MPI_Barrier` previo sincroniza a los procesos para que todos comiencen el cálculo a la vez. El intervalo incluye el `MPI_Reduce`; como la reducción termina en el proceso 0 recién cuando recibe el aporte de todos, el tiempo medido es el del proceso más lento más el costo de la comunicación.
- **Versión serial.** Se usa `clock_gettime(CLOCK_MONOTONIC)`, un reloj de tiempo real que no se ve afectado por ajustes de la hora del sistema.
- **Qué queda fuera.** En ambos casos se mide solo la región de cálculo. No se incluyen el lanzamiento de los procesos, `MPI_Init` ni la difusión de los argumentos. El speedup informado es, por lo tanto, el de la región de cálculo y no el del tiempo total del comando `mpirun`.

### 5.4. Compilación, ejecución y formato de salida

Los programas se compilan con `make`, que usa `gcc` para las versiones seriales y `mpicc` para las paralelas, en ambos casos con `-O2 -Wall -Wextra`.

```bash
make
./montecarlo_pi_serial 100000000 12345          # <N> [semilla]
mpirun -np 4 ./montecarlo_pi_mpi 100000000 12345
```

Cada ejecución imprime una línea en formato CSV con la constante, N, P, la semilla, la estimación, el error absoluto y el tiempo en segundos:

```
pi,100000000,4,12345,3.1414293200,1.633e-04,0.374259
```

## 6. Diseño experimental

### 6.1. Variables

La Tabla 3 resume las variables que se modificaron.

**Tabla 3.** Variables del experimento de rendimiento.

| Variable | Valores |
|---|---|
| Constante | π, *e* |
| Cantidad de muestras, N | 10⁵, 10⁶, 10⁷, 10⁸, 10⁹ |
| Cantidad de procesos, P (PC) | 1, 2, 3, 4, 6, 8 |
| Cantidad de procesos, P (clúster) | 1, 2, 4, 8, 12, 16, 24, 32, 48 |
| Repeticiones por configuración | 10 |

Para cada combinación de constante y N se ejecuta además la versión serial, que sirve de referencia para el speedup. En total son 700 ejecuciones en la PC y 1000 en el clúster.

Los valores de P en la PC se eligieron para cubrir tres situaciones: menos procesos que núcleos físicos (1 a 3), tantos procesos como núcleos físicos (4) y más procesos que núcleos físicos (6 y 8), donde entra en juego el *hyperthreading*. En el clúster se llega hasta 48 procesos, uno por núcleo. Los tamaños de problema cubren cinco órdenes de magnitud para poder observar tanto la tasa de convergencia como el efecto del tamaño sobre la eficiencia.

### 6.2. Sistemas utilizados

Los experimentos se ejecutaron en los dos sistemas que describe la Tabla 4.

**Tabla 4.** Sistemas en los que se ejecutaron los experimentos.

| | PC | Clúster |
|---|---|---|
| Procesador | Intel Core i5-10210U, 1,60 GHz | [COMPLETAR] |
| Núcleos físicos / hilos | 4 / 8 | 48 / [COMPLETAR] |
| Caché L1d / L2 / L3 | 32 KiB y 256 KiB por núcleo / 6 MiB compartida | [COMPLETAR] |
| Sistema operativo | Ubuntu 24.04 sobre WSL 2 (Windows 11) | [COMPLETAR] |
| Compilador | gcc 13.3.0 | [COMPLETAR] |
| Implementación de MPI | Open MPI 4.1.6 | [COMPLETAR] |
| Opciones de `mpirun` | `--oversubscribe` | [COMPLETAR] |

La PC es una notebook con un procesador de bajo consumo. Los programas se ejecutaron dentro de WSL 2, que es una máquina virtual sobre el hipervisor de Windows. Ambas características influyen en las mediciones y se discuten en la sección 6.5. Las ejecuciones del clúster se hicieron en un único nodo, por lo que la comunicación entre procesos no atraviesa la red.

### 6.3. Repeticiones, semillas y uso de la mediana

Cada configuración se ejecutó 10 veces. Como tiempo representativo se toma la mediana y no el promedio, porque los tiempos de ejecución tienen una distribución asimétrica: una ejecución puede demorarse por la actividad de otros procesos del sistema, pero no puede acelerarse. La mediana no se ve afectada por esos valores atípicos mientras sean menos de la mitad de las repeticiones. Como ejemplo, en la PC una de las diez ejecuciones de π con N = 10⁶ y P = 3 tardó 8,1 ms frente a una mediana de 4,2 ms.

Cada ejecución usa una semilla distinta, que se obtiene de forma determinista a partir del número de repetición y de P:

- versión serial: semilla = repetición × 100 000;
- versión paralela: semilla = repetición × 100 000 + P × 1 000, y el proceso de número r usa semilla + r.

De esta forma ninguna ejecución repite la semilla de otra y todo el experimento es reproducible. Una consecuencia es que, para una misma configuración, los dos sistemas generan exactamente los mismos números y obtienen la misma estimación: se verificó que las 500 ejecuciones comunes a ambos coinciden en todos sus dígitos. Para el análisis del error esas ejecuciones se cuentan una sola vez, lo que deja 1200 ejecuciones distintas.

### 6.4. Métricas calculadas

El script `graficos.py` agrupa las repeticiones de cada configuración y calcula:

- la mediana del tiempo, T_s para la versión serial y T_P para la paralela;
- el speedup S(P) = T_s / T_P, tomando como referencia la versión serial y no la versión paralela con P = 1;
- la eficiencia E(P) = S(P) / P;
- el RMSE de las estimaciones para cada N, que se compara con σ/√N.

### 6.5. Reproducción y limitaciones de las mediciones

Los resultados se obtienen con:

```bash
PROCESOS="1 2 3 4 6 8" REPETICIONES=10 ./benchmark.sh pc                       # en la PC
PROCESOS="1 2 4 8 12 16 24 32 48" REPETICIONES=10 ./benchmark.sh cluster       # en el clúster
python graficos.py resultados/pc_2026-10-11 resultados/cluster_2026-10-11
```

`benchmark.sh` guarda cada corrida en su propia carpeta, `resultados/<sistema>_<fecha>/`, con los tiempos y la descripción del hardware. `graficos.py` reúne las corridas indicadas y deja las tablas y los gráficos en `resultados/comparacion/`.

Limitaciones que deben tenerse en cuenta al interpretar los tiempos:

1. **Frecuencia variable del procesador (PC).** El procesador ajusta su frecuencia según la temperatura y la cantidad de núcleos activos. Un proceso solo puede ejecutarse a mayor frecuencia que cada uno de varios procesos simultáneos.
2. **Virtualización (PC).** WSL 2 agrega una capa de planificación entre los procesos y el hardware.
3. **Procesos sin núcleo exclusivo (ambos sistemas).** No se fijó cada proceso a un núcleo físico propio, por lo que el sistema operativo puede ubicar dos hilos activos en un mismo núcleo aunque haya otros libres.
4. **Orden de ejecución fijo (ambos sistemas).** Las configuraciones se ejecutaron siempre en el mismo orden, por lo que un cambio en el estado de la máquina durante la corrida afecta a configuraciones concretas en lugar de repartirse entre todas.
5. **Ejecuciones muy cortas.** Con los tamaños menores los tiempos son de milisegundos o menos. En la PC su dispersión es alta (sección 7.3).

## 7. Resultados

### 7.1. Error y convergencia

La Figura 2 muestra las estimaciones individuales en función de N. La dispersión alrededor del valor real se reduce al aumentar N en ambas constantes.

![Convergencia de las estimaciones](resultados/comparacion/convergencia.png)

**Figura 2.** Estimaciones de π y *e* en función de N. Cada punto es una ejecución; la línea horizontal es el valor real.

La Tabla 5 compara el RMSE de las 120 ejecuciones distintas realizadas con cada N con el error estándar teórico.

**Tabla 5.** Error medido y error teórico en función de N (120 ejecuciones por fila y constante).

| N | RMSE de π | σ/√N de π | Cociente | RMSE de *e* | σ/√N de *e* | Cociente |
|---|---|---|---|---|---|---|
| 10⁵ | 5,25 × 10⁻³ | 5,19 × 10⁻³ | 1,01 | 2,57 × 10⁻³ | 2,77 × 10⁻³ | 0,93 |
| 10⁶ | 1,82 × 10⁻³ | 1,64 × 10⁻³ | 1,11 | 8,73 × 10⁻⁴ | 8,75 × 10⁻⁴ | 1,00 |
| 10⁷ | 5,55 × 10⁻⁴ | 5,19 × 10⁻⁴ | 1,07 | 3,04 × 10⁻⁴ | 2,77 × 10⁻⁴ | 1,10 |
| 10⁸ | 1,62 × 10⁻⁴ | 1,64 × 10⁻⁴ | 0,99 | 8,52 × 10⁻⁵ | 8,75 × 10⁻⁵ | 0,97 |
| 10⁹ | 5,29 × 10⁻⁵ | 5,19 × 10⁻⁵ | 1,02 | 2,68 × 10⁻⁵ | 2,77 × 10⁻⁵ | 0,97 |

El cociente entre el error medido y el teórico se mantiene entre 0,93 y 1,11. El ajuste por mínimos cuadrados del RMSE en escala log-log da una pendiente de −0,505 para π y −0,497 para *e*, frente al valor teórico de −0,5 (Figura 3).

![Error en función de N](resultados/comparacion/error.png)

**Figura 3.** RMSE en función de N en escala log-log. Las líneas de trazos son las rectas teóricas σ/√N.

Además, el 95,0 % de las 600 ejecuciones de π y el 95,7 % de las 600 de *e* tuvieron un error menor que 1,96·σ/√N, en concordancia con el 95 % que predice el Teorema Central del Límite.

Con N = 10⁹ el error típico es de 5 × 10⁻⁵ para π y 3 × 10⁻⁵ para *e*, es decir, del orden de cuatro decimales correctos.

### 7.2. Precisión y cantidad de procesos

Para comparar ejecuciones con distinto N, cada error se divide por su valor teórico σ/√N. Si los procesos generan muestras que se comportan como independientes, el RMSE de ese error normalizado debe ser cercano a 1 para cualquier P. Si las secuencias de los procesos estuvieran correlacionadas positivamente, sería mayor que 1. La Tabla 6 y la Figura 4 muestran el resultado.

**Tabla 6.** RMSE del error normalizado según la cantidad de procesos (50 ejecuciones por celda).

| | Serial | 1 | 2 | 3 | 4 | 6 | 8 | 12 | 16 | 24 | 32 | 48 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| π | 0,96 | 1,05 | 1,04 | 0,81 | 1,05 | 0,99 | 1,03 | 1,13 | 1,05 | 1,09 | 1,14 | 1,09 |
| *e* | 1,01 | 1,02 | 0,92 | 0,96 | 1,09 | 1,14 | 0,94 | 0,92 | 0,97 | 1,03 | 0,94 | 0,97 |

![Error normalizado según P](resultados/comparacion/error_procesos.png)

**Figura 4.** Error medido dividido por el error teórico, para la versión serial y para cada P.

Con 50 ejecuciones por celda, la fluctuación estadística esperada de este indicador es de ±0,10. Los valores de *e* oscilan alrededor de 1 sin tendencia. Los de π con P ≥ 12 quedan todos por encima de 1; reunidos, dan 1,10 sobre 250 ejecuciones, unos 2,4 desvíos estándar por encima de lo esperado. Teniendo en cuenta la cantidad de comparaciones realizadas, ese exceso está en el límite de lo que puede atribuirse al azar.

En síntesis, los datos no muestran una pérdida de precisión clara al aumentar la cantidad de procesos: reunidas todas las ejecuciones, el indicador vale 1,04 para π y 0,99 para *e*. Tampoco permiten descartar un efecto pequeño, del orden del 10 %, en π con muchos procesos.

### 7.3. Tiempos de ejecución

Las Tablas 7 y 8 presentan la mediana del tiempo de cada configuración, y las Figuras 5 y 6, su variación con N.

**Tabla 7.** Mediana del tiempo de ejecución en la PC (10 repeticiones).

| Constante | N | Unidad | Serial | P = 1 | P = 2 | P = 3 | P = 4 | P = 6 | P = 8 |
|---|---|---|---|---|---|---|---|---|---|
| π | 10⁵ | ms | 1,73 | 1,39 | 0,646 | 0,425 | 0,334 | 0,423 | 0,338 |
| π | 10⁶ | ms | 15,1 | 13,9 | 6,08 | 4,19 | 3,09 | 4,02 | 3,17 |
| π | 10⁷ | ms | 128 | 123 | 59,5 | 41,6 | 46,9 | 39,8 | 31,0 |
| π | 10⁸ | s | 1,27 | 1,19 | 0,642 | 0,555 | 0,504 | 0,403 | 0,372 |
| π | 10⁹ | s | 12,1 | 12,1 | 8,24 | 6,43 | 5,81 | 4,93 | 4,67 |
| *e* | 10⁵ | ms | 12,5 | 9,28 | 5,06 | 2,15 | 1,02 | 1,02 | 0,863 |
| *e* | 10⁶ | ms | 103 | 71,7 | 38,0 | 23,0 | 17,2 | 11,8 | 7,76 |
| *e* | 10⁷ | ms | 470 | 439 | 301 | 185 | 124 | 98,8 | 79,0 |
| *e* | 10⁸ | s | 3,52 | 3,41 | 1,89 | 1,39 | 1,08 | 0,810 | 0,699 |
| *e* | 10⁹ | s | 34,1 | 34,1 | 18,4 | 13,3 | 10,4 | 7,83 | 8,17 |

**Tabla 8.** Mediana del tiempo de ejecución en el clúster (10 repeticiones).

| Constante | N | Unidad | Serial | P = 1 | P = 2 | P = 4 | P = 8 | P = 12 | P = 16 | P = 24 | P = 32 | P = 48 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| π | 10⁵ | ms | 1,25 | 1,24 | 0,626 | 0,323 | 0,170 | 0,125 | 0,124 | 0,121 | 0,104 | 0,170 |
| π | 10⁶ | ms | 12,4 | 12,4 | 6,19 | 3,13 | 1,58 | 1,07 | 0,814 | 0,634 | 0,523 | 0,447 |
| π | 10⁷ | ms | 125 | 123 | 61,7 | 31,1 | 15,7 | 10,5 | 7,85 | 5,31 | 6,61 | 3,50 |
| π | 10⁸ | s | 1,24 | 1,23 | 0,616 | 0,311 | 0,155 | 0,104 | 0,078 | 0,071 | 0,039 | 0,027 |
| π | 10⁹ | s | 12,4 | 12,3 | 6,16 | 3,09 | 1,55 | 1,03 | 0,777 | 0,518 | 0,394 | 0,265 |
| *e* | 10⁵ | ms | 3,36 | 3,35 | 1,69 | 0,856 | 0,442 | 0,308 | 0,251 | 0,213 | 0,169 | 0,209 |
| *e* | 10⁶ | ms | 33,5 | 33,3 | 16,7 | 8,44 | 4,28 | 2,82 | 2,17 | 1,50 | 1,15 | 0,855 |
| *e* | 10⁷ | ms | 334 | 333 | 166 | 83,8 | 42,1 | 28,1 | 21,1 | 14,1 | 10,6 | 7,21 |
| *e* | 10⁸ | s | 3,34 | 3,33 | 1,66 | 0,834 | 0,420 | 0,281 | 0,210 | 0,141 | 0,105 | 0,087 |
| *e* | 10⁹ | s | 33,4 | 33,3 | 16,6 | 8,34 | 4,18 | 2,79 | 2,10 | 1,39 | 1,06 | 0,864 |

![Tiempo en función de N en la PC](resultados/comparacion/tiempo_n_pc.png)

**Figura 5.** Mediana del tiempo en función de N para la versión serial y para cada P, en la PC (escala log-log).

![Tiempo en función de N en el clúster](resultados/comparacion/tiempo_n_cluster.png)

**Figura 6.** Mediana del tiempo en función de N para la versión serial y para cada P, en el clúster (escala log-log).

Observaciones:

- **Crecimiento lineal con N.** En el clúster el tiempo serial es proporcional a N en todo el rango: el costo por muestra se mantiene entre 12,4 y 12,5 ns para π y entre 33,4 y 33,6 ns para *e*. En la Figura 6 esto se ve como rectas paralelas, separadas por un factor constante.
- **Costo relativo de las dos constantes.** Una muestra de *e* cuesta 2,7 veces más que una de π. La diferencia en la cantidad de números aleatorios (2,718 en promedio contra 2) explica solo un factor de 1,36; el resto se atribuye a la estructura del bucle de *e* (sección 8.6).
- **Versión paralela con un proceso.** En el clúster, el tiempo con P = 1 difiere del serial en menos del 1 %. La sobrecarga de MPI en la región medida es despreciable.
- **Tamaños pequeños con muchos procesos.** En el clúster, las curvas de P alto se aplanan al disminuir N. Con N = 10⁵, el tiempo con 48 procesos es mayor que con 32.
- **Ejecuciones cortas en la PC.** En la PC el costo por muestra no es constante: en régimen es de 12 ns para π y 34 ns para *e*, pero con N = 10⁵ la versión serial de *e* tarda 125 ns por muestra. La dispersión entre repeticiones es alta: el rango intercuartílico llega al 79 % de la mediana en algunas configuraciones con N ≤ 10⁷.

### 7.4. Speedup

Las Tablas 9 y 10 y las Figuras 7 y 8 presentan el speedup de cada sistema.

**Tabla 9.** Speedup respecto de la versión serial en la PC. Los valores en cursiva superan a P.

| Constante | N | P = 1 | P = 2 | P = 3 | P = 4 | P = 6 | P = 8 |
|---|---|---|---|---|---|---|---|
| π | 10⁵ | *1,24* | *2,67* | *4,07* | *5,18* | 4,09 | 5,11 |
| π | 10⁶ | *1,09* | *2,49* | *3,61* | *4,91* | 3,77 | 4,77 |
| π | 10⁷ | *1,04* | *2,15* | *3,07* | 2,73 | 3,21 | 4,12 |
| π | 10⁸ | *1,07* | 1,98 | 2,29 | 2,52 | 3,15 | 3,41 |
| π | 10⁹ | 1,00 | 1,47 | 1,89 | 2,09 | 2,46 | 2,60 |
| *e* | 10⁵ | *1,35* | *2,47* | *5,82* | *12,31* | *12,31* | *14,51* |
| *e* | 10⁶ | *1,44* | *2,71* | *4,47* | *5,99* | *8,73* | *13,27* |
| *e* | 10⁷ | *1,07* | 1,56 | 2,54 | 3,78 | 4,76 | 5,95 |
| *e* | 10⁸ | *1,03* | 1,86 | 2,52 | 3,26 | 4,34 | 5,03 |
| *e* | 10⁹ | 1,00 | 1,85 | 2,57 | 3,28 | 4,35 | 4,17 |

**Tabla 10.** Speedup respecto de la versión serial en el clúster. Los valores en cursiva corresponden a configuraciones con N ≥ 10⁷ en las que al menos la mitad de las repeticiones cayó en el modo lento descrito en la sección 8.4.

| Constante | N | P = 1 | P = 2 | P = 4 | P = 8 | P = 12 | P = 16 | P = 24 | P = 32 | P = 48 |
|---|---|---|---|---|---|---|---|---|---|---|
| π | 10⁵ | 1,01 | 1,99 | 3,87 | 7,37 | 9,99 | 10,07 | 10,32 | 12,01 | 7,37 |
| π | 10⁶ | 1,00 | 2,01 | 3,97 | 7,85 | 11,65 | 15,27 | 19,59 | 23,76 | 27,84 |
| π | 10⁷ | 1,01 | 2,02 | 4,01 | 7,95 | 11,83 | 15,87 | 23,46 | *18,84* | *35,56* |
| π | 10⁸ | 1,01 | 2,02 | 4,01 | 8,03 | 11,99 | 15,97 | *17,43* | 31,85 | 45,42 |
| π | 10⁹ | 1,01 | 2,02 | 4,02 | 8,03 | 12,02 | 16,00 | 24,01 | 31,50 | 46,92 |
| *e* | 10⁵ | 1,00 | 1,99 | 3,92 | 7,59 | 10,89 | 13,39 | 15,71 | 19,85 | 16,05 |
| *e* | 10⁶ | 1,00 | 2,00 | 3,97 | 7,82 | 11,85 | 15,39 | 22,30 | 28,98 | 39,15 |
| *e* | 10⁷ | 1,00 | 2,01 | 3,99 | 7,95 | 11,90 | 15,84 | 23,65 | 31,45 | 46,38 |
| *e* | 10⁸ | 1,00 | 2,01 | 4,00 | 7,96 | 11,87 | 15,89 | 23,67 | 31,82 | *38,56* |
| *e* | 10⁹ | 1,00 | 2,01 | 4,01 | 8,01 | 11,99 | 15,94 | 24,03 | 31,64 | *38,68* |

![Speedup en la PC](resultados/comparacion/speedup_pc_n_grande.png)

**Figura 7.** Speedup en función de P en la PC, para N ≥ 10⁷. La línea de trazos es el speedup ideal. Los tamaños menores se omiten porque sus valores superan a P por las razones que se analizan en la sección 8.5; figuran en la Tabla 9.

![Speedup en el clúster](resultados/comparacion/speedup_cluster.png)

**Figura 8.** Speedup en función de P en el clúster para cada N, en escala log-log. La línea de trazos es el speedup ideal.

En el **clúster**, con N = 10⁹ el speedup sigue al ideal en todo el rango para π, hasta 46,9 con 48 procesos. Para *e* lo sigue hasta 32 procesos (31,6) y con 48 llega a 38,7. Al disminuir N las curvas se separan del ideal a partir de un valor de P cada vez menor, y con N = 10⁵ el speedup alcanza un máximo de 12 para π y 20 para *e* con 32 procesos, y disminuye con 48. No se observan speedups mayores que P más allá de un 1 %.

En la **PC**, para N ≥ 10⁸ y P ≥ 2 los speedups son menores que P y crecen con P de forma regular. Con 4 procesos y N = 10⁹ se obtiene 3,28 para *e* y 2,09 para π. Para N ≤ 10⁷ aparecen speedups mayores que P, de hasta 14,5 con 8 procesos y N = 10⁵, que no reflejan una ganancia real por paralelismo.

### 7.5. Eficiencia

Las Tablas 11 y 12 presentan la eficiencia de cada sistema.

**Tabla 11.** Eficiencia en la PC para los dos tamaños mayores.

| Constante | N | P = 2 | P = 3 | P = 4 | P = 6 | P = 8 |
|---|---|---|---|---|---|---|
| π | 10⁸ | 0,99 | 0,76 | 0,63 | 0,53 | 0,43 |
| π | 10⁹ | 0,74 | 0,63 | 0,52 | 0,41 | 0,33 |
| *e* | 10⁸ | 0,93 | 0,84 | 0,82 | 0,72 | 0,63 |
| *e* | 10⁹ | 0,93 | 0,86 | 0,82 | 0,72 | 0,52 |

**Tabla 12.** Eficiencia en el clúster. La cursiva tiene el mismo significado que en la Tabla 10. Las filas "mínimo" usan el menor tiempo de las 10 repeticiones en lugar de la mediana.

| Constante | N | P = 2 | P = 4 | P = 8 | P = 12 | P = 16 | P = 24 | P = 32 | P = 48 |
|---|---|---|---|---|---|---|---|---|---|
| π | 10⁵ | 1,00 | 0,97 | 0,92 | 0,83 | 0,63 | 0,43 | 0,38 | 0,15 |
| π | 10⁶ | 1,00 | 0,99 | 0,98 | 0,97 | 0,95 | 0,82 | 0,74 | 0,58 |
| π | 10⁷ | 1,01 | 1,00 | 0,99 | 0,99 | 0,99 | 0,98 | *0,59* | *0,74* |
| π | 10⁸ | 1,01 | 1,00 | 1,00 | 1,00 | 1,00 | *0,73* | 1,00 | 0,95 |
| π | 10⁹ | 1,01 | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 | 0,98 | 0,98 |
| π | 10⁹, mínimo | 1,01 | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 | 0,99 |
| *e* | 10⁵ | 1,00 | 0,98 | 0,95 | 0,91 | 0,84 | 0,65 | 0,62 | 0,33 |
| *e* | 10⁶ | 1,00 | 0,99 | 0,98 | 0,99 | 0,96 | 0,93 | 0,91 | 0,82 |
| *e* | 10⁷ | 1,00 | 1,00 | 0,99 | 0,99 | 0,99 | 0,99 | 0,98 | 0,97 |
| *e* | 10⁸ | 1,00 | 1,00 | 0,99 | 0,99 | 0,99 | 0,99 | 0,99 | *0,80* |
| *e* | 10⁹ | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 | 0,99 | *0,81* |
| *e* | 10⁹, mínimo | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 | 0,99 |

En el clúster, con N ≥ 10⁷ la eficiencia es de 0,95 o más en todas las configuraciones salvo las celdas en cursiva, donde la mediana quedó determinada por las repeticiones lentas. En la mejor repetición de cada configuración, la eficiencia con N = 10⁹ es de 0,99 o más para todos los valores de P. Con N ≤ 10⁶ la eficiencia disminuye de forma sostenida al aumentar P.

En la PC, la eficiencia de *e* se mantiene por encima de 0,8 hasta P = 4 y cae al usar los dos hilos de cada núcleo: con N = 10⁹, pasar de 4 a 8 procesos solo eleva el speedup de 3,28 a 4,17, y con 8 procesos el tiempo es mayor que con 6 (8,17 s frente a 7,83 s). La eficiencia de π es menor en todos los casos.

### 7.6. Comparación entre sistemas

Las Figuras 9 y 10 comparan el speedup y la eficiencia de los dos sistemas con el tamaño de problema más grande, y la Tabla 13 resume sus diferencias.

![Speedup en ambos sistemas](resultados/comparacion/speedup.png)

**Figura 9.** Speedup de ambos sistemas con N = 10⁹, en escala log-log.

![Eficiencia en ambos sistemas](resultados/comparacion/eficiencia.png)

**Figura 10.** Eficiencia de ambos sistemas con N = 10⁹.

**Tabla 13.** Comparación de los dos sistemas con N = 10⁹.

| | PC | Clúster |
|---|---|---|
| Tiempo serial, π | 12,1 s | 12,4 s |
| Tiempo serial, *e* | 34,1 s | 33,4 s |
| Costo por muestra en serie, π / *e* | 12,1 ns / 34,1 ns | 12,4 ns / 33,4 ns |
| Eficiencia con P = 4, π / *e* | 0,52 / 0,82 | 1,00 / 1,00 |
| Eficiencia con P = 8, π / *e* | 0,33 / 0,52 | 1,00 / 1,00 |
| Mejor tiempo paralelo, π | 4,67 s (P = 8) | 0,265 s (P = 48) |
| Mejor tiempo paralelo, *e* | 7,83 s (P = 6) | 0,864 s (P = 48) |
| Speedup máximo, π / *e* | 2,60 / 4,35 | 46,9 / 38,7 |

Un núcleo de la PC y uno del clúster ejecutan el programa serial prácticamente a la misma velocidad: los tiempos difieren en un 2 %. La diferencia entre los sistemas aparece al usar varios núcleos. A igual cantidad de procesos, el clúster conserva una eficiencia de 1,00 donde la PC baja a valores de entre 0,33 y 0,82. Con todos sus núcleos, el clúster resuelve el problema de π en un tiempo 18 veces menor que el mejor tiempo de la PC, y el de *e* en un tiempo 9 veces menor.

Las mediciones del clúster son además mucho más estables: el rango intercuartílico de las diez repeticiones, tomando el valor central entre todas las configuraciones, es del 1 % de la mediana en el clúster y del 11 % en la PC.

## 8. Análisis de resultados

### 8.1. Convergencia y validez estadística

Los resultados de la sección 7.1 confirman las tres predicciones de la teoría: las estimaciones convergen al valor real, el error disminuye como 1/√N y su magnitud coincide con σ/√N. La tercera es la más exigente, porque no tiene parámetros libres: la constante σ se calcula a partir de la distribución de cada experimento y no se ajusta a los datos. La proporción de ejecuciones con error menor que 1,96·σ/√N, cercana al 95 %, indica además que la distribución del error es la esperada y no solo su valor medio.

La sección 7.2 muestra que repartir las muestras entre hasta 48 procesos no produce una degradación clara de la precisión. Esta comprobación es necesaria porque un defecto en la independencia de las secuencias no se manifiesta de otra forma: el programa termina normalmente y la estimación sigue pareciendo razonable. También muestra su límite: con 50 ejecuciones por caso, una diferencia del 10 % no puede distinguirse de una fluctuación.

La cautela se justifica porque las secuencias de los procesos no son independientes. En un generador congruencial lineal, la diferencia entre dos secuencias que parten de estados distintos evoluciona de forma determinista. Como `srand48` coloca la semilla en los bits altos del estado, de la recurrencia del generador se deduce que las secuencias de dos procesos consecutivos cumplen

$$u_n^{(r+1)} = \left(u_n^{(r)} + d_n\right) \bmod 1, \qquad d_n = \frac{a^n \bmod 2^{32}}{2^{32}}$$

donde a es el multiplicador del generador. El desplazamiento d_n no depende de la semilla. En consecuencia, los P procesos no generan N muestras independientes, sino N/P muestras base y P − 1 copias desplazadas de cada una. Cada copia sigue siendo uniforme, por lo que el estimador no tiene sesgo, pero su varianza ya no está garantizada por la teoría de la sección 3.1: puede ser mayor o menor que σ²/N según el problema. En la estimación de π la correspondencia es exacta punto a punto; en la de *e* se pierde en parte, porque cada experimento consume una cantidad distinta de números. Esto es coherente con que el único indicio de desvío haya aparecido en π.

Las mediciones indican que, en estos dos problemas, esa dependencia no tiene un efecto grande, pero no alcanzan para cuantificarlo. La sección 10.1 propone un generador que garantiza secuencias separadas por construcción, y la sección 10.6, una verificación con más ejecuciones.

En términos prácticos, la convergencia lenta es la principal limitación del método. Con 10⁹ muestras se obtienen unos cuatro decimales correctos de π en 12 segundos en serie. Obtener un decimal más requiere 10¹¹ muestras, unos 20 minutos en serie en cualquiera de los dos sistemas, y cada decimal adicional multiplica ese tiempo por 100. El paralelismo reduce el tiempo en un factor constante, pero no cambia esa tasa: con el speedup medido en el clúster, esas 10¹¹ muestras demandarían menos de 30 segundos con 48 procesos.

### 8.2. Escalabilidad con N grande

El clúster confirma la predicción de la sección 4.6. Con N = 10⁹ la eficiencia es de 0,98 o más hasta 32 procesos en ambas constantes, y la fracción serial experimental de Karp–Flatt es menor que 0,01 en valor absoluto para todos los valores de P. El programa no tiene una fracción serial apreciable y, en un sistema que puede sostener todos sus núcleos trabajando a la vez, escala de forma prácticamente lineal. Las dos constantes escalan igual.

Las eficiencias levemente mayores que 1, de hasta 1,01, se deben a que el ejecutable paralelo con un proceso es entre un 0,5 % y un 0,8 % más rápido que el serial que se usa como referencia.

La única configuración con N = 10⁹ que se aparta del ideal es *e* con 48 procesos, con eficiencia 0,81. No se debe al programa: 4 de las 10 repeticiones tardaron 0,70 s, que corresponde a una eficiencia de 0,99, y las otras 6 tardaron entre 0,86 y 0,90 s. La sección 8.4 analiza ese comportamiento.

En la PC, en cambio, la fracción serial experimental toma valores altos (Tabla 14).

**Tabla 14.** Fracción serial experimental ε(P) en la PC para N = 10⁹.

| Constante | P = 2 | P = 3 | P = 4 | P = 6 | P = 8 |
|---|---|---|---|---|---|
| π | 0,36 | 0,30 | 0,31 | 0,29 | 0,30 |
| *e* | 0,08 | 0,09 | 0,07 | 0,08 | 0,13 |

Si la pérdida de speedup se debiera a código no paralelizado, estos valores indicarían que el 8 % del programa de *e* y el 30 % del de π son seriales. El clúster demuestra que no es así, porque el mismo código da allí valores menores que 0,01. La Ley de Amdahl no explica los resultados de la PC: la pérdida de eficiencia es una propiedad de ese sistema (sección 8.5).

### 8.3. Costo fijo de sincronización y tamaño mínimo del problema

Con N pequeño, la eficiencia del clúster cae al aumentar P (Tabla 12). La causa se identifica al restar del tiempo medido el tiempo ideal, T_s / P. La diferencia es la sobrecarga de la ejecución paralela, cuyos valores muestra la Tabla 15:

$$c(P) = T_P - \frac{T_s}{P}$$

**Tabla 15.** Sobrecarga c(P) en microsegundos, medida en el clúster con N = 10⁵.

| Constante | P = 2 | P = 4 | P = 8 | P = 12 | P = 16 | P = 24 | P = 32 | P = 48 |
|---|---|---|---|---|---|---|---|---|
| π | 2 | 11 | 13 | 21 | 46 | 69 | 65 | 143 |
| *e* | 8 | 17 | 23 | 28 | 41 | 74 | 64 | 139 |

La sobrecarga es prácticamente la misma para las dos constantes, aunque sus tiempos de cómputo difieren en un factor de 2,7, y con N = 10⁶ se obtienen valores del mismo orden. No depende entonces del trabajo que se realiza, sino de la cantidad de procesos: es el costo de la sincronización y de la reducción dentro de la región medida, y crece con P hasta unos 0,14 ms con 48 procesos.

Este costo fijo explica el comportamiento observado. La eficiencia resulta

$$E(P) = \frac{1}{1 + P\,c(P)/T_s}$$

y con c(48) = 0,14 ms el modelo predice una eficiencia de 0,83 para *e* con N = 10⁶ y 48 procesos, frente a 0,82 medido, y de 0,98 con N = 10⁷, frente a 0,97. También explica que con N = 10⁵ el tiempo con 48 procesos sea mayor que con 32: a cada proceso le corresponden unas 2000 muestras, 26 µs de cómputo en el caso de π, y la sobrecarga es cinco veces mayor que ese trabajo.

De aquí surge un criterio de dimensionamiento. Para que la eficiencia supere 0,95, el trabajo de cada proceso debe ser unas 20 veces mayor que la sobrecarga, lo que con 48 procesos equivale a unos 3 ms por proceso, es decir, N del orden de 10⁷ o mayor. Por debajo de ese tamaño conviene usar menos procesos.

Este resultado completa la predicción de la sección 4.6. El límite al speedup de este programa no proviene de una fracción serial, como en el modelo de Amdahl, sino de una sobrecarga que crece con P y que solo es relevante cuando el problema es pequeño.

### 8.4. Dos modos de tiempo en el clúster

En el clúster, los tiempos de una misma configuración no se distribuyen alrededor de un único valor sino en dos grupos bien separados. Por ejemplo, las diez repeticiones de π con N = 10⁹ y 24 procesos dieron seis tiempos de entre 0,515 y 0,518 s y cuatro de entre 0,88 y 0,92 s. El grupo rápido corresponde al speedup ideal. Tres observaciones caracterizan al grupo lento:

1. **El cociente entre el tiempo lento y el rápido es constante para cada programa** y no depende de N ni de P: vale 1,76 para π (entre 1,65 y 1,81 en 33 ejecuciones lentas) y 1,25 para *e* (entre 1,18 y 1,29 en 38).
2. **Su frecuencia crece con P** (Tabla 16).
3. **Afecta a la ejecución completa**, incluso a las de varios segundos, y no a un intervalo breve.

**Tabla 16.** Cantidad de ejecuciones lentas en el clúster según P, sobre 20 ejecuciones por celda (N = 10⁸ y 10⁹).

| P | 1 | 2 | 4 | 8 | 12 | 16 | 24 | 32 | 48 |
|---|---|---|---|---|---|---|---|---|---|
| π | 0 | 0 | 4 | 1 | 1 | 5 | 9 | 6 | 7 |
| *e* | 0 | 1 | 1 | 2 | 5 | 4 | 7 | 6 | 12 |

Estas observaciones son compatibles con que, en las ejecuciones lentas, al menos un proceso haya compartido su núcleo físico con otro hilo activo durante toda la ejecución. Como el tiempo medido es el del proceso más lento (sección 5.3), basta con que uno solo esté afectado para que toda la ejecución caiga en el modo lento, y la probabilidad de que eso ocurra aumenta con la cantidad de procesos. Un factor que depende del programa, y menor que 2, es lo esperable cuando dos hilos comparten un núcleo mediante multihilo simultáneo, y no cuando se alternan en el uso del procesador. El otro hilo puede ser un proceso de la misma ejecución o una carga ajena en el nodo. Esta explicación no fue verificada de forma directa; para hacerlo habría que repetir las mediciones fijando cada proceso a un núcleo físico (sección 10.5).

Este comportamiento tiene dos consecuencias para la interpretación de los resultados. La primera es que la mediana protege de las ejecuciones lentas solo mientras sean minoría: en las celdas en cursiva de las Tablas 10 y 12 fueron la mitad o más, y la mediana refleja el modo lento. Por eso se informa también la eficiencia calculada con el tiempo mínimo. La segunda es que la caída de eficiencia de *e* con 48 procesos no indica un límite de escalabilidad del programa.

### 8.5. Comportamiento de la PC

La comparación con el clúster permite interpretar los resultados de la PC, que por sí solos eran ambiguos.

**Speedups mayores que P con N pequeño.** Son un artefacto de la medición en la PC. En el clúster, con el mismo programa y los mismos tamaños, el costo por muestra es constante y el speedup nunca supera a P en más de un 1 %. En la PC, en cambio, el costo por muestra de las ejecuciones cortas es mayor que en régimen y disminuye al aumentar P: para *e* con N = 10⁵, la versión serial tarda 125 ns por muestra y cada uno de 4 procesos paralelos tarda unos 41 ns, frente a 34 ns en régimen. El tiempo de referencia está sobreestimado y eso infla el speedup. La causa no fue determinada; son factores posibles la gestión de energía del procesador, que eleva la frecuencia cuando la carga es sostenida, y el estado térmico de la máquina. Estas configuraciones no se usan para evaluar la escalabilidad de la PC.

**Pérdida de eficiencia con N grande.** Dado que el programa escala linealmente en el clúster y que un núcleo de cada sistema tiene la misma velocidad, la pérdida de eficiencia de la PC se debe a que sus núcleos no mantienen esa velocidad cuando trabajan varios a la vez. Tres factores son coherentes con las mediciones:

1. **Frecuencia según la cantidad de núcleos activos.** Con varios núcleos activos, un procesador de bajo consumo reduce la frecuencia de cada uno para respetar su límite térmico y de potencia. Cada proceso paralelo es entonces más lento que el proceso serial de referencia.
2. **Multihilo simultáneo.** Con más de 4 procesos se usan los dos hilos de cada núcleo, que comparten sus unidades de ejecución. Esto explica la caída de eficiencia entre P = 4 y P = 8.
3. **Procesos que comparten un núcleo.** Al ejecutarse dentro de una máquina virtual y sin fijar los procesos, dos de ellos pueden compartir un núcleo físico aun con P ≤ 4.

**Diferencia entre π y *e*.** En la PC, π escala peor que *e* de forma sistemática, aunque ambos programas tienen la misma estructura paralela. En el clúster las dos constantes escalan igual en el modo rápido, de modo que la diferencia no es del programa. El modo lento del clúster ofrece una pista: cuando un proceso comparte su núcleo, π se retrasa un 76 % y *e* un 25 %. En la PC con 4 procesos, los tiempos son 1,92 veces el ideal para π y 1,22 veces para *e*, valores del mismo orden. Esto sugiere que en la PC los procesos comparten núcleos físicos de forma habitual y que π es más sensible a esa situación. Es una hipótesis coherente con ambos conjuntos de datos, no una conclusión verificada.

**Heterogeneidad de una medición.** Las mediciones de π con N = 10⁹ en la PC no son homogéneas. En las repeticiones 1 a 7 el tiempo serial fue de 12,0 a 12,3 s; en las repeticiones 8 a 10 subió a un rango de 14,6 a 15,3 s, mientras que los tiempos con 6 y 8 procesos bajaron de unos 5,0 s y 4,7 s a unos 3,9 s. El estado de la máquina cambió durante la corrida, posiblemente por un cambio en el modo de energía, y la mediana informada mezcla ambas condiciones. El speedup de π con N = 10⁹ en la PC debe tomarse con esa reserva: vale 2,6 con 8 procesos en el primer grupo y cerca de 3,8 en el segundo.

### 8.6. Costo por muestra de *e*

El experimento de *e* cuesta 33 ns contra 12 ns del de π, una relación de 2,7, aunque consume solo 1,36 veces más números aleatorios. La diferencia se atribuye a que el bucle interno de *e* termina después de una cantidad aleatoria de iteraciones. El procesador no puede predecir cuándo se sale del bucle, y cada predicción errónea le hace descartar trabajo adelantado. La condición de π también depende de los datos, pero el compilador puede traducirla en una suma condicional sin salto. Esta explicación surge del análisis del código y no de una medición con contadores de hardware; la sección 10.3 propone una reescritura que elimina ese salto.

La explicación es coherente con la sección 8.4. Un código que pierde ciclos por predicciones erróneas deja recursos del núcleo sin usar, que otro hilo puede aprovechar; por eso *e* se retrasaría menos que π al compartir un núcleo.

Pese a su mayor costo por muestra, el estimador de *e* tiene menor varianza. El tiempo serial necesario para alcanzar un error estándar dado es proporcional a σ² por el costo de una muestra, y resulta similar para las dos constantes: 2,70 × 12 ns ≈ 33 ns para π y 0,766 × 33 ns ≈ 26 ns para *e*.

### 8.7. Limitaciones

**Del método.** La tasa de convergencia 1/√N hace que Monte Carlo no sea competitivo para calcular estas constantes: una serie como la de *e* de la sección 3.3 alcanza la precisión de máquina con menos de 20 términos. Su valor está en problemas donde no hay alternativa determinista eficiente, como las integrales en muchas dimensiones, y en que su estructura se presta al estudio del paralelismo.

**De la implementación.** Las secuencias de los procesos no son independientes (sección 8.1); en los experimentos no se observó una pérdida de precisión clara, pero la precisión no está garantizada. El período del generador, 2⁴⁸ ≈ 2,8 × 10¹⁴, es suficiente para los tamaños ensayados (el mayor experimento consume unos 2,7 × 10⁹ números) pero acota el tamaño máximo de problema. El programa no informa la incertidumbre de su estimación.

**Del estudio experimental.** No se fijaron los procesos a núcleos, lo que introdujo ejecuciones lentas en el clúster y dificulta la interpretación de la PC. Las mediciones de la PC están además afectadas por la gestión de energía y la virtualización. Solo se estudió escalabilidad fuerte, en un único nodo y sin medir el costo de lanzamiento de los procesos. Las explicaciones de las secciones 8.4 a 8.6 son coherentes con los datos, pero no se verificaron con mediciones directas.

## 9. Conclusiones

1. **El método converge como predice la teoría.** El error medido coincide con σ/√N en los cinco órdenes de magnitud de N ensayados, con pendientes de −0,50 para ambas constantes, y el 95 % de las 1200 ejecuciones queda dentro del intervalo esperado.

2. **La precisión depende de N y no muestra una dependencia clara con P.** Con hasta 48 procesos, el error se mantuvo entre 0,81 y 1,14 veces el teórico, en torno a la fluctuación esperada. En π con 12 o más procesos se observó un exceso del 10 %, en el límite de lo significativo, que no pudo confirmarse ni descartarse. Como las secuencias de los procesos no son independientes, este es el punto más débil de la implementación.

3. **El programa escala de forma prácticamente lineal.** En el clúster, con N = 10⁹ la eficiencia es de 0,98 o más hasta 32 procesos, y con 48 procesos se obtienen speedups de 46,9 para π y 38,7 para *e*, que en las mejores repeticiones llegan a 47 en ambos casos. El tiempo de 10⁹ muestras de π baja de 12,4 s a 0,26 s. La fracción serial experimental es menor que 0,01, como corresponde a un problema *embarrassingly parallel* resuelto con dos operaciones colectivas.

4. **El límite del speedup es una sobrecarga fija, no una fracción serial.** La región paralela tiene un costo de sincronización que no depende de N y crece con P, hasta unos 0,14 ms con 48 procesos. Con problemas pequeños ese costo domina: con N = 10⁵, usar 48 procesos es más lento que usar 32. Para mantener una eficiencia mayor que 0,95 con 48 procesos se necesita N del orden de 10⁷ o mayor.

5. **La diferencia entre los dos sistemas no está en la velocidad de sus núcleos.** Un núcleo de la notebook y uno del clúster ejecutan el programa serial en el mismo tiempo, con un 2 % de diferencia. Con 4 procesos, la eficiencia es de 1,00 en el clúster y de 0,52 a 0,82 en la notebook. La pérdida de la notebook no se explica con la Ley de Amdahl, porque el mismo código escala linealmente en el clúster; se debe a que sus núcleos no sostienen su rendimiento cuando trabajan a la vez.

6. **Usar más procesos que núcleos físicos aporta poco.** En la notebook, de 4 a 8 procesos el speedup de *e* pasa de 3,28 a 4,17 y la eficiencia cae de 0,82 a 0,52; el mejor tiempo se obtuvo con 6 procesos.

7. **La ubicación de los procesos importa.** En el clúster, parte de las ejecuciones fue 1,76 veces más lenta para π y 1,25 veces para *e*, con una frecuencia creciente con P. El patrón es compatible con procesos que comparten un núcleo físico, lo que se evita fijando cada proceso a un núcleo.

8. **La mediana es necesaria, pero no suficiente.** Protegió los resultados de ejecuciones atípicas aisladas, pero no cuando las ejecuciones lentas fueron la mitad o más. Revisar la distribución de los tiempos, y no solo su mediana, permitió distinguir un límite del programa de un efecto del sistema. Los tiempos de milisegundos en la notebook resultaron inadecuados para medir escalabilidad.

9. **La convergencia lenta es la limitación de fondo.** Cada decimal adicional cuesta 100 veces más muestras. El paralelismo permite alcanzar tamaños de problema mayores en un tiempo razonable, pero no modifica esa tasa: según los tiempos medidos, 10¹¹ muestras demandarían unos 20 minutos en serie y menos de 30 segundos con 48 procesos.

En cuanto a la elección del sistema: para problemas de hasta 10⁷ muestras, que se resuelven en décimas de segundo en un solo núcleo, la notebook es suficiente y el paralelismo masivo no se justifica. A partir de 10⁸ muestras el clúster aprovecha de forma eficiente todos sus núcleos y es la opción adecuada.

## 10. Mejoras futuras

Las mejoras se ordenan por su relación con las limitaciones identificadas. No se implementaron por falta de tiempo. Los factores de aceleración que se citan en las secciones 10.1 a 10.3 provienen de un banco de pruebas preliminar, independiente del código del proyecto y ejecutado en serie, por lo que son orientativos y deben volver a medirse sobre la implementación real.

### 10.1. Generador con secuencias separadas por proceso

Es la mejora prioritaria, porque es la única que atiende una cuestión de validez y no solo de velocidad. Se propone reemplazar `drand48` por xoshiro256\*\* (Blackman y Vigna, 2021), un generador de período 2²⁵⁶ − 1 que dispone de una función de salto que avanza la secuencia 2¹²⁸ posiciones. El proceso de número r aplicaría el salto r veces sobre un mismo estado inicial, de modo que cada proceso recorre un tramo propio de la secuencia. Con el esquema actual las secuencias de los procesos son copias desplazadas unas de otras (sección 8.1) y la precisión solo puede verificarse a posteriori; con este generador la separación entre secuencias queda garantizada por construcción y el resultado no depende del problema que se resuelva.

También mejora el rendimiento: el generador puede insertarse dentro del bucle, lo que evita una llamada a la biblioteca por cada número y permite mantener su estado en registros.

### 10.2. Un solo número aleatorio por punto en π

Una salida de 64 bits del generador alcanza para las dos coordenadas del punto, con 31 bits cada una. Se reduce a la mitad la cantidad de números generados. La discretización introduce un sesgo del orden de 10⁻⁹, varios órdenes de magnitud por debajo del error estadístico para cualquier N alcanzable.

### 10.3. Bucle sin saltos impredecibles y aritmética entera en *e*

Atiende la observación de la sección 8.6. El doble bucle se reemplaza por uno solo que acumula la suma como un entero y, cuando supera el umbral, la reinicia con una operación de máscara en lugar de una salida condicional:

```c
while (hechos < n) {
    s += rng_next(&g) >> 11;      // suma entera de 53 bits
    c++;                          // cantidad total de sumandos
    uint64_t fin = (s > UNO);     // 1 si el experimento terminó
    hechos += fin;
    s &= fin - 1;                 // reinicia la suma sin usar un salto
}
```

El estimador no cambia: se consumen los mismos números en el mismo orden. Se elimina la predicción errónea al final de cada experimento y, al usar enteros, la suma acumulada tiene menor latencia que en punto flotante. En las pruebas preliminares las dos modificaciones solo alcanzaron su efecto al combinarse.

En conjunto, las mejoras 10.1 a 10.3 redujeron en el banco de pruebas el costo por muestra a algo menos de la mitad para π y a un tercio para *e*. Estas mejoras aceleran por igual la versión serial y la paralela: reducen el tiempo absoluto, no modifican el speedup. Al reducir el tiempo de cómputo, aumentan el peso relativo de la sobrecarga fija de la sección 8.3 y, por lo tanto, el tamaño mínimo de problema para el que conviene usar muchos procesos.

### 10.4. Informar el error estándar

Se propone que el programa informe, junto con la estimación, su error estándar calculado a partir de los propios datos. Para π se obtiene de los aciertos ya contados. Para *e* hay que acumular además la suma de K² y reducir dos valores en lugar de uno. Así cada ejecución informaría un intervalo de confianza sin necesidad de conocer el valor real de la constante, que es la situación habitual al aplicar el método a un problema cuyo resultado se desconoce.

### 10.5. Fijar los procesos a núcleos físicos

Atiende la observación de la sección 8.4. Ejecutar con `mpirun --bind-to core` asigna a cada proceso un núcleo físico propio e impide que dos procesos de la ejecución compartan uno. Si la explicación propuesta es correcta, esto eliminaría las ejecuciones lentas del clúster que no se deban a cargas ajenas y llevaría la eficiencia con 48 procesos y N = 10⁹ a los valores de las mejores repeticiones, cercanos a 0,99. Repetir las mediciones con esta opción sirve además para verificar la explicación.

### 10.6. Mejoras del diseño experimental

- **Verificar la precisión con muchas más semillas por valor de P**, del orden de miles, para reducir la fluctuación del indicador de la sección 7.2 de ±0,10 a cerca de ±0,01 y resolver la duda sobre π con muchos procesos. Puede hacerse sin MPI, recorriendo en un solo proceso las semillas que usaría cada proceso.
- **Alternar o aleatorizar el orden de las configuraciones**, para que un cambio en el estado de la máquina no afecte siempre a las mismas.
- **Informar la dispersión junto con la mediana**, por ejemplo el mínimo y el rango intercuartílico, dado que la distribución de los tiempos resultó tener dos modos.
- **Estudiar escalabilidad débil** (Gustafson, 1988), aumentando N en proporción a P. Es el uso natural del método: aprovechar más procesos para obtener más precisión en el mismo tiempo.
- **Medir también el tiempo total del comando**, incluido el lanzamiento de los procesos, que es el costo que percibe el usuario.
- **Ejecutar en varios nodos**, para evaluar la sobrecarga de la sección 8.3 cuando la comunicación atraviesa la red.

### 10.7. Otras líneas

- **Reducción de varianza.** Técnicas como las variables antitéticas, el muestreo estratificado o las secuencias de baja discrepancia (cuasi-Monte Carlo) atacan la limitación de fondo, la tasa 1/√N, en lugar del tiempo por muestra. Cambian el estimador, por lo que corresponden a una variante del método y no a una optimización del actual.
- **Aceleradores.** La independencia entre muestras hace al problema apto para GPU y para vectorización SIMD. En el caso de *e*, la longitud variable de cada experimento dificulta la vectorización.

Se evaluaron y descartaron dos técnicas habituales. La optimización del uso de caché (*cache blocking*) no aplica, porque el programa no recorre estructuras de datos. Un esquema híbrido MPI + OpenMP no aporta en un solo nodo, donde los procesos MPI ya ocupan todos los núcleos con eficiencia cercana a 1.

## 11. Bibliografía

Amdahl, G. M. (1967). Validity of the single processor approach to achieving large scale computing capabilities. *AFIPS Conference Proceedings*, 30, 483–485.

Blackman, D., y Vigna, S. (2021). Scrambled linear pseudorandom number generators. *ACM Transactions on Mathematical Software*, 47(4), artículo 36.

Gustafson, J. L. (1988). Reevaluating Amdahl's law. *Communications of the ACM*, 31(5), 532–533.

Karp, A. H., y Flatt, H. P. (1990). Measuring parallel processor performance. *Communications of the ACM*, 33(5), 539–543.

L'Ecuyer, P., Munger, D., Oreshkin, B., y Simard, R. (2017). Random numbers for parallel computers: Requirements and methods, with emphasis on GPUs. *Mathematics and Computers in Simulation*, 135, 3–17.

Message Passing Interface Forum (2021). *MPI: A Message-Passing Interface Standard, Version 4.0*. <https://www.mpi-forum.org/docs/>

Metropolis, N., y Ulam, S. (1949). The Monte Carlo method. *Journal of the American Statistical Association*, 44(247), 335–341.

Pacheco, P. S. (2011). *An Introduction to Parallel Programming*. Morgan Kaufmann.

Robert, C. P., y Casella, G. (2004). *Monte Carlo Statistical Methods* (2.ª ed.). Springer.

Russell, K. G. (1991). Estimating the value of e by simulation. *The American Statistician*, 45(1), 66–68.

*drand48(3) — Linux manual page*. <https://man7.org/linux/man-pages/man3/drand48.3.html>

[COMPLETAR: material de la cátedra utilizado.]
