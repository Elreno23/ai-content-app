# ENGINE_RULES.md — Reglas del motor narrativo y de producción

> Documento consolidado de la arquitectura objetivo H3.
> Etiquetas: **[EXISTE]** implementado y verificado · **[OBJETIVO]** decisión aprobada,
> no implementado · **[PENDIENTE]** decisión abierta.
>
> H3 no ha sido ejecutado. Estas reglas definen cómo DEBERÁ comportarse el motor; no
> describen comportamiento actual salvo que se etiquete [EXISTE].

---

## 1. Regla: planificación antes que desarrollo

**[OBJETIVO]** La planificación global de la temporada (resumen de sus capítulos) se
realiza antes del desarrollo individual de los capítulos.

R1.1 — Los capítulos planificados son **entidades reales** con estado `planned`, no una
lista de texto paralela. La planificación y los capítulos son la misma entidad en dos
momentos del ciclo de vida (evita duplicidad y divergencia outline↔capítulos).

R1.2 — El límite de capítulos por temporada es **configurable por serie**. Propuesta
( marcada como propuesta, no decisión formal): valor por defecto 20. [PENDIENTE]

R1.3 — Las planificaciones **pueden modificarse conservando sus versiones anteriores**.
Mecanismo de versionado (tabla de versiones vs. snapshots) **[PENDIENTE]**.

R1.4 — Los capítulos **ya desarrollados no se modifican automáticamente** cuando cambia
una planificación. Un cambio de planificación afecta solo a capítulos en estado
`planned` (y posteriores). Si el usuario quiere realinear un capítulo desarrollado con
la nueva planificación, es una acción explícita suya, nunca un efecto colateral.

- Por qué: el trabajo narrativo ya desarrollado (y sus generaciones asociadas) es
  patrimonio persistido; una re-planificación no puede invalidarlo silenciosamente.
- Si se violara: borrados o reescrituras encubiertas de contenido aprobado, y
  trazabilidad rota entre lo planificado y lo producido.

## 2. Regla: ciclo de vida del capítulo con finalización separada

**[OBJETIVO]** Decisión aprobada: `separate`. El capítulo tiene **dos ciclos de
finalización independientes**:

1. **Finalización narrativa**: el capítulo tiene sus escenas y beats completos y sus
   acontecimientos validados. Es la condición para congelar el snapshot del mundo y
   actualizar el resumen rodante (ver `STATE_MODEL.md`).
2. **Finalización audiovisual**: los shots del capítulo tienen una generación aprobada.
   Es independiente de la narrativa: un capítulo puede estar narrativamente terminado y
   sin render, o tener renders en curso sin haberse cerrado narrativamente.

R2.1 — **La generación de imágenes no determina el estado narrativo del capítulo.**
Ni a la inversa: fallar un render no "des-cierra" la narrativa; cerrar la narrativa no
obliga a renderizar.

R2.2 — Estados de ciclo de vida propuestos (**propuesta, no decisión formal**
[PENDIENTE]):

```
planned → drafting → narrative_complete → visualizing → visual_complete
                                                    ↘ (re-apertura manual)
```

`drafting` y `visualizing` pueden solaparse en el tiempo para un mismo capítulo, dado
que los ciclos son independientes; la propuesta de arriba los ordena para legibilidad y
deberá refinarse a un modelo de dos ejes (eje narrativo + eje visual) en la
implementación. **[PENDIENTE]**

- Contraste con el estado actual [EXISTE]: hoy no hay estados de ciclo de vida.
  `ScriptService.generate_script` es una única **operación de aplicación** que, en la
  misma llamada HTTP, coordina la generación narrativa (LLM + persistencia) y el envío
  audiovisual a ComfyUI: eso es finalización narrativa y audiovisual acopladas a nivel
  de orquestación de servicio — exactamente lo que R2.1 prohíbe. (No se afirma nada
  sobre transacciones de base de datos compartidas; el acoplamiento es de coordinación,
  no de transacción.)

## 3. Regla: estructura narrativa

**[OBJETIVO]** Serie → Temporada → Capítulo → Escena → Beat → Shot.

R3.1 — La unidad narrativa mínima es el **Beat**; la unidad de encargo visual es el
**Shot**. Son unidades diferentes.

R3.2 — Un Beat puede tener **cero, uno o varios Shots**. Un beat sin shots es legítimo
(beat de transición o solo narrativo).

R3.3 — Un shot visualiza un beat concreto; su descripción visual se deriva del beat y
del estado del mundo, nunca se inventa de forma aislada.

## 4. Regla: generación y trazabilidad audiovisual

**[OBJETIVO]**

R4.1 — Cada Shot admite **múltiples generaciones** (intentos).

R4.2 — Cada intento es un **registro independiente** con `attempt_number` secuencial.
**No se sobrescriben generaciones anteriores**: un re-render es un intento nuevo.

R4.3 — Un intento registra como fuente de verdad técnica: **prompt exacto** enviado,
**workflow completo** (snapshot del payload), **parámetros** (seed, steps, cfg, modelo,
loras), **proveedor** y **resultados**. Distinguir dos conceptos que no deben
confundirse: el **`prompt_id`** es el **identificador de ejecución** que ComfyUI asigna
al job encolado (sirve para consultar `/history`, no para reproducir la imagen); el
**`seed`** es el **parámetro de generación** que afecta al resultado visual y se registra
en `params`. Reproducir un intento exige el workflow + parámetros (incluido `seed`), no
el `prompt_id`. Nota de continuidad [EXISTE]: el contrato actual
`ComfyUIBridge.submit_prompt(visual_metadata) -> prompt_id` ya produce el `prompt_id` y
el payload; H3.4 deberá persistirlos (hoy se pierden).

R4.4 — El intento con estado `approved` es el oficial del shot. Un shot se considera
resuelto cuando tiene exactamente un intento aprobado.

R4.5 — Salidas: **inicialmente imágenes**. La estructura reserva espacio para **vídeo**
(tipo de output `image | video`); el pipeline de vídeo **[PENDIENTE]** (no aprobado
como implementación, solo como capacidad futura).

R4.6 — Los archivos generados se persisten fuera del área `temp/` de ComfyUI con
referencia (ruta + tipo) en el registro del intento. [EXISTE] como problema conocido:
hoy los outputs viven en `temp/` y se pierden.

R4.7 — Los fallos de generación se registran en el intento (`failed` + detalle), nunca
como ausencia de registro. [EXISTE] el contrato de errores tipados
(`ComfyUIBridgeError → 502/503/504/500`) que el nuevo servicio reutilizará.

## 5. Regla: contexto del LLM

**[OBJETIVO]** (principio ya vigente [EXISTE] en su versión mínima)

R5.1 — El LLM **no accede** a la base de datos. Todo su conocimiento de la serie llega
por el contexto ensamblado por `ContextBuilder`.

R5.2 — El contexto se compone de datos estructurados (biblia, planificación, resumen
rodante, snapshot del último capítulo, fichas de los personajes del capítulo) y no de
la BD cruda ni de historiales sin acotar.

R5.3 — El contexto ensamblado se **registra** junto a la llamada que lo consumió, para
auditar qué "sabía" el modelo. [EXISTE] parcialmente: el prompt actual no se persiste.

R5.4 — El tamaño del contexto debe ser aproximadamente **constante** respecto al número
de capítulos (gracias al resumen rodante; ver `STATE_MODEL.md`).

## 6. Regla: validación (`propose_validate`)

**[OBJETIVO]**

R6.1 — Toda propuesta de acontecimiento del LLM pasa por validación backend antes de
persistirse (contrato: `ACTIONS_SCHEMA.json`).

R6.2 — La validación tiene dos niveles: **estructural** (schema: campos, tipos,
longitudes) y **semántica de dominio** (referencias a personajes existentes, coherencia
con el estado del mundo). El nivel semántico está parcialmente **[PENDIENTE]** de las
decisiones abiertas del schema (taxonomía de tipos, mecanismo de referencias).

R6.3 — El rechazo de propuestas usa el contrato de errores existente [EXISTE]
(`LLMResponseError` para no-conformidad estructural; errores de dominio del mismo árbol
`AppError` para semántica). La semántica de rechazo total vs. parcial del conjunto de
propuestas **[PENDIENTE]**.

## 7. Regla: independencia de la lógica de negocio

**[OBJETIVO]** (principio vigente [EXISTE])

R7.1 — Los seis servicios (`PlanningService`, `ChapterService`, `ContextBuilder`,
`WorldStateService`, `VisualService`, `GenerationService`) no importan FastAPI. Las
rutas son adaptadores finos.

R7.2 — Los proveedores externos (Ollama, ComfyUI) mantienen sus contratos actuales
[EXISTE]: `generate_script -> LlmResponse | raise LLMProviderError` y
`submit_prompt -> prompt_id | raise ComfyUIBridgeError`.

## 8. Índice de decisiones pendientes

| # | Decisión abierta | Bloquea |
|---|---|---|
| P1 | Taxonomía de tipos de acontecimiento (`ACTIONS_SCHEMA.json`) | `WorldStateService`, validación semántica |
| P2 | Mecanismo de referencia a personajes/ubicaciones (nombre vs. ID) | Schema de acciones, validación |
| P3 | Semántica de rechazo (total vs. parcial) | Validación de propuestas |
| P4 | Mecanismo de versionado de planificaciones | `PlanningService` |
| P5 | Límite por defecto de capítulos (propuesta: 20) | `PlanningService` |
| P6 | Modelo completo de estados de capítulo (dos ejes) | Ciclos de finalización |
| P7 | Estrategia de consistencia visual de personajes (LoRA/IP-Adapter/refs) | Campos visuales, H3.4 |
| P8 | Pipeline de vídeo | Outputs de `Generation` |
| P9 | ¿Puede el LLM proponer la creación de personajes/ubicaciones nuevos? | Validación de propuestas |
| P10 | Mecanismo de producción del WorldStateSnapshot y del Resumen rodante (derivación de código vs. LLM-asistido validado) y su forma de almacenamiento | `WorldStateService`, `ContextBuilder` |
