# 03 — Gráficos, speedup y conclusiones

> **Apunte de estudio.** Describe los resultados de la rama `main`.
> Todos los números de este apunte salen de `results/summary/tablas.md`, medidos en la PC local.
> **Los del clúster todavía no existen:** la sección 9 dice qué correr y qué partes completar después.

Contenido:

1. Las métricas, en simple
2. Los dos gráficos de intuición
3. Convergencia y error
4. Las versiones seriales
5. Tiempo y speedup en función de P
6. El costo de arrancar MPI
7. Versión ingenua contra versión final
8. Eficiencia y comparación PC – clúster
9. Qué falta medir en el clúster
10. Conclusiones
11. Mejoras futuras
12. Preguntas probables sobre los resultados

Para cada gráfico: **qué muestra → por qué tiene esa forma → qué decir**.

---

## 1. Las métricas, en simple

| Métrica | Fórmula | En simple |
|---|---|---|
| Tiempo mediano | mediana de las 7 repeticiones | El valor "del medio" al ordenar los 7 tiempos |
| Speedup | S = T serial / T con P procesos | Cuántas veces más rápido que con un solo proceso |
| Eficiencia | E = S / P | Qué fracción de cada proceso se aprovecha. 1 = perfecto |
| Error absoluto | \|estimación − valor real\| | Cuánto me equivoqué |
| Error relativo | error absoluto / valor real | Lo mismo, en proporción |

**Analogía del speedup y la eficiencia.** Un pintor tarda 8 horas en pintar una casa. Con 4
pintores tardan 2,5 horas. Speedup = 8 / 2,5 = 3,2. Eficiencia = 3,2 / 4 = 0,8: cada pintor
rindió al 80 %, porque se estorban, comparten la escalera, etc.

**¿Por qué la mediana y no el promedio?**
Los tiempos tienen ruido de un solo lado: el sistema operativo puede **demorar** una ejecución
(otra tarea, una interrupción), pero nunca la acelera. Una sola ejecución muy lenta arrastra el
promedio hacia arriba; la mediana la ignora. Ejemplo real de mis datos, `mpi_v2` de π con N = 10⁹
y P = 1: los siete tiempos fueron 9,2 · 8,9 · 10,4 · 12,1 · 8,6 · 9,4 · 8,6 s. Promedio 9,6 s;
mediana 9,2 s. El 12,1 es un valor atípico que el promedio absorbe y la mediana no.

**¿Por qué 7 repeticiones?** Impar, para que la mediana sea una medición real y no el promedio de
dos. Suficiente para que hasta tres ejecuciones perturbadas no cambien el resultado.

**¿Contra qué se calcula el speedup?** Contra la versión **serial equivalente** (`serial_v2` para
`mpi_v2`), no contra `mpi_v2` con P = 1. Es la comparación honesta: incluye lo que cuesta MPI.

---

## 2. Los gráficos de intuición

### `intuicion_pi`

**Qué muestra.** 3000 puntos al azar en el cuadrado unitario. Azul: dentro del cuarto de círculo.
Naranja: fuera. La línea negra es el arco. El título hace la cuenta: π ≈ 4 × 2371 / 3000 = 3,1613.

**Qué decir.** "La proporción de puntos azules estima el área del cuarto de círculo, π/4. Con 3000
puntos el error esperado es 1,64/√3000 ≈ 0,03, y el obtenido fue 0,02: lo esperable."

### `intuicion_e`

**Qué muestra.** 100 000 ensayos. Eje horizontal: cuántos números hicieron falta para pasar de 1.
Barras: proporción observada. Puntos negros: probabilidad teórica (n − 1)/n!.

**Por qué tiene esa forma.** Nunca alcanza con 1 número. La mitad de las veces alcanzan 2, un
tercio de las veces hacen falta 3, y cae muy rápido (por el factorial). El promedio ponderado de
esas cantidades es e: 2 × 0,5 + 3 × 0,333 + 4 × 0,125 + … = 2,718.

**Qué decir.** "Las barras coinciden con los puntos teóricos: el experimento reproduce la
distribución que predice la demostración."

---

## 3. Convergencia y error

### `convergencia`

**Qué muestra.** Cada punto es **una estimación** (una ejecución). Eje horizontal: N en escala
logarítmica. Línea negra: valor real. Banda sombreada: donde debería caer el 95 % de las
estimaciones según la teoría (±1,96 σ/√N).

**Por qué tiene esa forma.** Es un embudo: con N chico las estimaciones se dispersan mucho; al
crecer N se aprietan contra el valor real. El embudo se cierra **despacio**: para angostarlo 10
veces hay que multiplicar N por 100.

**Qué decir.** "Casi todos los puntos caen dentro de la banda, y algunos fuera: es lo esperado,
porque la banda es del 95 %, no del 100 %. Hay 35 estimaciones por cada N; uno o dos puntos fuera
es normal."

### `error_vs_n` (el gráfico más importante de la parte matemática)

**Qué muestra.** Ejes logarítmicos. Línea punteada: error teórico σ/√N. Puntos grandes: error
medido (raíz del error cuadrático medio de las 35 ejecuciones con ese N). Puntos tenues: el error
de cada ejecución individual.

**Por qué es una recta de pendiente −1/2.**

$$\text{error} = \frac{\sigma}{\sqrt{N}} \;\Rightarrow\; \log(\text{error}) = \log\sigma - \tfrac{1}{2}\log N$$

En escala log-log eso es una recta: pendiente −1/2 y ordenada log σ. La pendiente es la misma
para π y para e (es la ley del método); la altura cambia porque σ es distinta (1,642 y 0,875).
Por eso son dos rectas **paralelas**, con la de e más abajo.

**Resultados medidos:**

| | Pendiente ajustada | Teoría |
|---|---|---|
| π | −0,48 | −0,50 |
| e | −0,50 | −0,50 |

| N | error medido π | teoría π | error medido e | teoría e |
|---|---|---|---|---|
| 10⁵ | 4,4 × 10⁻³ | 5,2 × 10⁻³ | 2,6 × 10⁻³ | 2,8 × 10⁻³ |
| 10⁶ | 1,4 × 10⁻³ | 1,6 × 10⁻³ | 8,0 × 10⁻⁴ | 8,8 × 10⁻⁴ |
| 10⁷ | 5,0 × 10⁻⁴ | 5,2 × 10⁻⁴ | 2,6 × 10⁻⁴ | 2,8 × 10⁻⁴ |
| 10⁸ | 1,8 × 10⁻⁴ | 1,6 × 10⁻⁴ | 8,5 × 10⁻⁵ | 8,8 × 10⁻⁵ |
| 10⁹ | 5,0 × 10⁻⁵ | 5,2 × 10⁻⁵ | 2,4 × 10⁻⁵ | 2,8 × 10⁻⁵ |

El cociente medido/teoría está entre 0,82 y 1,10 en todos los casos.

**Por qué hay zigzag y los puntos tenues están tan dispersos.** El error de una ejecución es en sí
mismo un número aleatorio. σ/√N es su tamaño *típico*. Una ejecución puede caer por casualidad muy
cerca del valor real (puntos muy abajo) o a dos veces el error típico. En escala logarítmica los
errores chicos "se estiran" hacia abajo, por eso la nube se ve asimétrica. El punto grande promedia
35 ejecuciones y por eso sigue la recta mucho mejor, aunque con 35 muestras todavía le queda algo
de ruido (de ahí el −0,48 en lugar de −0,50 exacto).

**Qué decir.** "El error medido sigue la recta teórica con pendiente −0,48 para π y −0,50 para e.
Esto valida tres cosas a la vez: la teoría, la implementación, y la calidad del generador y de la
separación entre procesos, porque las ejecuciones paralelas están incluidas en esos puntos. Si los
procesos repitieran números, el error dejaría de bajar como 1/√N."

---

## 4. Las versiones seriales (`serial_versiones_pc`)

**Qué muestra.** Barras: nanosegundos por muestra de V0, V1 y V2, para π y para e.

| | V0 | V1 | V2 | V0 → V1 | V1 → V2 |
|---|---|---|---|---|---|
| π (N = 10⁹) | 27,3 ns | 27,2 ns | 9,4 ns | 1,00× | 2,9× |
| e (N = 10⁸) | 40,3 ns | 42,0 ns | 15,3 ns | 0,96× | 2,7× |

**Por qué tiene esa forma.**

- **V0 → V1 no mejora el tiempo.** Es el resultado más interesante para defender, y hay que
  decirlo sin vueltas. Dos razones:
  1. Con `-O3` el compilador ya hacía por su cuenta buena parte de lo que la V1 hace a mano
     (`pow(x, 2)` → `x * x`, el `if` → suma sin salto).
  2. El costo dominante es `rand()`, que no se tocó. Cada muestra de π llama dos veces a `rand()`;
     la aritmética que se optimizó es una fracción menor del total.
  En e la V1 quedó incluso un 4 % más lenta: una diferencia del orden de la variación entre
  corridas, no una mejora ni un empeoramiento que pueda afirmar.
- **V1 → V2 mejora casi 3 veces.** Ahí estaba el cuello de botella: el generador. xoshiro no tiene
  candado ni estado global y se integra dentro del bucle.
- **e cuesta más que π** por muestra: cada ensayo de e usa en promedio 2,72 números aleatorios
  contra 2 de π, y además tiene un `while` de duración impredecible.

**Qué decir.** "La optimización aritmética no aportó tiempo porque el compilador ya la hacía y
porque el cuello de botella era el generador. Es la ley de Amdahl dentro de un programa serial:
optimizar una parte que pesa poco no cambia el total. El valor real de la V1 es la **corrección**:
los contadores de 64 bits permiten N mayores a 2 × 10⁹. La mejora de rendimiento vino de atacar el
cuello de botella correcto en la V2."

**Si preguntan "¿entonces para qué sirvió la V1?"** Para medirlo. Antes de medir, la hipótesis
razonable era que quitar `sqrt` y `pow` ayudaría. La medición la refutó, y eso orientó la V2.
Además aporta `uint64_t`, sin el cual no se puede llegar a N = 10¹⁰.

---

## 5. Tiempo y speedup en función de P

### `tiempo_vs_p_pc`

**Qué muestra.** Tiempo mediano de `mpi_v2` (eje vertical, logarítmico) contra P, una línea por
cada N. La línea vertical marca los 4 núcleos físicos.

**Por qué tiene esa forma.** Las líneas son casi paralelas y separadas por un factor 10: el tiempo
es proporcional a N. Todas bajan al aumentar P. Si el escalado fuera perfecto, cada vez que P se
duplica el tiempo bajaría a la mitad; bajan menos que eso.

### `speedup_pc`

**Qué muestra.** Speedup contra P, una línea por N. Línea punteada gris: el ideal S = P.

**Resultados con N = 10⁹ (el caso que importa):**

| P | π: tiempo | π: S | π: E | e: tiempo | e: S | e: E |
|---|---|---|---|---|---|---|
| serial | 9,43 s | — | — | 14,65 s | — | — |
| 1 | 9,23 s | 1,02 | 1,02 | 16,84 s | 0,87 | 0,87 |
| 2 | 5,37 s | 1,76 | 0,88 | 10,13 s | 1,45 | 0,72 |
| 4 | 3,47 s | 2,72 | 0,68 | 6,52 s | 2,25 | 0,56 |
| 8 | 2,45 s | 3,85 | 0,48 | 4,59 s | 3,19 | 0,40 |

**Por qué la curva se dobla.** Hay que separar cuatro efectos; no todo es Amdahl.

**(a) No es la fracción serial (Amdahl).** Dentro de la zona cronometrada no hay trabajo serial: la
lectura de argumentos, la siembra y el arranque quedan fuera. La ley de Amdahl dice
S = 1 / (f + (1 − f)/P), con f la fracción no paralelizable; acá f es prácticamente 0, así que
Amdahl por sí sola predice un speedup casi ideal.

**(b) No es la comunicación.** Hay una sola `MPI_Reduce` de un entero de 8 bytes. Cuesta
microsegundos contra segundos de cómputo.

**(c) Es el hardware de la notebook: límite de potencia y temperatura.** El i5-10210U es un
procesador de bajo consumo (15 W). Con un solo núcleo activo puede usar su frecuencia turbo máxima
(4,2 GHz según el fabricante). Con varios núcleos activos a la vez y de forma sostenida, el
límite de potencia y de temperatura lo obliga a bajar la frecuencia de **todos**. Cada proceso
corre más lento que cuando estaba solo, y el speedup queda por debajo de P aunque el programa
escale bien.

**La evidencia está en mis propios datos:** las ejecuciones cortas escalan mucho mejor que las largas.

| N | duración con P = 4 | eficiencia con P = 4 (π) |
|---|---|---|
| 10⁵ | 0,2 ms | 1,13 |
| 10⁶ | 2 ms | 1,15 |
| 10⁷ | 28 ms | 0,82 |
| 10⁸ | 0,32 s | 0,71 |
| 10⁹ | 3,5 s | 0,68 |

El mismo programa, con la misma proporción de trabajo paralelo, tiene eficiencia cercana a 1 cuando
dura milisegundos y 0,68 cuando dura segundos. Lo único que cambia es **cuánto tiempo** están los
cuatro núcleos cargados: es lo que se espera de un límite térmico y de potencia sostenida. Dicho
con honestidad: es la explicación consistente con los datos, pero no registré la frecuencia del
procesador durante las corridas, así que es una hipótesis bien apoyada y no una medición directa.

**(d) De 4 a 8 procesos: hilos lógicos (hyper-threading).** La PC tiene 4 núcleos físicos y 8
hilos. Dos hilos del mismo núcleo **comparten** las unidades de cálculo; no son dos núcleos. Pasar
de 4 a 8 procesos sube el speedup de 2,72 a 3,85 (un 41 % más), no el doble. Analogía: dos
cocineros compartiendo una sola hornalla; algo ganan porque aprovechan los tiempos muertos del
otro, pero no cocinan el doble.

**Eficiencias mayores que 1 con N chico (1,13, 1,15).** No es un speedup "superlineal" real. Son
núcleos de cómputo de menos de un milisegundo, donde el ruido de medición pesa mucho y donde la
referencia serial se mide en un proceso recién lanzado. No hay que venderlo como un logro.

**En e, `mpi_v2` con P = 1 es más lento que `serial_v2` (S = 0,87).** Es el mismo núcleo de
cómputo, así que debería dar 1. La diferencia es estable en todos los N (0,87 a 0,92). No la
investigué a fondo; las causas posibles son que el binario MPI se compila con otro envoltorio
(`mpicc`) y puede quedar distinto en cómo se integra el bucle, o el estado de la máquina en el
momento de cada bloque de mediciones. Consecuencia práctica: todos los speedups de e están
multiplicados por ese ~0,87; respecto de su propio P = 1, e escala igual que π (con P = 4: 16,84 /
6,52 = 2,58, contra 2,66 en π).

**Qué decir.** "El programa es embarazosamente paralelo y sin fracción serial apreciable, así que
la teoría predice speedup casi lineal. En mi notebook mido 1,76 con 2 procesos y 2,72 con 4. La
caída no viene del programa sino del hardware: un procesador de 15 W no puede mantener la
frecuencia turbo con todos los núcleos cargados. Lo respalda que las ejecuciones cortas sí
alcanzan eficiencia cercana a 1. Más allá de 4 procesos uso hilos lógicos, que comparten núcleo y
aportan solo un 41 % adicional."

---

## 6. El costo de arrancar MPI (`arranque_pc`)

**Qué muestra.** Para `mpi_v2`, π, P = 4. Línea azul: tiempo de cómputo cronometrado
(`MPI_Wtime`). Línea naranja: tiempo total del lanzamiento (desde que se ejecuta `mpirun` hasta que
termina). Ejes logarítmicos.

**Por qué tiene esa forma.** La azul es una recta: el cómputo es proporcional a N. La naranja es
**plana** al principio: lanzar `mpirun`, crear los procesos e inicializar MPI cuesta alrededor de
**0,33 a 0,45 s**, sin importar N. Recién cuando el cómputo supera ese costo fijo (cerca de
N = 10⁸) las dos líneas se juntan.

| N | cómputo (P = 4) | lanzamiento completo (P = 4) | cómputo de serial_v2 |
|---|---|---|---|
| 10⁵ | 0,0002 s | 0,35 s | 0,001 s |
| 10⁷ | 0,03 s | 0,37 s | 0,09 s |
| 10⁹ | 3,47 s | 3,86 s | 9,43 s |

**Qué decir.** "Con N chico paralelizar es contraproducente: con N = 10⁵ el cómputo paralelo tarda
0,2 milisegundos pero lanzar MPI cuesta 0,35 segundos, unas 1500 veces más. La versión serial
termina en 1 milisegundo. El punto de equilibrio está donde el trabajo serial iguala al costo de
arranque: a 9,4 ns por muestra, unos 3 a 4 × 10⁷ puntos. Por debajo conviene serial; por encima,
MPI."

**Este es el régimen "dominado por sobrecosto".** Atención al vocabulario: el programa **nunca**
queda limitado por comunicación (hay una sola reducción). Lo que domina con N chico es el **costo
fijo de arranque**. Con N grande domina el cómputo. Si el profesor dice "limitado por
comunicación", la respuesta precisa es: "en este programa el sobrecosto no es de comunicación sino
de arranque de procesos; la comunicación es una reducción de 8 bytes".

**Por qué mi speedup no muestra ese efecto.** Porque el speedup se calcula con el tiempo
cronometrado, que excluye `MPI_Init`. Es una decisión de metodología: mide la escalabilidad del
algoritmo. El costo de arranque se informa por separado, con esta figura.

---

## 7. Versión ingenua contra versión final (`speedup_v0_v2_pc`)

**Qué muestra.** Speedup de `mpi_v0` (azul) y `mpi_v2` (verde) con N = 10⁸. Línea punteada larga:
ideal. Línea de puntos: ley de Amdahl con 5 % de fracción serial, solo como referencia visual.

| P | `mpi_v0` π: S | `mpi_v2` π: S | `mpi_v0` tiempo | `mpi_v2` tiempo |
|---|---|---|---|---|
| 1 | 1,01 | 0,99 | 2,74 s | 0,91 s |
| 2 | 1,85 | 1,79 | 1,50 s | 0,50 s |
| 4 | 2,70 | 2,83 | 1,03 s | 0,32 s |
| 8 | 3,95 | 4,36 | 0,70 s | 0,21 s |

**Por qué tiene esa forma.** Las dos curvas son casi iguales: el speedup depende de la estructura
paralela (que es la misma) y del hardware, no de qué tan rápido es el núcleo.

**Qué decir (la conclusión más valiosa de esta figura).** "Las dos versiones escalan parecido,
pero `mpi_v2` es unas 3 veces más rápida en tiempo absoluto. `mpi_v0` con **8 procesos** tarda
0,70 s; `serial_v2` con **un solo proceso** tarda 0,90 s. O sea: ocho procesos de la versión
ingenua apenas le ganan a un proceso de la versión optimizada. El speedup mide qué tan bien se
aprovechan los procesadores, no qué tan bueno es el programa. Primero se optimiza el código serial
y después se paraleliza."

**Sobre la curva de Amdahl del gráfico.** Es una referencia para mostrar qué forma tendría una
limitación por fracción serial: se aplana hacia un techo de 1/f = 20. Mis curvas quedan por debajo
de ella ya desde P = 2, pero por la causa de hardware explicada antes, no porque el programa tenga
5 % de código serial.

---

## 8. Eficiencia y comparación PC – clúster (`eficiencia_sistemas`)

**Qué muestra.** Eficiencia E = S/P de `mpi_v2` contra P, una línea por sistema. Línea punteada: E = 1.

**Por qué empieza cerca de 1 y baja.** Con P = 1 no hay nada que repartir: E ≈ 1. Al sumar
procesos, cada uno rinde un poco menos (en la PC, por el límite de potencia y después por los
hilos lógicos). En la PC, π con N = 10⁹: 1,02 → 0,88 → 0,68 → 0,48.

**Qué dice sobre el límite de escalado.** La eficiencia indica cuándo deja de convenir agregar
procesos. En la PC, con 8 procesos se aprovecha menos de la mitad de cada uno: el tiempo sigue
bajando (de 3,47 a 2,45 s), pero con retornos decrecientes.

### Cómo explicar la diferencia PC – clúster

**Hoy la figura tiene una sola línea (la PC).** Lo que sigue es lo que se **espera** ver en el
clúster por las características del hardware; hay que confirmarlo con las mediciones y ajustar.

| | PC: Intel i5-10210U | Clúster: AMD EPYC 7B12 |
|---|---|---|
| Tipo | Notebook, bajo consumo (15 W) | Servidor |
| Núcleos | 4 físicos, 8 hilos | Decenas por zócalo (confirmar con `collect_sysinfo.sh`) |
| Frecuencia | Turbo alto con 1 núcleo, cae con todos cargados | Diseñado para sostener la frecuencia con todos los núcleos cargados |
| Refrigeración | Limitada | De centro de datos |
| Caché L3 | 6 MB | Mucho mayor |
| Memoria | 1 nodo | Varios dominios NUMA |

Qué se espera y por qué:

1. **Eficiencia más alta y más plana en el clúster**, mientras P no supere los núcleos físicos: un
   procesador de servidor no baja tanto la frecuencia al cargar todos los núcleos.
2. **Un solo núcleo del clúster puede ser más lento que uno de la notebook.** Los procesadores de
   servidor priorizan muchos núcleos a frecuencia moderada; la notebook, con un solo núcleo
   activo, usa un turbo alto. No hay que sorprenderse si `serial_v2` tarda más en el clúster.
3. **Más núcleos: speedup máximo mayor.** La PC se queda en 4 núcleos; el clúster permite P = 16, 32 o más.
4. **Caché, ancho de banda de memoria y NUMA casi no influyen en este programa.** Es un punto fino
   y vale la pena decirlo: el núcleo de cómputo usa 32 bytes de estado y un par de contadores;
   todo vive en registros del procesador. No recorre arreglos ni compite por memoria. Por eso este
   problema escala bien en cualquier máquina, a diferencia de un código que mueve muchos datos
   (por ejemplo un producto de matrices), donde el ancho de banda de memoria y la ubicación NUMA
   limitan el escalado.
5. **Atención a los núcleos virtuales.** El modelo EPYC 7B12 es el que usan máquinas virtuales en
   la nube. Si los nodos del clúster son máquinas virtuales, una "CPU" puede ser un **hilo** y no
   un núcleo físico. En ese caso, el speedup se doblará al pasar la mitad de las CPU visibles,
   igual que en la PC al pasar de 4 a 8. `collect_sysinfo.sh` registra hilos por núcleo y si hay
   hipervisor.

---

## 9. Qué falta medir en el clúster

El servidor (`cluster_boogie`, AMD EPYC 7B12) se usa desde la terminal de JupyterLab, con `mpirun`
directo y sin SLURM. Conviene pedir la asignación de **24 núcleos**: da más puntos en la curva.

En la terminal del servidor, dentro de la carpeta del proyecto (rama `main`):

```bash
# 1) Comprobación previa (2 minutos): herramientas, núcleos reales y prueba de escalado
MPIRUN_FLAGS="--bind-to none --oversubscribe" bash scripts/check_system.sh 24

# 2) Descripción del sistema (agregar PHYS_CORES=12 adelante si el paso 1 mostró que son hilos)
SYSTEM=cluster_boogie bash scripts/collect_sysinfo.sh

# 3) Barrido principal: N de 10^5 a 10^9, 7 repeticiones (del orden de 30 minutos)
SYSTEM=cluster_boogie PS="1 2 4 8 12 16 24" MPIRUN_FLAGS="--bind-to none --oversubscribe" HWTHREAD_FLAGS="" bash scripts/run_benchmark.sh

# 4) Opcional: N = 10^10, solo la versión final, 3 repeticiones (del orden de 40 minutos)
SYSTEM=cluster_boogie APPEND=1 NS=10000000000 MAX_N=10000000000 REPS=3 SERIAL_PROGRAMS=serial_v2 MPI_PROGRAMS=mpi_v2 PS="1 2 4 8 12 16 24" MPIRUN_FLAGS="--bind-to none --oversubscribe" HWTHREAD_FLAGS="" bash scripts/run_benchmark.sh
```

Los tiempos son estimaciones a partir de la velocidad de la notebook; la velocidad de cada núcleo
del servidor no la conozco hasta medir.

**Qué mirar en el paso 1:**

- Si falta `mpicc` o `mpirun`: la imagen "Python Científico" puede no traer MPI. Sin permisos de
  administrador, probar `conda install -c conda-forge openmpi`; si no se puede, pedirlo a la cátedra.
- Si el usuario es `root`: agregar `--allow-run-as-root` a `MPIRUN_FLAGS`.
- La prueba de escalado dice si los 24 "núcleos" son físicos o son 12 con dos hilos cada uno.

**Por qué esas opciones** (pueden preguntarlo):

- `--bind-to none`: Open MPI normalmente fija cada proceso a un núcleo. Dentro de un contenedor
  solo ve una parte de la máquina y esa fijación puede fallar o amontonar procesos en el mismo núcleo.
- `--oversubscribe`: Open MPI puede contar mal cuántos núcleos tiene disponibles en el contenedor.
- `HWTHREAD_FLAGS=""`: desactiva la opción de hilos lógicos que el script agrega en la PC.

**Por qué esos valores de P y de N:**

- P = 1, 2, 4, 8 coinciden con la PC, para comparar los dos sistemas punto a punto. P = 12, 16 y
  24 son los que solo el servidor permite. No conviene pedir más procesos que núcleos asignados:
  el contenedor limita la CPU y el speedup se aplana por un motivo artificial.
- Con N = 10⁹ y P = 24 cada proceso hace unos 4 × 10⁷ muestras (décimas de segundo): sigue siendo
  muchísimo más que el costo de la reducción, así que **N = 10⁹ alcanza para estudiar el escalado
  hasta 24 procesos**. N = 10¹⁰ no hace falta para el speedup; aporta un punto más en la curva de
  error y muestra que el programa funciona por encima del límite de `int`. Por eso es opcional y con 3 repeticiones.
- Con N = 10⁵ y P = 24 cada proceso hace unas 4000 muestras (microsegundos). Ese punto no mide
  escalado: muestra el régimen donde manda el costo fijo.

**El servidor es compartido.** Otros usuarios pueden estar usando la misma máquina, y eso mete
ruido en los tiempos. La mediana de 7 repeticiones protege de ejecuciones aisladas; además
`analyze.py` ahora imprime "avisos de coherencia" cuando una configuración tiene mucha dispersión
o cuando MPI con un proceso no coincide con la versión serial. Si aparecen muchos avisos del
servidor, repetir el barrido en otro momento.

Después, descargar `results/raw/cluster_boogie.csv` y `results/sysinfo/cluster_boogie.txt` desde
JupyterLab (clic derecho → Download), copiarlos a las mismas carpetas en la PC y ejecutar:

```bash
python analysis/analyze.py
python analysis/plot_convergencia.py
python analysis/plot_rendimiento.py
```

Las figuras por sistema se generan solas (`speedup_cluster_boogie`, etc.) y `eficiencia_sistemas`
pasa a tener dos líneas.

**Nota sobre las semillas.** El barrido de la PC usó semillas `100 × P + repetición`; el script
ahora usa `100000 × repetición + 1000 × P`. El motivo: `mpi_v0` siembra cada proceso con
`semilla + rango`, y con el esquema anterior un proceso de una repetición repetía la semilla de
otro de la repetición siguiente. No afecta a los tiempos ni al análisis de error (que usa solo la
versión final, donde la independencia la da `jump()`), así que los datos de la PC siguen valiendo.

### Experimento adicional (opcional): hasta 96 procesos

Hacerlo **después** del barrido de 24, en otra sesión con el perfil de 96 núcleos (384 GB). Usa
otro nombre de sistema (`cluster_boogie_96`), así queda en archivos aparte y no pisa nada.

```bash
# 1) Comprobación previa con 96
MPIRUN_FLAGS="--bind-to none --oversubscribe" bash scripts/check_system.sh 96

# 2) Descripción del sistema (agregar PHYS_CORES=48 adelante si el paso 1 mostró que son hilos)
SYSTEM=cluster_boogie_96 bash scripts/collect_sysinfo.sh

# 3) Barrido acotado: solo la versión final, N = 10^9 y 10^10, 3 repeticiones (del orden de 45 minutos)
SYSTEM=cluster_boogie_96 NS="1000000000 10000000000" MAX_N=10000000000 REPS=3 \
SERIAL_PROGRAMS=serial_v2 MPI_PROGRAMS=mpi_v2 PS="1 2 4 8 16 24 32 48 64 96" \
MPIRUN_FLAGS="--bind-to none --oversubscribe" HWTHREAD_FLAGS="" \
bash scripts/run_benchmark.sh
```

El tiempo es una estimación con la velocidad de la notebook.

**Por qué solo N = 10⁹ y 10¹⁰.** Con 96 procesos y N = 10⁹ cada uno hace unos 10⁷ muestras: una
décima de segundo. Es medible pero ya con ruido; con N = 10¹⁰ cada proceso trabaja alrededor de un
segundo y la medición es sólida. Los N más chicos solo mostrarían ruido. **Por qué solo la versión
final:** el objetivo es ver hasta dónde escala, y las versiones seriales ya están comparadas.

**Qué archivos descargar:** `results/raw/cluster_boogie_96.csv` y `results/sysinfo/cluster_boogie_96.txt`.

**Qué cambia en los gráficos.** Los scripts lo tratan como un sistema más:

- Se generan `speedup_cluster_boogie_96`, `tiempo_vs_p_cluster_boogie_96` y `arranque_cluster_boogie_96`.
  No se generan `serial_versiones` ni `speedup_v0_v2` para ese sistema, porque no se midieron esas versiones.
- Como P pasa de 32, el speedup se dibuja en **escala logarítmica en los dos ejes**. En escala
  lineal los puntos 1, 2, 4 y 8 quedarían amontonados en una esquina. En log-log el ideal S = P
  sigue siendo una recta diagonal y cada duplicación de P ocupa el mismo ancho.
- `eficiencia_sistemas` pasa a tener tres líneas (PC, clúster con 24, clúster con 96).
- Las estimaciones entran también en el análisis de error, que gana un punto en N = 10¹⁰.

**Cómo leer la curva de speedup hasta 96.** Mirar dónde se separa de la diagonal:

| Lo que se ve | Explicación más probable | Cómo confirmarlo |
|---|---|---|
| Sigue la diagonal hasta cierto P y ahí se dobla | Se acabaron los núcleos físicos; desde ahí son hilos lógicos (dos hilos comparten un núcleo) | En el archivo de sistema: "Thread(s) per core: 2". El quiebre debería estar cerca de la mitad de las CPU asignadas |
| Se dobla de forma gradual desde antes | Menor frecuencia del procesador con muchos núcleos activos, o carga de otros usuarios | Comparar con el barrido de 24: si en P = 24 da distinto, hubo ruido |
| Se aplana del todo en un valor | El contenedor limita la CPU a ese valor | La línea "cpu.max" del archivo de sistema |
| Sube y baja sin patrón | Ruido: el servidor es compartido | Los "avisos de coherencia" de `analyze.py`; repetir en otro momento |
| La curva de N = 10⁹ queda por debajo de la de N = 10¹⁰ con P alto | Con poco trabajo por proceso pesa más cualquier costo fijo | Es el mismo efecto que en la PC con N chico |

Dato de contexto: el procesador tiene 64 núcleos físicos por zócalo. 96 "cores" asignados no entran
en un zócalo como núcleos físicos: son hilos lógicos o abarcan dos zócalos. El archivo de sistema
(líneas "Socket(s)", "Core(s) per socket", "Thread(s) per core") dice cuál de los dos.

**Si resulta que abarca dos zócalos y preguntan por NUMA.** NUMA significa que cada zócalo tiene su
propia memoria cercana y acceder a la del otro es más lento. A este programa casi no lo afecta: el
núcleo de cómputo usa 32 bytes de estado y un par de contadores, que viven en registros del
procesador; no recorre memoria. Es la misma razón por la que el ancho de banda de memoria no limita
el escalado.

**Qué decir.** "Además del barrido hasta 24 procesos, hice una prueba hasta 96 para ver dónde deja
de escalar. El speedup sigue cerca del ideal hasta P = [completar] y después se dobla, porque
[completar con la causa confirmada]. Como el programa no tiene parte serial ni comunicación
apreciable, el límite lo pone el hardware."

**Qué NO decir** sin haberlo confirmado: que el quiebre es por la ley de Amdahl (la fracción serial
es prácticamente nula) o por la comunicación (es una sola reducción de 8 bytes por proceso).

**Cuándo dejarlo afuera.** Si la curva sale errática o no se llega a entender por qué se dobla, no
incluirla: el barrido de 24 ya cumple la consigna. Borrar `results/raw/cluster_boogie_96.csv` y
`results/sysinfo/cluster_boogie_96.txt`, y volver a ejecutar `analyze.py` y los scripts de gráficos.

Para completar después de medir:

- [ ] Tabla de la sección 8 con los datos reales de `results/sysinfo/cluster.txt`.
- [ ] Speedup y eficiencia del clúster con N = 10⁹ y 10¹⁰.
- [ ] ¿Se confirmó que la eficiencia es más alta que en la PC? ¿Hasta qué P?
- [ ] ¿Un núcleo del clúster es más rápido o más lento que uno de la PC? (comparar `serial_v2`).
- [ ] ¿Las "CPU" son núcleos físicos o hilos?

---

## 10. Conclusiones

Para decir al cierre. Cada una con el dato que la respalda.

1. **El método funciona y cumple la teoría.** El error medido sigue σ/√N con pendiente ajustada
   −0,48 (π) y −0,50 (e), y cociente medido/teoría entre 0,82 y 1,10. Con N = 10⁹ el error típico
   es 5 × 10⁻⁵ en π y 2,4 × 10⁻⁵ en e.

2. **La convergencia es lenta y paralelizar no la cambia.** Un decimal más cuesta 100 veces más
   muestras. Con P procesos se hace el mismo trabajo en menos tiempo (o P veces más muestras en el
   mismo tiempo, con error √P veces menor). El paralelismo compra tiempo, no orden de convergencia.

3. **Hay que medir antes de optimizar.** La optimización aritmética (V1) no redujo el tiempo
   (1,00× en π) porque el compilador ya la hacía y el cuello de botella era el generador. Cambiar
   el generador (V2) lo redujo casi 3 veces (2,9× en π, 2,7× en e).

4. **Optimizar el serial vale más que sumar procesos a un código lento.** Ocho procesos de la
   versión ingenua (0,70 s) apenas le ganan a un proceso de la versión optimizada (0,90 s).

5. **El algoritmo escala casi idealmente; el límite medido es del hardware.** No hay fracción
   serial apreciable en la zona cronometrada ni costo de comunicación relevante. En la notebook el
   speedup con 4 procesos fue 2,72 (π, N = 10⁹), atribuible al límite de potencia de un procesador
   de 15 W; las ejecuciones cortas alcanzan eficiencia cercana a 1. Los hilos lógicos aportan un
   41 % adicional, no el doble.

6. **Hay dos regímenes según N.** Con N chico domina el costo fijo de arrancar MPI (≈ 0,35 s): no
   conviene paralelizar por debajo de unos 3 a 4 × 10⁷ puntos. Con N grande domina el cómputo y el
   paralelismo rinde. El programa nunca queda limitado por comunicación.

7. **Ley de Amdahl y ley de Gustafson.**
   - *Amdahl* (problema de tamaño fijo): S ≤ 1 / (f + (1 − f)/P). Con f ≈ 0 no impone un techo
     práctico acá; sí lo impone si se cuenta el arranque como parte serial, y eso es exactamente
     lo que pasa con N chico.
   - *Gustafson* (el problema crece con los recursos): S = P − f (P − 1). Es la forma natural de
     usar Monte Carlo: con más procesadores no se quiere el mismo N más rápido, sino **más
     muestras en el mismo tiempo** para bajar el error. Con f ≈ 0, el trabajo útil crece casi
     proporcional a P.

8. **La independencia de los números aleatorios es un requisito de corrección, no un detalle.**
   `jump()` garantiza tramos disjuntos de 2¹²⁸ números por proceso; `semilla + rango` con `rand()` no garantiza nada.

9. **Compromisos asumidos.** Se priorizó que el código sea legible y explicable sobre el máximo
   rendimiento: la conversión de entero a real elegida es unas 4 veces más lenta que la alternativa
   con desplazamiento de bits (medido). No afecta al speedup ni a la eficiencia.

*(Agregar la conclusión de la comparación PC – clúster cuando estén los datos.)*

---

## 11. Mejoras futuras

Cada una: qué es, en simple, y por qué mejoraría.

**1. Conversión de entero a real más rápida.**
Usar los 53 bits altos del entero y multiplicar por 2⁻⁵³. Es un cambio de una línea y lo medí:
unas 4 veces más rápido en el núcleo de π. Es la mejora más barata disponible.

**2. Procesamiento por bloques y vectorización (SIMD, AVX2 / AVX-512).**
*En simple:* en lugar de procesar un punto por vez, el procesador puede hacer la misma operación
sobre 4 u 8 números a la vez con instrucciones especiales, como una cajera que pasa 8 productos
juntos. Para aprovecharlo hay que generar los números en bloques chicos (que entren en la caché
L1) y contar en un bucle aparte, sin dependencias entre vueltas, que el compilador pueda vectorizar.
*Límite:* el generador depende de su estado anterior, así que no se vectoriza solo; hay que correr
varios generadores independientes en paralelo dentro del mismo proceso ("carriles"). El bucle de e
tiene un `while` de largo variable, que tampoco se vectoriza bien.

**3. Híbrido MPI + OpenMP.**
*En simple:* MPI reparte entre máquinas (procesos); OpenMP reparte entre los núcleos de una misma
máquina (hilos, que comparten memoria). En un clúster de muchos nodos se usa un proceso MPI por
nodo y varios hilos dentro de cada uno. Reduce la cantidad de procesos y el costo de arranque.
Cada hilo necesitaría su propio generador con `jump()`, igual que ahora cada proceso.

**4. Cuasi-Monte Carlo (secuencias de Sobol o Halton).**
*En simple:* los puntos al azar dejan huecos y amontonamientos. Las secuencias de baja discrepancia
reparten los puntos de forma pareja a propósito, como plantar árboles en una grilla irregular pero
bien distribuida. El error baja cerca de 1/N en lugar de 1/√N: con 10⁶ puntos se lograría lo que
hoy cuesta ~10¹². **Es la única mejora de la lista que cambia el orden de convergencia**; las demás
solo hacen más rápida cada muestra. Sirve directo para π; para e no, porque cada ensayo usa una
cantidad variable de números.

**5. GPU (CUDA).**
*En simple:* una GPU tiene miles de núcleos simples. Como cada muestra es independiente, se pueden
lanzar millones a la vez. Requiere un generador pensado para paralelismo masivo (basado en
contador, como Philox) y contadores por bloque.

**6. Generadores basados en contador (Philox, Threefry).**
En lugar de un estado que avanza, el número aleatorio i-ésimo se calcula directamente como una
función de (semilla, i). La independencia entre procesos es trivial: cada uno usa un rango de i
distinto, sin `jump()`.

**7. Reducción de varianza.**
Técnicas que bajan σ sin aumentar N. Ejemplo, variables antitéticas: por cada punto (x, y) usar
también (1 − x, 1 − y); los errores de la pareja tienden a compensarse.

**8. Medición más robusta.**
Fijar cada proceso a un núcleo (`--bind-to core`), registrar la frecuencia del procesador durante
las corridas para confirmar la hipótesis térmica, y medir en una máquina sin límite de potencia.

---

## 12. Preguntas probables sobre los resultados

**¿Por qué el speedup no es 4 con 4 núcleos, si el problema es embarazosamente paralelo?**
Por el hardware, no por el programa: procesador de 15 W que baja la frecuencia con todos los
núcleos cargados. Evidencia: las ejecuciones cortas tienen eficiencia cercana a 1.

**¿Cómo sabe que es eso y no la ley de Amdahl?**
Amdahl depende de la fracción serial, que no cambia con la duración de la ejecución. Mis datos
muestran que la eficiencia sí cambia con la duración (1,13 con 0,2 ms; 0,68 con 3,5 s). Una
fracción serial fija no explica eso; un límite térmico o de potencia sostenida, sí.

**¿Por qué con 8 procesos sigue mejorando si hay 4 núcleos?**
Por los hilos lógicos: cada núcleo físico expone dos hilos que comparten las unidades de cálculo.
Aportan un 41 % más, no el doble.

**¿Qué significa una eficiencia mayor que 1?**
En mis datos aparece solo en núcleos de menos de un milisegundo: es ruido de medición, no un efecto real.

**¿Por qué usó la mediana?**
Porque el ruido de tiempos es de un solo lado (el sistema solo puede demorar). Ejemplo concreto en la sección 1.

**¿Tuvo algún problema al medir?**
Sí, y conviene contarlo porque muestra criterio. En la primera corrida, los primeros ocho minutos
la máquina funcionó cerca de dos veces más lenta y después se aceleró (se ve en los tiempos
individuales de `serial_v1`: 5,8 · 5,2 · 5,9 · 5,5 · 4,9 · 4,4 · 3,3 s). Eso hacía que `mpi_v0` con
un solo proceso pareciera el doble de rápido que `serial_v0`, lo cual es imposible porque es el
mismo código. Detecté la inconsistencia, repetí ese bloque de mediciones (las tres versiones
seriales y `mpi_v0` de π) de forma contigua, y los tiempos quedaron estables (27,2 a 27,5 s en las
siete repeticiones). La corrida original está guardada como respaldo. Lección: la mediana protege
de ejecuciones aisladas, pero no de un cambio de estado de la máquina que afecta a un bloque
entero; por eso hay que revisar la coherencia de los datos y no solo calcular.

**¿Los resultados paralelos son correctos, además de rápidos?**
Sí: están incluidos en el análisis de error y siguen la recta teórica. Además `mpi_v2` con P = 1
reproduce exactamente a `serial_v2`.

**¿Qué haría distinto con más tiempo?**
Cambiar la conversión de entero a real (4× medido), medir en una máquina sin límite térmico,
registrar la frecuencia del procesador, y probar cuasi-Monte Carlo para π.
