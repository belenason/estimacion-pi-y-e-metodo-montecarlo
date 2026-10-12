# Guía para terminar el informe

Acompaña a `informe.md`. No forma parte de la entrega.

## 1. Qué falta

Lo único que no pude completar es la descripción del clúster, porque no tengo su `sistema_cluster.txt`.

1. **Tabla 4 (sección 6.2), columna Clúster.** Seis celdas con `[COMPLETAR]`. En el clúster:
   ```bash
   lscpu | grep -E "Model name|Socket|Core|Thread|^CPU\(s\)|L1d|L2|L3"
   nproc
   cat /sys/fs/cgroup/cpu.max        # si corrió en contenedor
   gcc --version | head -1
   mpirun --version | head -1
   lsb_release -d
   ```
   Y anotar las opciones de `mpirun` con que se lanzó (`OPCIONES_MPI`).
2. **Copiar `sistema_cluster.txt`** a `resultados/cluster_2026-10-11/`. Ahí solo está el CSV que me pasaste.
3. **Bibliografía.** Agregar el material de la cátedra y verificar cada referencia: las cité de memoria.
4. **Verificar tres supuestos míos** (sección 2 de esta guía).

## 2. Supuestos que hice sobre el clúster

Revisalos; si alguno no es cierto hay que tocar una oración.

| Supuesto | Dónde aparece | Si no es cierto |
|---|---|---|
| Se ejecutó en un único nodo | 6.2, 8.7, 10.6 | Cambiar esas menciones |
| No se fijaron los procesos a núcleos (`--bind-to none` o el valor por defecto) | 6.5 punto 3, 8.4, 8.7, 10.5 | Si se usó `--bind-to core`, la explicación de 8.4 pierde fuerza y hay que reescribirla |
| El comando fue `PROCESOS="1 2 4 8 12 16 24 32 48" REPETICIONES=10 ./benchmark.sh cluster` | 6.5 | Corregir el comando |

**Dato clave para la sección 8.4:** la línea `Thread(s) per core` de `lscpu`.

- Si vale 2, el clúster tiene dos hilos por núcleo y la explicación de los dos modos de tiempo queda bien respaldada. Conviene agregarlo en 8.4.
- Si vale 1, dos procesos de la corrida no pudieron compartir un núcleo de esa forma. La causa más probable pasa a ser otra carga en el nodo, y hay que ajustar la redacción de 8.4 y 10.5.

## 3. Qué cambió en esta versión

- **Resultados reorganizados por tema** (error, tiempos, speedup, eficiencia, comparación) en lugar de por sistema.
- **Tablas y figuras numeradas de corrido**: 16 tablas y 10 figuras, todas citadas en el texto.
- **Análisis del error con 1200 ejecuciones distintas.** Las 500 corridas del clúster con P = 1, 2, 4, 8 y serial dan exactamente la misma estimación que en la PC (misma semilla), así que se cuentan una vez.
- **Secciones nuevas de análisis**: 8.2 (escalabilidad), 8.3 (costo fijo de sincronización), 8.4 (dos modos de tiempo), 8.5 (PC reinterpretada con el clúster).
- **Conclusiones reescritas**: 9 conclusiones más un párrafo sobre qué sistema conviene.
- **Mejoras futuras**: se agregó 10.5 (fijar procesos a núcleos), que sale directamente de los datos del clúster.
- **Carátula**: tomé institución y nombres del README.

## 4. Hallazgos del clúster que conviene saber defender

1. **Speedup casi ideal.** Con N = 10⁹: 46,9 para π y 38,7 para *e* con 48 procesos. Eficiencia ≥ 0,98 hasta 32 procesos.
2. **Un núcleo del clúster no es más rápido que uno de la notebook** (12,4 ns contra 12,1 ns por muestra de π). La ventaja del clúster es que sostiene todos los núcleos a la vez.
3. **Esto resuelve la duda de la PC**: el mismo código escala lineal en el clúster, así que la pérdida de la notebook es del hardware. Y los speedups mayores que P con N chico eran un artefacto de la notebook: en el clúster no aparecen.
4. **Costo fijo de sincronización**: unos 0,14 ms con 48 procesos, igual para π y *e*. Por eso con N = 10⁵ usar 48 procesos es más lento que usar 32.
5. **Dos modos de tiempo.** Muchas configuraciones tienen repeticiones "rápidas" (speedup ideal) y "lentas": 1,76 veces más para π, 1,25 veces para *e*, siempre el mismo factor. Por eso *e* con 48 procesos da eficiencia 0,81 en la mediana (6 de 10 lentas) y 0,99 en las mejores repeticiones. La explicación propuesta (procesos que comparten un núcleo físico) no está verificada: ver sección 2 de esta guía.
6. **Semillas.** Con `srand48(semilla + rank)` las secuencias de los procesos son copias desplazadas unas de otras, no secuencias independientes. Los datos no muestran una pérdida de precisión clara, pero en π con P ≥ 12 hay un exceso del 10 % que queda en la duda. Es el punto más débil y la razón de la mejora 10.1.

## 5. Puntos débiles que el informe declara

- **π con N = 10⁹ en la PC** mezcla dos estados de la máquina (repeticiones 8 a 10). Está explicado en 8.5. Si hay tiempo, repetirlo con la notebook enchufada:
  ```bash
  TAMANIOS="1000000000" PROCESOS="1 2 3 4 6 8" REPETICIONES=10 CORRIDA=pc_pi9 ./benchmark.sh pc
  ```
- **Las explicaciones de 8.4, 8.5 y 8.6 son hipótesis** coherentes con los datos, no mediciones directas. El texto usa "compatible con", "sugiere", "se atribuye". No las conviertas en afirmaciones al editar.
- **Los factores de aceleración de la sección 10** salen de un banco de pruebas aparte, no del proyecto. El informe lo aclara.

## 6. Figuras

Todas están en `resultados/comparacion/` y se regeneran con:

```bash
.venv/bin/python graficos.py resultados/pc_2026-10-11 resultados/cluster_2026-10-11
```

| Figura | Archivo | Sección |
|---|---|---|
| 1 | `intuicion.png` | 3.3 |
| 2 | `convergencia.png` | 7.1 |
| 3 | `error.png` | 7.1 |
| 4 | `error_procesos.png` | 7.2 |
| 5 | `tiempo_n_pc.png` | 7.3 |
| 6 | `tiempo_n_cluster.png` | 7.3 |
| 7 | `speedup_pc_n_grande.png` | 7.4 |
| 8 | `speedup_cluster.png` | 7.4 |
| 9 | `speedup.png` | 7.6 |
| 10 | `eficiencia.png` | 7.6 |

No se usan `tiempo_pc.png`, `tiempo_cluster.png`, `speedup_pc.png` ni `speedup_cluster_n_grande.png`. Sirven para la presentación oral.

Un detalle: el título dentro de `error_procesos.png` dice "El error no depende de la cantidad de procesos", más categórico que el texto de 7.2. Cambiarlo por un título neutro es una línea en `graficos.py`.

## 7. Cambios en `graficos.py` de esta versión

Sin commitear. Son tres:

1. **Ejecuciones repetidas entre sistemas.** Función nueva `ejecuciones_distintas`, usada en los gráficos de convergencia y de error. Sin esto, las 500 ejecuciones que PC y clúster comparten se cuentan dos veces.
2. **Figura extra `speedup_<sistema>_n_grande.png`**, igual a la de speedup pero solo con N ≥ 10⁷. Es la Figura 7. La original no cambia.
3. **Tres comentarios corregidos** que decían cosas que los datos contradicen (por ejemplo, que el lanzamiento de procesos entra en el tiempo medido).

Para deshacerlos: `git checkout -- graficos.py`. En ese caso la Figura 7 tendría que usar `speedup_pc.png` y las cifras de 7.1 cambiarían levemente.

## 8. Inconsistencias fuera del informe

El **README.md** del repositorio no coincide con el código ni con lo que se corrió, y el repositorio se evalúa:

- dice `-O3`; el Makefile usa `-O2`;
- dice P = 1, 2, 4, 8, 16 y cinco repeticiones; se corrió con otros valores y 10 repeticiones;
- dice `./benchmark.sh` y `python3 graficos.py` sin argumentos; ahora llevan argumentos;
- menciona el error relativo porcentual, que el programa no calcula.

## 9. Pasar a PDF o a Google Docs

- Las fórmulas están en LaTeX (`$…$`); se ven en la vista previa de VS Code y en GitHub.
- PDF: `pandoc informe.md -o informe.pdf --pdf-engine=xelatex -V lang=es -V geometry:margin=2.5cm`
- Word o Google Docs: `pandoc informe.md -o informe.docx` y subir el `.docx`.
- Las tablas anchas (8, 10 y 12) pueden necesitar página apaisada o letra más chica.

## 10. Revisión final

- [ ] No queda ningún `[COMPLETAR]`.
- [ ] Supuestos de la sección 2 de esta guía verificados.
- [ ] Todas las figuras se ven.
- [ ] Bibliografía verificada y material de la cátedra agregado.
- [ ] `resultados/cluster_2026-10-11/` y `resultados/comparacion/` subidos al repositorio, con `sistema_cluster.txt`.
- [ ] README corregido.
