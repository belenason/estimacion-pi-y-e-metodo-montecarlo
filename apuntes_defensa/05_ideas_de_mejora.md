# 05 — Ideas de mejora para la versión simple

> **Apunte de estudio.** Lista de candidatas para decidir cuáles implementar en `version-simple`.
> Ninguna está aplicada todavía, salvo la 7, que ya está preparada y solo hay que correrla.

Ordenadas de más a menos recomendable, pesando lo que aportan a la defensa contra el código nuevo
que habría que explicar.

| # | Mejora | Qué agrega | Toca el código C | Riesgo al defender | Veredicto |
|---|---|---|---|---|---|
| 1 | Costo de arranque de MPI | 3 líneas en `benchmark.sh`, una columna y un gráfico | No | Casi nulo | Aplicar |
| 2 | Marcar los núcleos físicos en el speedup | Una línea vertical en `graficos.py` | No | Nulo | Aplicar |
| 3 | Avisos de coherencia de las mediciones | Unas 10 líneas en `graficos.py` | No | Nulo | Aplicar |
| 4 | Referencia con NumPy | Un script de ~20 líneas y una barra en un gráfico | No | Bajo | Recomendable |
| 5 | Escalado débil (ley de Gustafson) | Una opción en `benchmark.sh` y un gráfico | No | Bajo a medio | Recomendable si hay tiempo |
| 6 | Validar argumentos con `strtoll` | Unas 8 líneas en `montecarlo.h` | Sí | Bajo | Opcional |
| 7 | Experimento hasta 96 procesos | Nada: ya está preparado | No | Medio | Opcional (apunte 04, sección 5) |
| 8 | Programa serial "ingenuo" (`rand()` + `sqrt`) | Un archivo `.c` y un gráfico | Sí | Medio | Solo si sobra tiempo |
| 9 | xoshiro256\*\* con `jump()` | Unas 60 líneas con operaciones de bits | Sí | Alto | Dejar como mejora futura |
| 10 | Referencia "muy eficiente" (Intel MKL o SIMD) | Instalar una librería y código C contra su API | Sí | Alto | No recomendada |

---

## 1. Costo de arranque de MPI

**Qué es.** Medir, además del tiempo de cómputo que informa el programa, cuánto tarda el comando
`mpirun` completo. La diferencia es lo que cuesta lanzar los procesos e inicializar MPI.

**Qué aporta.** Un gráfico que muestra que ese costo es fijo (en `main` dio entre 0,33 y 0,45 s en
la notebook) y la conclusión "por debajo de tal N no conviene paralelizar". Hoy la versión simple
no puede explicar con datos propios por qué el speedup es errático con N chico.

**Cómo se defiende.** "Medí también cuánto tarda el comando entero."

## 2. Marcar los núcleos físicos en el speedup

**Qué es.** Una línea vertical en el gráfico de speedup donde se acaban los núcleos físicos (4 en la notebook).

**Qué aporta.** La pregunta "¿por qué la curva se dobla acá?" es casi segura; la respuesta queda en el gráfico.

**Detalle.** En la notebook el dato sale de `lscpu`. En el clúster hay que indicarlo a mano después
de la prueba de escalado de `verificar_sistema.sh`, porque dentro del contenedor `lscpu` describe la máquina entera.

## 3. Avisos de coherencia de las mediciones

**Qué es.** Que `graficos.py` avise cuando (a) MPI con un proceso no tarda parecido al programa
serial, o (b) entre la repetición más rápida y la más lenta hay mucha diferencia.

**Qué aporta.** Detecta sola el problema que ya pasó en `main`: la notebook cambió de velocidad a
mitad de la corrida y la mediana lo escondía. En el clúster, que es compartido, es todavía más probable.

**Cómo se defiende.** "Verifico que las mediciones sean coherentes antes de sacar conclusiones."

## 4. Referencia con NumPy

**Qué es.** Una versión de los dos estimadores escrita con NumPy (operaciones vectorizadas sobre
bloques de un millón de números), medida con un solo núcleo, como barra de comparación del costo por muestra.

**Qué aporta.** Una comparación contra "la forma estándar de hacerlo en Python". Medición informal
en la notebook con N = 10⁸: NumPy 17 ns por muestra en π y 34 ns en e; la versión simple, unos 19 y
46 ns. O sea, el C propio queda parejo en π. No existe una librería que traiga este problema ya resuelto.

**Cómo se defiende.** "Comparé contra NumPy, que es la herramienta habitual. Queda parejo porque
NumPy genera arreglos enteros en memoria y los recorre varias veces, mientras que el C trabaja
muestra por muestra en los registros del procesador."

**Límite.** Es de un solo núcleo: entra en el gráfico de costo por muestra, no en las curvas de speedup.

## 5. Escalado débil (ley de Gustafson)

**Qué es.** Hoy se mide *escalado fuerte*: mismo N, más procesos, y se mira cuánto baja el tiempo.
El *escalado débil* hace crecer el problema con los procesos: N = P × N₀ (cada proceso hace siempre
la misma cantidad de muestras) y se mira si el tiempo **se mantiene constante**.

**Qué aporta.** Es la forma natural de usar Monte Carlo: con más procesadores no se quiere el mismo
N más rápido, sino más muestras en el mismo tiempo para bajar el error. Conecta directo con la ley
de Gustafson, y agrega un segundo tipo de experimento ("múltiples simulaciones cambiando las variables").

**Cómo se defiende.** "Con escalado fuerte medí cuánto se acelera un problema fijo (Amdahl). Con
escalado débil medí si puedo resolver un problema P veces más grande en el mismo tiempo (Gustafson)."

**Riesgo.** Hay que tener claras las dos definiciones y no mezclarlas.

## 6. Validar argumentos con `strtoll`

**Qué es.** Hoy `atoll("100abc")` devuelve 100 sin avisar. Con `strtoll` se detecta el texto inválido.

**Qué aporta.** Robustez. Es difícil que pregunten por esto.

## 7. Experimento hasta 96 procesos

Ya está preparado; no requiere cambios. Comandos, lectura de la curva y qué decir: apunte 04, sección 5.

## 8. Programa serial "ingenuo"

**Qué es.** Un segundo programa serial con `rand()` y `sqrt()`, para mostrar cuánto se gana con las decisiones tomadas.

**Qué aporta.** Una conclusión del tipo "medir antes de optimizar". En `main` fue muy clara (quitar
la raíz no ganó nada, cambiar el generador ganó 3 veces). En la versión simple el efecto sería
menor: `drand48` ronda 19 ns por muestra contra 27 ns de `rand()`.

**Riesgo.** Un programa más y un gráfico más para una conclusión menos contundente.

## 9. xoshiro256\*\* con `jump()`

**Qué es.** Reemplazar `drand48` por el generador de `main`.

**Qué aporta.** Elimina el punto débil de `semilla + rank` (secuencias disjuntas garantizadas) y es
más rápido (en `main`: 9,4 ns por muestra en π).

**Riesgo.** Abre las preguntas más difíciles: `splitmix64`, rotaciones de bits, por qué el salto
equivale a 2¹²⁸ pasos. Declararlo como limitación conocida y mejora futura da casi el mismo crédito.

## 10. Referencia "muy eficiente" (Intel MKL, AMD AOCL o SIMD)

**Qué es.** Usar una librería de generadores vectorizados para tener una versión varias veces más rápida.

**Por qué no.** Hay que instalarla en la PC y en el contenedor del clúster (sin permisos de
administrador), escribir código C contra su interfaz y poder explicarlo. La ganancia que estimo (1
a 2 ns por muestra) no la medí. Queda mejor como mejora futura mencionada.

---

## Combinaciones razonables

- **Mínima (una tarde):** 1 + 2 + 3. No tocan el código C y mejoran las conclusiones.
- **Intermedia:** las anteriores + 4. Suma la comparación contra una librería.
- **Ambiciosa:** las anteriores + 5 (+ 7 si el perfil de 96 núcleos está disponible).

Cualquier mejora que cambie `benchmark.sh` conviene aplicarla **antes** de correr el benchmark
definitivo, para no medir dos veces.
