# 03 — Gráficos, speedup y conclusiones

> **Apunte de estudio.** Describe los gráficos de la rama `version-simple`.
>
> **Estado:** el benchmark de esta versión todavía no se corrió. Donde dice **[completar]** va el
> dato de `resultados/resumen.csv` o de la salida de `graficos.py`. Los valores marcados como
> *referencia de `main`* se midieron en la misma notebook con la otra versión del código (otro
> generador de números aleatorios): sirven para saber qué esperar, no para citarlos como propios.

Contenido:

1. Las métricas, en simple
2. `intuicion.png`
3. `convergencia.png` y `error.png`
4. `tiempo_<sistema>.png`
5. `speedup_<sistema>.png`
6. Qué pasa con N chico: el costo de arrancar MPI
7. `eficiencia.png` y la comparación PC – clúster
8. Conclusiones
9. Mejoras futuras
10. Preguntas probables sobre los resultados

Para cada gráfico: **qué muestra → por qué tiene esa forma → qué decir**.

---

## 1. Las métricas, en simple

| Métrica | Fórmula | En simple |
|---|---|---|
| Tiempo mediano | mediana de las 5 repeticiones | El valor del medio al ordenar los 5 tiempos |
| Speedup | S = T serial / T con P procesos | Cuántas veces más rápido que el programa serial |
| Eficiencia | E = S / P | Qué fracción de cada proceso se aprovecha. 1 = perfecto |
| Error absoluto | \|estimación − valor real\| | Cuánto me equivoqué |

**Analogía del speedup y la eficiencia.** Un pintor tarda 8 horas en pintar una casa. Con 4
pintores tardan 2,5 horas. Speedup = 8 / 2,5 = 3,2. Eficiencia = 3,2 / 4 = 0,8: cada pintor rindió
al 80 %, porque se estorban, comparten la escalera, etc.

**¿Por qué la mediana y no el promedio?** El ruido de los tiempos va para un solo lado: el sistema
operativo puede **demorar** una ejecución, nunca acelerarla. Ejemplo: tiempos de 2,1 · 2,0 · 2,0 ·
3,4 · 2,1 s. El promedio da 2,32 s, arrastrado por el 3,4; la mediana da 2,1 s, que es lo que tarda
el programa cuando nada lo molesta.

**¿Por qué 5 repeticiones?** Impar, para que la mediana sea una medición real y no el promedio de
dos. Con 5, hasta dos ejecuciones perturbadas no cambian el resultado.

**¿Contra qué se calcula el speedup?** Contra `montecarlo_serial`, no contra `montecarlo_mpi` con un
proceso. Es la comparación honesta: incluye lo que cuesta usar MPI.

---

## 2. `intuicion.png`

**Qué muestra.** Panel izquierdo: 2000 puntos al azar en el cuadrado unitario; azules los que caen
dentro del cuarto de círculo, naranjas los de afuera. El título hace la cuenta: π ≈ 4 × 1568 / 2000
= 3,136. Panel derecho: 100 000 ensayos del experimento de e; las barras son la proporción de
ensayos que necesitó 2, 3, 4… números, y los puntos negros la probabilidad teórica (n − 1)/n!.

Este gráfico no usa los resultados del benchmark: genera sus propios números con NumPy y una semilla
fija, así que siempre da lo mismo.

**Por qué tiene esa forma.** A la izquierda, la proporción de puntos azules es el área del cuarto de
círculo, π/4. Con 2000 puntos el error esperado es 1,64/√2000 ≈ 0,04, y el obtenido fue 0,006. A
la derecha, nunca alcanza con un número, la mitad de las veces alcanzan dos, un tercio de las veces
hacen falta tres, y cae muy rápido por el factorial. El promedio ponderado da 2,720.

**Qué decir.** "La proporción de puntos azules estima π/4. El histograma coincide con la
distribución teórica que sale de la demostración, y su promedio es e."

---

## 3. `convergencia.png` y `error.png`

### `convergencia.png`

**Qué muestra.** Cada punto es **una estimación** (una ejecución). Eje horizontal: N en escala
logarítmica. Línea negra: valor real.

**Por qué tiene esa forma.** Es un embudo: con N chico las estimaciones se dispersan mucho; al
crecer N se aprietan contra el valor real. Se cierra **despacio**: para angostarlo 10 veces hay que
multiplicar N por 100.

**Qué decir.** "Al aumentar las simulaciones las estimaciones se concentran alrededor del valor
real, pero lento: el ancho del embudo baja como 1/√N."

### `error.png` (el gráfico más importante de la parte matemática)

**Qué muestra.** Ejes logarítmicos. Línea punteada: error teórico σ/√N. Puntos: error medido para
cada N, calculado como la raíz del error cuadrático medio de todas las ejecuciones con ese N
(seriales y paralelas). En la leyenda, la pendiente ajustada.

**Por qué es una recta de pendiente −1/2.**

$$\text{error} = \frac{\sigma}{\sqrt{N}} \;\Rightarrow\; \log(\text{error}) = \log\sigma - \tfrac{1}{2}\log N$$

En escala log-log eso es una recta de pendiente −1/2 y ordenada log σ. La pendiente es la misma para
π y para e (es la ley del método); la altura cambia porque σ es distinta (1,642 y 0,875). Por eso
son dos rectas **paralelas**, con la de e más abajo.

**Por qué los puntos no caen exactos sobre la recta.** El error de una ejecución es en sí mismo un
número aleatorio: σ/√N es su tamaño *típico*, no su valor exacto. Una ejecución puede caer por
casualidad muy cerca del valor real o a dos veces el error típico. Promediando varias ejecuciones el
punto se acerca a la recta, pero con pocas todavía queda ruido; por eso la pendiente ajustada da
cerca de −0,5 y no exacto.

| | Pendiente medida | Teoría | Referencia de `main` |
|---|---|---|---|
| π | [completar] | −0,50 | −0,48 |
| e | [completar] | −0,50 | −0,50 |

**Qué decir.** "El error medido sigue la recta teórica, con pendiente [completar] para π y
[completar] para e. Eso valida a la vez la teoría, la implementación y el manejo de los números
aleatorios en paralelo, porque las ejecuciones paralelas están incluidas en esos puntos: si los
procesos repitieran números, el error quedaría por encima de la recta."

---

## 4. `tiempo_<sistema>.png`

**Qué muestra.** Tiempo mediano (eje vertical, logarítmico) en función de P, una línea por cada N,
un panel para π y otro para e.

**Por qué tiene esa forma.** Las líneas quedan separadas por un factor de alrededor de 10: el tiempo
es proporcional a N. Todas bajan al aumentar P. Con escalado perfecto, cada vez que P se duplica el
tiempo bajaría a la mitad; en la práctica baja algo menos (sección 5). Las líneas de N chico son
irregulares porque se miden milisegundos o menos (sección 6).

**e tarda más que π** a igual N: cada ensayo de e usa en promedio 2,72 números aleatorios contra 2
de π, y tiene un `while` de largo impredecible. En una prueba informal: unos 19 ns por punto de π y
46 ns por ensayo de e.

---

## 5. `speedup_<sistema>.png`

**Qué muestra.** Speedup en función de P, una línea por cada N. Línea punteada gris: el ideal S = P.
Si el barrido pasa de 32 procesos (experimento de 96), los dos ejes son logarítmicos y el ideal
sigue siendo una recta diagonal.

**Resultados de la notebook con N = 10⁹** [completar]:

| P | π: tiempo | π: S | π: E | e: tiempo | e: S | e: E |
|---|---|---|---|---|---|---|
| serial | | — | — | | — | — |
| 1 | | | | | | |
| 2 | | | | | | |
| 4 | | | | | | |
| 8 | | | | | | |

*Referencia de `main` (π, N = 10⁹): S = 1,76 con 2 procesos, 2,72 con 4 y 3,85 con 8.*

**Por qué la curva se aparta del ideal.** Hay que separar cuatro efectos; no todo es Amdahl.

**(a) No es la fracción serial (ley de Amdahl).** Dentro de la zona cronometrada no hay trabajo
serial: la lectura de argumentos y el arranque quedan fuera. La ley de Amdahl dice
S = 1 / (f + (1 − f)/P), con f la fracción que no se puede paralelizar; acá f es prácticamente 0,
así que Amdahl por sí sola predice un speedup casi ideal.

**(b) No es la comunicación.** Hay una sola `MPI_Reduce` de un entero de 8 bytes por proceso: cuesta
microsegundos contra segundos de cómputo.

**(c) En la notebook: límite de potencia y temperatura.** El i5-10210U es un procesador de bajo
consumo (15 W). Con un solo núcleo activo usa su frecuencia turbo máxima (4,2 GHz según el
fabricante). Con varios núcleos cargados de forma sostenida, el límite de potencia y de temperatura
lo obliga a bajar la frecuencia de **todos**: cada proceso corre más lento que cuando estaba solo.

*Evidencia (referencia de `main`):* con 4 procesos, las ejecuciones que duraban milisegundos
tuvieron eficiencia cercana a 1, y las que duraban segundos, 0,68. El mismo programa escala mejor
cuando dura poco: es lo que se espera de un límite térmico sostenido. Con los datos de esta versión
se puede comprobar lo mismo comparando la eficiencia con P = 4 entre N = 10⁶ y N = 10⁹ [completar].
Dicho con honestidad: no se registró la frecuencia del procesador, así que es una hipótesis bien
apoyada, no una medición directa.

**(d) De 4 a 8 procesos en la notebook: hilos lógicos.** La notebook tiene 4 núcleos físicos y 8
hilos. Dos hilos del mismo núcleo **comparten** sus unidades de cálculo; no son dos núcleos. Pasar de
4 a 8 procesos mejora algo, no el doble (referencia de `main`: +41 %). Analogía: dos cocineros
compartiendo una hornalla; aprovechan los tiempos muertos del otro, pero no cocinan el doble.

**Speedups o eficiencias mayores que lo ideal con N chico.** No es un efecto real ("superlineal"):
son cómputos de milisegundos, donde el ruido de medición pesa mucho. No hay que presentarlo como un logro.

**Qué decir.** "El programa es embarazosamente paralelo y casi no tiene parte serial, así que la
teoría predice un speedup casi lineal. En mi notebook medí [completar] con 4 procesos. La diferencia
no viene del programa sino del hardware: un procesador de 15 W no puede sostener la frecuencia turbo
con todos los núcleos cargados, y más allá de 4 procesos uso hilos lógicos que comparten núcleo."

---

## 6. Qué pasa con N chico: el costo de arrancar MPI

**Qué se ve.** Con N = 10⁵ o 10⁶ las curvas de speedup son erráticas, y con muchos procesos pueden
incluso empeorar.

**Por qué.** Con N chico el cómputo dura microsegundos o milisegundos: cualquier perturbación pesa
más que el cálculo mismo. Además, aunque el tiempo cronometrado no lo incluye, lanzar MPI tiene un
costo fijo: crear los procesos e inicializar MPI cuesta alrededor de 0,3 a 0,4 s en la notebook
(referencia de `main`). Con N = 10⁵ eso es cientos de veces más que el cálculo: el programa serial
termina antes de que MPI termine de arrancar.

**Qué decir.** "Con N chico no conviene paralelizar: el costo fijo de arrancar los procesos supera
al cálculo. El punto de equilibrio está donde el cómputo serial iguala ese costo, que a unos 19 ns
por muestra son del orden de 10⁷ muestras."

**Vocabulario preciso.** Este programa **nunca** queda limitado por la comunicación: hay una sola
reducción. Con N chico lo que domina es el **costo fijo de arranque**. Si el profesor dice "limitado
por comunicación", la respuesta precisa es: "en este programa el sobrecosto no es de comunicación
sino de arranque de procesos".

**Por qué no se ve en el speedup.** Porque el tiempo cronometrado excluye `MPI_Init`: mide la
escalabilidad del algoritmo. Medir también el tiempo total del lanzamiento y graficarlo es la
mejora 1 del apunte 05.

---

## 7. `eficiencia.png` y la comparación PC – clúster

**Qué muestra.** Eficiencia E = S/P con el mayor N medido en todos los sistemas, una línea por
sistema. Línea punteada: E = 1.

**Por qué empieza cerca de 1 y baja.** Con P = 1 no hay nada que repartir: E ≈ 1. Al sumar
procesos cada uno rinde un poco menos (en la notebook, por el límite de potencia y después por los
hilos lógicos). La eficiencia indica **cuándo deja de convenir agregar procesos**: el tiempo puede
seguir bajando, pero con retornos decrecientes.

### La diferencia entre la notebook y el clúster

| | Notebook: Intel i5-10210U | Clúster Boogie: AMD EPYC 7B12 |
|---|---|---|
| Tipo | Portátil de bajo consumo (15 W) | Procesador de servidor (Zen 2) |
| Núcleos | 4 físicos, 8 hilos | 64 físicos por zócalo; al contenedor se le asignan 24 (o los que se elijan) |
| Frecuencia | Turbo alto con un núcleo; baja con todos cargados | Diseñado para sostener la frecuencia con todos los núcleos cargados |
| Entorno | Ubuntu sobre WSL2 | Contenedor Linux con JupyterLab |

Qué se espera, a confirmar con las mediciones:

1. **Eficiencia más alta y más estable en el clúster** mientras P no supere los núcleos físicos asignados.
2. **Un núcleo del clúster puede ser más lento que uno de la notebook.** Los procesadores de servidor
   priorizan muchos núcleos a frecuencia moderada; la notebook, con un solo núcleo activo, usa un
   turbo alto. No sorprenderse si `montecarlo_serial` tarda más en el clúster.
3. **Más núcleos, speedup máximo mayor.**
4. **Si los 24 "núcleos" son en realidad 12 físicos con dos hilos cada uno**, la curva se doblará
   pasando P = 12, igual que la notebook pasando P = 4. Lo dice la prueba de escalado de `verificar_sistema.sh`.
5. **El clúster es compartido:** otros usuarios pueden meter ruido. Por eso la mediana, y por eso
   revisar la dispersión de las repeticiones.

**Por qué la caché, la memoria y NUMA casi no influyen** (punto fino, vale la pena decirlo): cada
proceso usa un estado de 48 bits del generador y un par de contadores; todo vive en registros del
procesador y no recorre arreglos en memoria. Por eso este problema escala bien en cualquier máquina,
a diferencia de un código que mueve muchos datos (por ejemplo un producto de matrices), donde el
ancho de banda de memoria limita el escalado.

**Resultados [completar]:** speedup y eficiencia del clúster con N = 10⁹; si un núcleo del clúster
es más rápido o más lento que uno de la notebook (comparar el tiempo serial); si las CPU asignadas
son núcleos o hilos; y si, como se esperaba, la eficiencia fue más alta que en la notebook.

El experimento opcional hasta 96 procesos (cómo correrlo y cómo leer la curva) está en el apunte 04.

---

## 8. Conclusiones

Plantilla para completar con los datos. Cada conclusión con el dato que la respalda.

1. **El método funciona y cumple la teoría.** El error medido sigue σ/√N con pendiente [completar]
   para π y [completar] para e (teoría: −0,5). Con N = 10⁹ el error típico es [completar].
2. **La convergencia es lenta y paralelizar no la cambia.** Un decimal más cuesta 100 veces más
   muestras. Con P procesos se hace el mismo trabajo en menos tiempo, o P veces más muestras en el
   mismo tiempo, con un error √P veces menor. El paralelismo compra tiempo, no orden de convergencia.
3. **El algoritmo escala casi idealmente; el límite medido es del hardware.** No hay fracción serial
   apreciable en la zona cronometrada ni costo de comunicación relevante. En la notebook el speedup
   con 4 procesos fue [completar]; en el clúster con 24, [completar].
4. **Hay dos regímenes según N.** Con N chico domina el costo fijo de arrancar MPI y no conviene
   paralelizar; con N grande domina el cómputo y el paralelismo rinde.
5. **Ley de Amdahl y ley de Gustafson.**
   - *Amdahl* (problema de tamaño fijo): S ≤ 1 / (f + (1 − f)/P). Con f ≈ 0 no impone un techo
     práctico; sí aparece si se cuenta el arranque como parte serial, que es lo que pasa con N chico.
   - *Gustafson* (el problema crece con los recursos): S = P − f(P − 1). Es la forma natural de usar
     Monte Carlo: con más procesadores no se quiere el mismo N más rápido sino **más muestras en el
     mismo tiempo**, para bajar el error.
6. **La independencia de los números aleatorios es un requisito de corrección.** Semillas distintas
   por proceso evitan repetir muestras; no garantizan formalmente que los tramos no se solapen, pero
   el error medido sigue la teoría. La solución rigurosa es un generador con saltos.
7. **[completar]** Comparación entre la notebook y el clúster.

---

## 9. Mejoras futuras

Cada una: qué es y por qué mejoraría el programa. Cuáles se pueden implementar dentro de este
trabajo, ordenadas por conveniencia, está en el apunte 05.

**1. Generador con secuencias independientes garantizadas.** xoshiro256\*\* con su función de salto
(*jump*): todos los procesos parten de la misma semilla y el proceso r "salta" r × 2¹²⁸ posiciones
de la secuencia. Los tramos quedan separados por construcción. Además es más rápido que `drand48`.
Es la mejora que ataca el punto débil declarado del diseño. Está implementado en la rama `main`.

**2. Procesamiento por bloques y vectorización (SIMD).** *En simple:* el procesador puede hacer la
misma operación sobre 4 u 8 números a la vez, como una cajera que pasa 8 productos juntos. Para
aprovecharlo hay que generar los números en bloques y contar en un bucle sin dependencias entre
vueltas. *Límite:* el generador depende de su estado anterior y no se vectoriza solo; el `while` de
e tiene largo variable.

**3. Híbrido MPI + OpenMP.** MPI reparte entre máquinas (procesos); OpenMP reparte entre los núcleos
de una misma máquina (hilos que comparten memoria). En un clúster de muchos nodos: un proceso MPI por
nodo y varios hilos dentro. Habría que pasar de `drand48` a `erand48` con un estado por hilo.

**4. Cuasi-Monte Carlo (secuencias de Sobol o Halton).** *En simple:* los puntos al azar dejan huecos
y amontonamientos; estas secuencias reparten los puntos de forma pareja a propósito. El error baja
cerca de 1/N en lugar de 1/√N: con 10⁶ puntos se lograría lo que hoy cuesta ~10¹². **Es la única
mejora que cambia el orden de convergencia**; las demás solo hacen más rápida cada muestra. Sirve
directo para π; para e no, porque cada ensayo usa una cantidad variable de números.

**5. GPU (CUDA).** Miles de núcleos simples generando muestras independientes a la vez. Requiere un
generador pensado para paralelismo masivo. (Los nodos del clúster son solo CPU.)

**6. Generadores basados en contador (Philox, Threefry).** El número aleatorio i-ésimo se calcula
directamente a partir de (semilla, i); cada proceso usa un rango de i distinto, sin necesidad de saltos.

**7. Reducción de varianza.** Bajar σ sin aumentar N. Ejemplo, variables antitéticas: por cada punto
(x, y) usar también (1 − x, 1 − y); los errores de la pareja tienden a compensarse.

**8. Medición más completa.** Medir el tiempo total del lanzamiento (costo de arranque), registrar
la frecuencia del procesador para confirmar la hipótesis térmica, y medir escalado débil (N
proporcional a P) además del escalado fuerte.

**Comparación con una librería.** No existe una librería que traiga este problema ya resuelto. La
referencia natural es NumPy (operaciones vectorizadas). En una medición informal en la notebook con
N = 10⁸ y un núcleo: NumPy 17 ns por muestra en π y 34 ns en e, contra unos 19 y 46 ns de esta
versión. Queda parejo en π porque NumPy genera arreglos enteros en memoria y los recorre varias
veces, mientras que el C trabaja muestra por muestra en los registros del procesador.

---

## 10. Preguntas probables sobre los resultados

**¿Por qué el speedup no es igual a la cantidad de núcleos, si el problema es embarazosamente paralelo?**
Por el hardware, no por el programa: en la notebook, un procesador de 15 W baja la frecuencia con
todos los núcleos cargados, y más allá de 4 procesos usa hilos lógicos. La evidencia es que las
ejecuciones cortas escalan mejor que las largas.

**¿Cómo sabés que es eso y no la ley de Amdahl?**
Amdahl depende de la fracción serial, que no cambia con la duración de la ejecución. Si la
eficiencia cambia con la duración (mejor en ejecuciones cortas), una fracción serial fija no lo
explica; un límite térmico o de potencia sostenida, sí.

**¿Por qué con 8 procesos sigue mejorando si la notebook tiene 4 núcleos?**
Por los hilos lógicos: cada núcleo físico expone dos hilos que comparten las unidades de cálculo.
Aportan algo, no el doble.

**¿Qué significa una eficiencia mayor que 1?**
Si aparece, es en cómputos de milisegundos: ruido de medición, no un efecto real.

**¿Por qué usaste la mediana?**
Porque el ruido de los tiempos es de un solo lado (el sistema solo puede demorar). Ejemplo en la sección 1.

**¿Los resultados paralelos son correctos, además de rápidos?**
Sí: están incluidos en el análisis de error y siguen la recta teórica. Además, con un proceso y la
misma semilla, la versión MPI da exactamente lo mismo que la serial.

**¿Qué pasaría si todos los procesos usaran la misma semilla?**
El speedup se vería igual de bien, pero el error sería el de N/P muestras. Por eso no alcanza con
mirar el speedup: hay que mirar también el error.

**¿Qué harías distinto con más tiempo?**
Cambiar el generador por uno con saltos (resuelve el punto débil de la semilla por proceso), medir
el costo de arranque, registrar la frecuencia del procesador y probar cuasi-Monte Carlo para π.
