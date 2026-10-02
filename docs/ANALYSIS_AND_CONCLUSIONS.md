# Estimación de π y e por el método de Monte Carlo con MPI

**Informe de análisis y conclusiones — Evaluación Parcial 1, Computación Científica**

> Borrador de trabajo, referido a la rama `main`. Las secciones marcadas con
> **[PENDIENTE: clúster]** se completan cuando estén las mediciones del segundo sistema.
> Todos los valores numéricos provienen de `results/summary/tablas.md`.

---

## 1. Introducción

Se estiman las constantes π y e mediante el método de Monte Carlo y se estudia el comportamiento de
la solución al paralelizarla con MPI. El trabajo tiene tres objetivos: (i) verificar
experimentalmente la ley de convergencia del método, (ii) cuantificar el efecto de optimizaciones
sucesivas sobre la versión serial y (iii) medir la escalabilidad de la versión paralela, usando la
mediana de varias ejecuciones y comparando dos sistemas.

## 2. Fundamento teórico

### 2.1 Estimadores

**π.** Sea (x, y) un punto uniforme en el cuadrado unitario. La probabilidad de que caiga en el
cuarto de círculo de radio 1 es p = π/4. Con N puntos:

$$\hat{\pi} = 4\,\frac{\text{aciertos}}{N}, \qquad \sigma_\pi = 4\sqrt{p(1-p)} \approx 1{,}642$$

**e.** Sea N la menor cantidad de variables uniformes en [0, 1] cuya suma supera 1. Como
P(U₁ + … + Uₙ ≤ 1) = 1/n!, resulta P(N > n) = 1/n! y

$$E[N] = \sum_{n \ge 0} \frac{1}{n!} = e, \qquad \sigma_e = \sqrt{3e - e^2} \approx 0{,}875$$

Con M ensayos, ê = (total de números generados) / M.

### 2.2 Convergencia

Por el teorema central del límite, el error típico de ambos estimadores es σ/√N: en escala log-log,
una recta de pendiente −1/2. Reducir el error en un factor 10 exige multiplicar N por 100. Esta
tasa no depende de la dimensión del problema, lo que constituye la ventaja del método frente a las
reglas de cuadratura deterministas (O(N^(−2/d)) para trapecios) en dimensión alta; en una o dos
dimensiones, como aquí, las reglas deterministas son superiores. π y e se usan como problema de
estudio porque su valor exacto es conocido y el algoritmo es embarazosamente paralelo.

### 2.3 Limitaciones

Convergencia lenta; garantía de error solo probabilística; dependencia de la calidad y el período
del generador pseudoaleatorio; riesgo de desborde de enteros de 32 bits para N ≥ 2,1 × 10⁹; y, en
paralelo, necesidad de secuencias aleatorias independientes por proceso.

## 3. Implementación

### 3.1 Versiones seriales

| Versión | Cambio | Detalle |
|---|---|---|
| `serial_v0` | Línea de base | `rand()`, `sqrt(pow(x,2)+pow(y,2))`, `if`, contadores `int`; rechaza N que desbordarían |
| `serial_v1` | Aritmética, saltos y tipos | Comparación x² + y² ≤ 1, multiplicación por 1/`RAND_MAX`, suma del resultado de la comparación, contadores `uint64_t` |
| `serial_v2` | Generador | xoshiro256\*\* (período 2²⁵⁶ − 1, estado de 32 bytes), sembrado con SplitMix64 |

### 3.2 Versiones paralelas

`mpi_v0` y `mpi_v2` reparten los núcleos de `serial_v0` y `serial_v2` entre P procesos:

1. El proceso 0 valida los argumentos y los difunde con `MPI_Bcast`.
2. Reparto: `local_n = N / P + (rank < N % P ? 1 : 0)`. La suma es exactamente N y el desbalance máximo es de una muestra.
3. Secuencias independientes: en `mpi_v2` todos los procesos parten de la misma semilla y el
   proceso de rango r aplica r veces la función de salto del generador, que avanza 2¹²⁸ pasos. Los
   tramos son disjuntos por construcción. En `mpi_v0` solo es posible `srand(semilla + rango)`, sin garantía de independencia.
4. Cada proceso cuenta sin comunicarse; los P contadores enteros se suman con una única `MPI_Reduce`.
5. El tiempo se mide con `MPI_Wtime()` tras una `MPI_Barrier()` e incluye la reducción.

Se eligió una operación colectiva porque el patrón es la reducción de P escalares: admite una
implementación en árbol de profundidad O(log P) y no hay trabajo que solapar con la comunicación,
por lo que las primitivas no bloqueantes no aportarían beneficio.

### 3.3 Verificación

Compilación sin advertencias (`-Wall -Wextra -Wpedantic`); ejecución sin hallazgos con
`-fsanitize=address,undefined`; coincidencia exacta entre `mpi_v2` con P = 1 y `serial_v2`; suma
del reparto igual a N para N no divisible por P; y comprobación independiente de la función de
salto contra la potencia 2¹²⁸ de la matriz de transición del generador.

## 4. Metodología experimental

### 4.1 Sistemas

| | PC local | Clúster (`cluster_boogie`) |
|---|---|---|
| Procesador | Intel Core i5-10210U | AMD EPYC 7B12 (nodo solo CPU), contenedor con 24 núcleos y 96 GB asignados |
| Núcleos físicos / hilos | 4 / 8 | **[PENDIENTE]** |
| Caché L1d / L2 / L3 | 32 KiB y 256 KiB por núcleo / 6 MiB | **[PENDIENTE]** |
| Memoria visible | 3,7 GiB (WSL2) | **[PENDIENTE]** |
| Sistema | Ubuntu 24.04 sobre WSL2 (kernel 5.15) | **[PENDIENTE]** |
| Compilador | gcc 13.3.0 | **[PENDIENTE]** |
| MPI | Open MPI 4.1.6 | **[PENDIENTE]** |

Fuente: `results/sysinfo/<sistema>.txt`, generado por `scripts/collect_sysinfo.sh`.

### 4.2 Compilación

Todas las versiones: `-std=c11 -O3 -march=native -Wall -Wextra -Wpedantic -D_POSIX_C_SOURCE=200809L`,
sin `-ffast-math`. Se usan flags idénticas para que las diferencias de tiempo se deban al código.
Por `-march=native`, se recompila en cada sistema.

### 4.3 Barrido

| Programa | N | P |
|---|---|---|
| `serial_v0`, `serial_v1`, `serial_v2` | 10⁵ a 10⁹ (`serial_v0` para e: hasta 10⁸, por el límite de `int`) | — |
| `mpi_v0` | 10⁵ a 10⁸ | 1, 2, 4, 8 |
| `mpi_v2` | 10⁵ a 10⁹ (10¹⁰ en el clúster, opcional) | 1, 2, 4, 8 (en el clúster, además 12, 16 y 24) |

Cada configuración se ejecutó 7 veces (707 ejecuciones en la PC), con una semilla distinta por
repetición y por P. Para P = 8 en la PC se usan los hilos lógicos (`--use-hwthread-cpus`).

### 4.4 Métricas

- **Tiempo mediano:** mediana de las 7 repeticiones. Se usa la mediana y no la media porque las
  perturbaciones del sistema operativo solo pueden aumentar el tiempo; la media queda sesgada hacia
  arriba por los valores atípicos y la mediana no. Se informan también mínimo y máximo.
- **Speedup:** S_p = T_serial,mediana / T_p,mediana, con la versión serial equivalente como referencia.
- **Eficiencia:** E_p = S_p / P.
- **Error:** absoluto |estimación − valor real| y relativo (absoluto / valor real). Para cada N se
  informa la raíz del error cuadrático medio de las 35 estimaciones de `serial_v2` y `mpi_v2`.

El tiempo cronometrado abarca el cómputo y la reducción; excluye el arranque de MPI, que se
registra por separado como tiempo total del lanzamiento.

### 4.5 Incidencia durante la medición

En la primera corrida, los primeros minutos del barrido se ejecutaron con la máquina en un estado
aproximadamente dos veces más lento, lo que producía resultados incoherentes (`mpi_v0` con P = 1
más rápido que `serial_v0`, siendo el mismo código). Se repitieron de forma contigua las mediciones
afectadas (versiones seriales y `mpi_v0` de π) y se reemplazaron esas filas; la dispersión
resultante entre repeticiones fue inferior al 2 % para N = 10⁹. La corrida original se conserva como respaldo.

## 5. Resultados

### 5.1 Convergencia y error

Figuras: `convergencia`, `error_vs_n`.

| N | RECM π | σ/√N π | RECM e | σ/√N e |
|---|---|---|---|---|
| 10⁵ | 4,43 × 10⁻³ | 5,19 × 10⁻³ | 2,55 × 10⁻³ | 2,77 × 10⁻³ |
| 10⁶ | 1,35 × 10⁻³ | 1,64 × 10⁻³ | 7,95 × 10⁻⁴ | 8,75 × 10⁻⁴ |
| 10⁷ | 4,98 × 10⁻⁴ | 5,19 × 10⁻⁴ | 2,61 × 10⁻⁴ | 2,77 × 10⁻⁴ |
| 10⁸ | 1,80 × 10⁻⁴ | 1,64 × 10⁻⁴ | 8,46 × 10⁻⁵ | 8,75 × 10⁻⁵ |
| 10⁹ | 5,00 × 10⁻⁵ | 5,19 × 10⁻⁵ | 2,43 × 10⁻⁵ | 2,77 × 10⁻⁵ |

(RECM: raíz del error cuadrático medio, 35 estimaciones por N.)

Pendiente ajustada en escala log-log: **−0,48** para π y **−0,50** para e (teoría: −0,50). El
cociente entre error medido y teórico se mantiene entre 0,82 y 1,10. Con N = 10⁹ el error relativo
es 1,6 × 10⁻⁵ para π y 9,0 × 10⁻⁶ para e. Las estimaciones paralelas están incluidas en estos
valores, de modo que el resultado respalda también la independencia de las secuencias por proceso.

### 5.2 Versiones seriales (PC)

Figura: `serial_versiones_pc`.

| Constante | N | T V0 (s) | T V1 (s) | T V2 (s) | V0 → V1 | V1 → V2 | V0 → V2 |
|---|---|---|---|---|---|---|---|
| π | 10⁸ | 2,78 | 2,75 | 0,90 | 1,01× | 3,04× | 3,07× |
| π | 10⁹ | 27,26 | 27,17 | 9,43 | 1,00× | 2,88× | 2,89× |
| e | 10⁸ | 4,03 | 4,20 | 1,53 | 0,96× | 2,75× | 2,64× |
| e | 10⁹ | — | 38,27 | 14,65 | — | 2,61× | — |

La optimización aritmética (V1) no produjo una reducción medible del tiempo: con `-O3` el
compilador ya realiza parte de esas transformaciones y el costo dominante es `rand()`. Su aporte es
de corrección (contadores de 64 bits). El reemplazo del generador (V2) redujo el tiempo entre 2,6 y
3,0 veces. El costo por muestra de la versión final es 9,4 ns para π y unos 15 ns para e.

### 5.3 Escalabilidad de `mpi_v2` (PC)

Figuras: `tiempo_vs_p_pc`, `speedup_pc`.

**π**

| N | T serial (s) | P = 1 | P = 2 | P = 4 | P = 8 |
|---|---|---|---|---|---|
| 10⁷ | 0,0936 | S 1,01 / E 1,01 | 2,08 / 1,04 | 3,28 / 0,82 | 5,31 / 0,66 |
| 10⁸ | 0,904 | 0,99 / 0,99 | 1,79 / 0,90 | 2,83 / 0,71 | 4,36 / 0,55 |
| 10⁹ | 9,43 | 1,02 / 1,02 | 1,76 / 0,88 | 2,72 / 0,68 | 3,85 / 0,48 |

**e**

| N | T serial (s) | P = 1 | P = 2 | P = 4 | P = 8 |
|---|---|---|---|---|---|
| 10⁷ | 0,146 | S 0,87 / E 0,87 | 1,74 / 0,87 | 2,70 / 0,67 | 4,72 / 0,59 |
| 10⁸ | 1,53 | 0,92 / 0,92 | 1,75 / 0,88 | 2,85 / 0,71 | 3,90 / 0,49 |
| 10⁹ | 14,65 | 0,87 / 0,87 | 1,45 / 0,72 | 2,25 / 0,56 | 3,19 / 0,40 |

Tiempos medianos con N = 10⁹: π 9,23 / 5,37 / 3,47 / 2,45 s y e 16,84 / 10,13 / 6,52 / 4,59 s para P = 1 / 2 / 4 / 8.

Observaciones:

- El speedup crece con P en todos los casos, por debajo del ideal.
- La eficiencia depende de la duración de la ejecución: con P = 4 en π es 1,13 para N = 10⁵
  (0,2 ms) y 0,68 para N = 10⁹ (3,5 s).
- De P = 4 a P = 8 (hilos lógicos) el speedup de π con N = 10⁹ aumenta un 41 %.
- En e, `mpi_v2` con P = 1 resulta entre 8 % y 13 % más lento que `serial_v2`; esa diferencia se traslada a todos sus speedups.

### 5.4 Versión ingenua frente a versión final (PC)

Figura: `speedup_v0_v2_pc`. π, N = 10⁸:

| P | `mpi_v0`: T (s) | `mpi_v0`: S | `mpi_v2`: T (s) | `mpi_v2`: S |
|---|---|---|---|---|
| 1 | 2,74 | 1,01 | 0,91 | 0,99 |
| 2 | 1,50 | 1,85 | 0,50 | 1,79 |
| 4 | 1,03 | 2,70 | 0,32 | 2,83 |
| 8 | 0,70 | 3,95 | 0,21 | 4,36 |

Ambas versiones escalan de forma similar, pero la final es unas tres veces más rápida en tiempo
absoluto: `mpi_v0` con 8 procesos (0,70 s) apenas supera a `serial_v2` con uno (0,90 s).

### 5.5 Costo de arranque (PC)

Figura: `arranque_pc`. El lanzamiento de un programa MPI tiene un costo fijo de entre 0,33 y 0,45 s
que no depende de N. Con N = 10⁵ y P = 4 el cómputo dura 0,2 ms y el lanzamiento completo 0,35 s.
El cómputo serial iguala ese costo en torno a N ≈ 3–4 × 10⁷.

### 5.6 Comparación entre sistemas

Figura: `eficiencia_sistemas`. **[PENDIENTE: clúster]** — tabla de speedup y eficiencia del clúster
para N = 10⁹ y 10¹⁰, y comparación del tiempo de `serial_v2` entre ambos sistemas.

## 6. Discusión

**Convergencia.** Los resultados reproducen la ley σ/√N en cuatro órdenes de magnitud de N. La
dispersión de las ejecuciones individuales alrededor de la recta es propia del método: el error de
una ejecución es una variable aleatoria de desvío σ/√N.

**Optimización serial.** El resultado ilustra la ley de Amdahl dentro de un programa serial:
optimizar una parte que representa una fracción menor del tiempo no modifica el total. La ganancia
se obtuvo al actuar sobre el componente dominante, el generador.

**Escalabilidad.** La zona cronometrada no contiene trabajo serial apreciable y la comunicación se
reduce a una reducción de 8 bytes por proceso, por lo que la ley de Amdahl, S = 1/(f + (1 − f)/P)
con f ≈ 0, predice un speedup casi ideal. La pérdida de eficiencia medida en la PC no se explica
por una fracción serial fija, ya que varía con la duración de la ejecución. Es consistente con el
límite de potencia y temperatura de un procesador portátil de 15 W, que reduce la frecuencia cuando
varios núcleos permanecen cargados; esta interpretación no se verificó con un registro directo de
la frecuencia. Por encima de los 4 núcleos físicos, los hilos lógicos comparten las unidades de
ejecución y aportan una ganancia parcial.

**Regímenes.** Para N pequeño el tiempo total está dominado por el costo fijo de arranque de los
procesos, y la ejecución serial es preferible. Para N grande domina el cómputo. El programa no
entra en un régimen limitado por comunicación.

**Ley de Gustafson.** Monte Carlo se usa de forma natural con el problema escalado: con P
procesadores se generan P veces más muestras en el mismo tiempo, y el error disminuye en √P. Con
f ≈ 0, S = P − f(P − 1) ≈ P. El paralelismo reduce el tiempo o el error a tiempo fijo, pero no
altera el orden de convergencia.

**Comparación entre sistemas.** **[PENDIENTE: clúster]**. Dado que el núcleo de cómputo usa un
estado de 32 bytes y no recorre memoria, no se espera que la jerarquía de caché, el ancho de banda
de memoria ni la topología NUMA condicionen el escalado; las diferencias deberían provenir de la
cantidad de núcleos, de la frecuencia sostenida y de si las CPU visibles son núcleos físicos o hilos.

## 7. Conclusiones

1. El error de ambos estimadores decae como 1/√N, con pendientes ajustadas de −0,48 (π) y −0,50
   (e) y valores dentro del 18 % del error teórico.
2. La optimización aritmética no redujo el tiempo de ejecución (1,00× en π); el reemplazo del
   generador lo redujo entre 2,6 y 3,0 veces. Conviene medir para localizar el cuello de botella antes de optimizar.
3. Optimizar la versión serial rinde más que paralelizar una versión lenta: ocho procesos de la
   versión ingenua apenas superan a un proceso de la versión optimizada.
4. El algoritmo es embarazosamente paralelo y sin fracción serial apreciable. En la PC se midió un
   speedup de 2,72 con 4 procesos y 3,85 con 8 (π, N = 10⁹); la limitación es atribuible al hardware y no al programa.
5. Existen dos regímenes: dominado por el costo fijo de arranque para N ≲ 3–4 × 10⁷ y dominado por
   el cómputo para N mayores.
6. La independencia de las secuencias aleatorias entre procesos es un requisito de corrección; se
   garantiza con la función de salto del generador.
7. **[PENDIENTE: clúster]** Conclusión de la comparación entre sistemas.

## 8. Mejoras futuras

| Mejora | Por qué mejoraría |
|---|---|
| Conversión de entero a real con los 53 bits altos | Evita la conversión costosa de enteros sin signo de 64 bits; se midió una reducción de unas 4 veces en el núcleo de π |
| Procesamiento por bloques y vectorización (AVX2 / AVX-512) | Varias muestras por instrucción; requiere varios generadores independientes por proceso |
| Híbrido MPI + OpenMP | Un proceso por nodo e hilos por núcleo: menos procesos y menor costo de arranque en clústeres de muchos nodos |
| Cuasi-Monte Carlo (Sobol, Halton) | Error cercano a O(1/N) en lugar de O(1/√N); es la única mejora que cambia el orden de convergencia |
| GPU (CUDA) | Miles de muestras simultáneas, adecuado por la independencia entre muestras |
| Generadores basados en contador (Philox) | Independencia entre procesos sin función de salto |
| Reducción de varianza (variables antitéticas) | Disminuye σ sin aumentar N |
| Registro de frecuencia y fijación de procesos a núcleos | Permitiría confirmar la causa de la pérdida de eficiencia en la PC |

## Referencias

- D. Blackman, S. Vigna. *Scrambled Linear Pseudorandom Number Generators*. ACM Transactions on Mathematical Software, 2021.
- G. Amdahl. *Validity of the single processor approach to achieving large scale computing capabilities*. AFIPS, 1967.
- J. Gustafson. *Reevaluating Amdahl's Law*. Communications of the ACM, 1988.
- Message Passing Interface Forum. *MPI: A Message-Passing Interface Standard*.
