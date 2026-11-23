# ARCHITECTURE_DECISIONS.md — Razonamiento de las decisiones arquitectónicas (H3)

> Documento de razonamiento, no de especificación. Qué está decidido está en
> `SYSTEM_SPEC.md`, `STATE_MODEL.md`, `ENGINE_RULES.md`, `ACTIONS_SCHEMA.json` y
> `docs/H3.1_PLAN.md`; este documento explica el **porqué** de cada decisión con las
> alternativas que se consideraron.
>
> Etiquetas: **[APROBADA]** decisión formalizada · **[IMPLÍCITA]** decisión tomada en la
> implementación de H3.1 sin discusión explícita registrada · **[PENDIENTE]** abierta,
> con identificador P# si existe en `ENGINE_RULES.md`.
>
> Convención didáctica: cada decisión incluye motivo, alternativas consideradas (si
> están documentadas; si no, se declara expresamente) y consecuencias técnicas.

---

## 1. Arquitectura general

### 1.1 Tres planos separados [APROBADA]

**Decisión.** El sistema se organiza en tres planos: estructura narrativa
(Series → Seasons → Chapters → Escenas → Beats → Shots), estado del mundo (personajes,
ubicaciones, relaciones, acontecimientos, snapshots, resumen rodante) y producción
audiovisual (Shots → Generations → outputs). Detalle: `SYSTEM_SPEC.md` §3.

**Motivo.** Cada plano cambia a un ritmo distinto y tiene consumidores distintos: la
narrativa cambia con cada sesión de escritura, el mundo al cerrar cada capítulo, la
producción con cada intento de render. Mezclarlos obliga a reescribir el todo para
consultar cualquier parte — el `payload` JSONB del sistema actual es la prueba de ese
problema.

**Alternativas consideradas.** No hay alternativa documentada de "todo en un plano"
como opción deliberada: era simplemente el estado inicial accidental. La propuesta de
tres planos se aprobó sin variantes registradas.

**Consecuencias técnicas.** Más tablas y más repositorios, pero consultas estructuradas
posibles ("¿en qué capítulos aparece X?") sin leer JSONB; cada plano evoluciona con
migraciones independientes. El coste está asumido y documentado en H3.1_PLAN §4.

### 1.2 Servicios con lógica de negocio independiente de FastAPI [APROBADA]

**Decisión.** Seis servicios previstos (`PlanningService`, `ChapterService`,
`ContextBuilder`, `WorldStateService`, `VisualService`, `GenerationService`); las rutas
son adaptadores finos; `main.py` es el único punto que traduce excepciones a HTTP.

**Motivo.** Si la lógica viviera en las rutas, la capa de transporte dictaría la forma
del dominio; si viviera en los providers, el proveedor dictaría el negocio. La
separación permite probar servicios sin HTTP y cambiar el framework sin reescribir el
dominio. Este principio ya funciona [EXISTS] desde P0.1/P0.2: los providers lanzan
excepciones de dominio, nunca `HTTPException`.

**Consecuencias técnicas.** Los contratos entre servicios son llamadas Python normales;
el contrato de errores (`app/core/exceptions.py`) es el idioma común de todas las capas.

### 1.3 El LLM no accede a la base de datos [APROBADA]

**Decisión.** PostgreSQL es la fuente de verdad; el contexto del LLM lo ensambla código
(`ContextBuilder`), nunca consultas hechas por el modelo ni volcados crudos de la BD.
Detalle: `STATE_MODEL.md` §1 y `ENGINE_RULES.md` R5.

**Motivo.** Un LLM con acceso a datos no es determinista ni auditable; el contexto
ensamblado por código es reproducible, acotado en tamaño (resumen rodante) y registrable
(junto a cada llamada).

**Consecuencias técnicas.** Existe un contrato formal de lo que el LLM puede proponer
(`ACTIONS_SCHEMA.json`) y todo lo que entra al estado pasa por validación backend
(`propose_validate`).

---

## 2. Modelo de datos: Series, Seasons y Chapters

### 2.1 Jerarquía con contención [APROBADA]

**Decisión.** `Series` contiene `Seasons`; cada `Season` contiene `Chapters`. FK con
`ON DELETE CASCADE` en ambas direcciones. Numeración (`number`) es **por padre**:
`UNIQUE(series_id, number)` y `UNIQUE(season_id, number)`.

**Motivo.** Es una relación de contención: una temporada sin serie, o un capítulo sin
temporada, no tienen significado en el dominio. El CASCADE materializa esa dependencia
existencial: si desaparece el contenedor, desaparece el contenido. La numeración
relativa al padre (y no global) refleja cómo se habla de series en el mundo real
("capítulo 3 de la temporada 2"), y la constraint UNIQUE convierte esa convención en
garantía de BD en lugar de esperanza de código.

**Alternativas consideradas.** FK directa Series↔Chapters: descartada — sería
redundancia mantenida a mano con riesgo de incoherencia (un capítulo podría apuntar a
una serie distinta de la de su temporada). Registrada en `H3.1_PLAN.md` §2.

**Consecuencias técnicas.** Borrar una serie borra su árbol completo; los IDs son
SERIAL globales, la unicidad es compuesta. Consultas "capítulos de una serie" requieren
JOIN por temporada — aceptable, y la relación transitiva se consulta así en los repos.

### 2.2 La planificación son capítulos reales, no una estructura paralela [APROBADA]

**Decisión.** Planificar una temporada produce capítulos con `status='planned'` y una
`logline` cada uno. No existe una entidad "outline" separada. (`ENGINE_RULES.md` R1.1.)

**Motivo.** Outline y capítulos son la misma cosa en dos momentos del ciclo de vida.
Dos estructuras paralelas tendrían que sincronizarse a mano — fuente clásica de
divergencia ("¿este capítulo está planificado o escrito?" sin respuesta).

**Consecuencias técnicas.** `chapters.status` es la puerta de los ciclos de vida; el
resumen de planificación vive en `logline` (Text). La regla de modificación (los
desarrollados no se tocan al replanificar) es regla de servicio, no de esquema
(`ENGINE_RULES.md` R1.4).

### 2.3 La tabla `narrative` queda como histórico [APROBADA]

**Decisión.** Los 20 episodios existentes se conservan en `narrative` sin migrar; las
tablas nuevas parten de cero y ninguna FK cruza hacia ella.

**Motivo.** Los `payload` históricos son heterogéneos y su descomposición automática al
esquema nuevo puede perder matices; el coste de migrar superaba el valor. Arrancar
desde cero mantiene limpia la primera migración estructural.

**Consecuencias técnicas.** Dos "mundos" coexisten en la BD (`narrative` congelado +
`series/seasons/chapters` activos). Los tests afirman explícitamente que `narrative`
queda intacta, para que nadie la conecte ni la modifique por accidente.

### 2.4 Claves primarias SERIAL (globales) [IMPLÍCITA]

**Decisión registrada en implementación:** PKs `Integer` autoincrement, igual que
`narrative`.

**Nota de pendiente:** no hay discusión documentada Serial-vs-UUID. Con IDs compuestos
de unicidad por padre, los SERIAL son suficientes para el uso actual; si algún día hace
falta identificación global entre entornos (sincronización, exportación), será una
decisión a revisar. **[PENDIENTE, sin número asignado]** — documentada aquí por
honestidad, no resuelta.

---

## 3. Relaciones ORM

### 3.1 `relationship()` + `back_populates` en ambos extremos [APROBADA]

**Decisión.** `Series.seasons ↔ Season.series` y `Season.chapters ↔ Chapter.season`,
ambas con `back_populates`, sobre las FKs existentes.

**Motivo.** Las FK definen la relación **a nivel de base de datos**; `relationship()`
la define **a nivel de objetos**. Sin ORM-relation, navegar ("dame la serie de esta
temporada") exige consultas manuales repetidas en cada repositorio; con ella, el modelo
de objetos expone la relación y SQLAlchemy coordina ambas caras vía `back_populates`
(modificar un lado refleja el otro en memoria). Las FK no se sustituyen: siguen siendo
la única definición de integridad en la BD.

**Alternativas consideradas.** Ninguna documentada respecto a usar/no usar
`relationship()`; la elección de `back_populates` (frente a `backref`, que configura el
recíproco implícitamente) es coherente con la preferencia del proyecto por explicitud.

**Consecuencias técnicas.** Los modelos se conocen por nombre (strings resueltos por el
registry, con `TYPE_CHECKING` para los imports de tipos), lo que permite archivos
separados sin imports circulares.

### 3.2 `lazy="selectin"` por AsyncSession [APROBADA]

**Decisión.** Ambos extremos cargan con `lazy="selectin"` (`H3.1_PLAN.md` §2.1).

**Motivo.** Con `AsyncSession`, el lazy loading por defecto (`select`) falla en runtime
(`MissingGreenlet`) si se accede a una relación no cargada. `selectin` ejecuta la carga
secundaria como parte del SELECT principal (compatible con async), de modo que
`season.series` o `series.seasons` funcionan sin `selectinload()` manual en cada
consulta.

**Alternativas consideradas.** `lazy="raise"` + `selectinload()` explícito en cada
consulta: más estricto (cada acceso no cargado falla ruidosamente) pero más boilerplate
en H3.1; documentada como descartada por ahora y revisable en H3.2 si los perfiles de
consulta lo justifican.

**Consecuencias técnicas.** Cargar un `Series` trae sus seasons (y sus chapters vía
cadena selectin): puede traer más datos de lo necesario en listados grandes. Coste
aceptado para H3.1; si aparece, la mitigación es cambiar a `raise` + carga explícita.

### 3.3 `passive_deletes=True` en las colecciones padre [IMPLÍCITA — necesidad técnica, aplicada e informada en H3.1]

**Decisión.** `Series.seasons` y `Season.chapters` llevan `passive_deletes=True`.

**Motivo.** Sin ella, al borrar un padre SQLAlchemy intenta poner a `NULL` las FK de los
hijos cargados — imposible con FKs NOT NULL (`IntegrityError`). Con ella, el ORM no
toca a los hijos: el borrado lo ejecuta la BD vía `ON DELETE CASCADE`, que es la
política aprobada. Es el emparejamiento estándar CASCADE-atributo.

**Consecuencias técnicas.** Un `session.delete(series)` no carga los hijos para
borrarlos; la BD hace el trabajo en una sentencia. Sin esta pareja (CASCADE en BD +
passive_deletes en ORM), el borrado en contención simplemente no funcionaría.

### 3.4 Sin ORM-cascade (`all, delete-orphan`) [APROBADA]

**Decisión.** No se configura `cascade="all, delete-orphan"` en las relaciones.

**Motivo.** Duplicaría la política de borrado (ya en la BD) y crearía dos lugares donde
puede cambiar el comportamiento de borrado. La regla de contención vive en un solo
sitio: la BD.

**Consecuencias técnicas.** Quitar un hijo de una colección en memoria no lo elimina de
la BD (no hay delete-orphan); si algún flujo lo necesitara, será una decisión explícita
entonces.

---

## 4. Repositorios

### 4.1 Acceso a datos aislado en repositorios [APROBADA]

**Decisión.** Un repositorio por agregado (`SeriesRepository`, `SeasonRepository`,
`ChapterRepository`), cada uno async y construido con la `AsyncSession`.

**Motivo.** Los servicios no deberían saber construir consultas SQL ni gestionar
sesiones: el repositorio es el único traductor entre objetos de dominio y filas. Así
los tests de negocio pueden sustituir el repositorio por un falso, y el esquema puede
evolucionar tocando un solo lugar. Es la continuación natural del patrón ya existente
(`BaseNarrativeRepository`/`NarrativeRepository`).

**Alternativas consideradas.** Ninguna documentada para H3.1 (p. ej. DAO genérico o
Active Record). El patrón repositorio con interfaces viene heredado del código actual.

**Consecuencias técnicas.** Los repos devuelven **entidades ORM vivas** (con
`expire_on_commit=False` en las sesiones, usables tras commit). Operaciones estándar:
CRUD + `list_by_*` + `next_number` (max+1 por padre, mismo patrón que el histórico).

### 4.2 Interfaces abstractas por repositorio [APROBADA]

**Decisión.** Cada implementación hereda de un ABC (`BaseSeriesRepository`, etc.) que
declara el contrato.

**Motivo.** La interfaz es el contrato visible: documenta qué operaciones existen sin
leer la implementación, y permite en tests sustituir la implementación (fake/in-memory)
sin tocar los servicios. Es exactamente el patrón que P0.1 aplicó a los proveedores
(`BaseAIProvider`): contratos explícitos entre capas.

**Consecuencias técnicas.** Un methods-set fijo por agregado; añadir una operación es
un cambio de contrato visible en el diff.

---

## 5. Servicios y commits

### 5.1 El commit es del servicio, no del repositorio [APROBADA — decisión del usuario en H3.1]

**Decisión.** Los repositorios ejecutan `add + flush` y **nunca** `commit`. El commit es
responsabilidad del servicio que orquesta. En H3.1 (aún sin servicios), los tests
commitean vía la sesión del fixture. (`H3.1_PLAN.md` §8.)

**Motivo.** El commit define el **límite de la transacción de negocio**: "guardar una
serie y su temporada" es una unidad lógica que puede abarcar varios repositorios. Si
cada repositorio commitea por su cuenta, no existe transacción de negocio — dos
escrituras relacionadas pueden quedar la una aplicada y la otra no. El servicio conoce
la unidad de trabajo; el repositorio solo conoce su agregado.

**Alternativas consideradas.** Commit dentro del repositorio: es el patrón actual del
código histórico (`NarrativeRepository`) y se descartó para las tablas nuevas por lo
anterior. Ese patrón se conserva **intacto** en `narrative_repository.py` (histórico)
para no reescribir código congelado.

**Consecuencias técnicas.** Con repos sin commit, un test o servicio que olvide commitear
pierde los datos silenciosamente al cerrar la sesión — por eso los fixtures de test
commitean explícitamente. `flush()` sigue garantizando: obtención de PKs y detección
inmediata de violaciones de FK/UNIQUE/CHECK (por eso los tests de integridad esperan el
error en `create`, no en `commit`).

---

## 6. Transacciones y Unit of Work (deuda declarada)

**Estado actual [IMPLÍCITA].** H3.1 usa transacciones por llamada: el servicio/fixture
commitea al terminar su unidad. Suficiente mientras las unidades de negocio caben en
una sesión y un commit.

**Deuda declarada [PENDIENTE, registrada en `H3.1_PLAN.md` §10]:** cuando H3.2 introduzca
escrituras **multi-agregado** (p. ej., crear escenas + beats + actualizar capítulo en
una unidad), el commit manual en el servicio se volverá repetitivo y propenso a omisiones.
El patrón Unit of Work formalizó esa coordinación: una sola sesión, un solo commit al
final, rollback total ante cualquier fallo parcial.

**Motivo del aplazamiento.** Introducir UoW ahora, sin escrituras multi-agregado reales,
sería abstracción sin consumidor. La deuda se ejecutará cuando exista el segundo
escritor.

**Consecuencia si se ignora la deuda:** servicios con `commit()` repartidos a mano y
flujos a medio-aplicar ante fallos parciales — exactamente el problema que UoW evita.

---

## 7. Restricciones e integridad

### 7.1 Filosofía general [APROBADA]

La integridad estructural (lo que **siempre** debe cumplirse) vive en la BD; la
integridad de negocio (lo que depende de reglas cambiantes) vive en servicios. Criterio
aplicado tabla a tabla:

| Restricción | Nivel | Por qué ahí |
|---|---|---|
| PK `id` SERIAL | BD | Identidad de fila, siempre |
| FK + `ON DELETE CASCADE` (×2) | BD | Contención existencial, sin excepciones conocidas |
| `UNIQUE(series_id, number)` / `UNIQUE(season_id, number)` | BD | La numeración por padre es regla invariante |
| `CHECK(number >= 1)` (×2) | BD | Ordinales positivos, invariante |
| `CHECK(max_chapters_per_season IS NULL OR > 0)` | BD | Un límite 0/negativo no tiene sentido, sea cual sea el default |
| No exceder el límite de capítulos | **Servicio** (H3.5) | Regla de negocio evaluable solo con lógica (contar filas), no con un CHECK declarativo |
| Valores válidos de `status` | **Servicio** (H3.2) | El conjunto está abierto (P6); un CHECK enum lo congelaría |

**Motivo transversal.** Poner en la BD solo lo invariante evita migraciones para cada
ajuste de regla de negocio; poner en la BD lo invariante evita que un bug de código
corrompa el esquema lógico.

**Consecuencias técnicas.** Las violaciones de BD se manifiestan como
`IntegrityError` en `flush()` (no al final del commit); el contrato de errores del
dominio (`AppError`) las traducirá a errores de negocio cuando los servicios las
expongan — hoy los tests las verifican directamente.

### 7.2 El CHECK de `status` aplazado deliberadamente [APROBADA]

**Motivo.** `planned` es hoy el único valor aprobado, pero P6 definirá un modelo de dos
ejes (narrativo/visual). Un `CHECK (status IN ('planned'))` exigiría una migración por
cada estado nuevo. Cuando P6 cierre, añadir el CHECK es una migración aditiva barata.

---

## 8. Decisiones aplazadas (por qué)

| # | Decisión aplazada | Por qué se aplazó | Cuándo se decidirá |
|---|---|---|---|
| P4 | Mecanismo de versionado de planificaciones | Sin `PlanningService` no hay consumidor; esquema diseñado para que sea migración aditiva | H3.5 |
| P5 | Default de `max_chapters_per_season` | La columna es nullable: decidir el valor es cambio de código, no de migración. Evita fijar una cifra sin dueño de producto | H3.5 |
| P6 | Modelo de dos ejes de estados (narrativo/visual) | Requiere el diseño de `ChapterService`; el esquema usa String abierto a propósito | H3.2 |
| Índice `chapters.status` | Sin consultas por estado todavía (YAGNI) | Migración de H3.2 |
| Unit of Work | Sin escrituras multi-agregado reales (ver §6) | H3.2 |
| Serial-vs-UUID en PKs (§2.4) | Sin necesidad de identificación global hoy | Cuando exista sincronización/exportación |
| P10 | Mecanismo de producción de snapshot/resumen rodante | Pertenece a H3.3 (`WorldStateService`), no a la estructura | H3.3 |

**Motivo transversal del aplazamiento:** cada aplazamiento deja el esquema preparado
para que la decisión futura sea **aditiva** (columna nullable, CHECK nuevo, índice
nuevo) y no reestructurante. Ningún aplazamiento actual obligará a rehacer tablas.

---

## 9. Alternativas descartadas (índice con su razón)

| Alternativa | Descartada porque | Fuente |
|---|---|---|
| FK directa Series↔Chapters | Redundancia mantenida a mano; riesgo de incoherencia | `H3.1_PLAN.md` §2 |
| Outline de temporada como estructura paralela a capítulos | Divergencia garantizada entre lo planificado y lo escrito | `ENGINE_RULES.md` R1.1 |
| Migrar los 20 episodios al esquema nuevo | Coste > valor; payloads heterogéneos; decisión: histórico | `SYSTEM_SPEC.md` §4 |
| CHECK enum sobre `status` | Congelaría P6; cada estado nuevo = migración | §7.2 |
| Commit dentro de repositorios (para tablas nuevas) | Rompe la noción de transacción de negocio | §5.1 |
| ORM `cascade="all, delete-orphan"` | Duplicaría la política de borrado ya en BD | §3.4 |
| `lazy="raise"` + `selectinload()` explícito | Estricto pero boilerplate; revisable en H3.2 | §3.2 |
| Naming español (`Serie`/`serie`, ...) | Decisión del usuario: inglés, coherente con el código existente | `H3.1_PLAN.md` |
| Todos los modelos en un archivo | Decisión del usuario: un archivo por entidad | `H3.1_PLAN.md` |
| Índice de `status` desde el día uno | YAGNI: sin consultas por estado todavía | §8 |

**Nota de honestidad:** las alternativas listadas son las que quedaron registradas en
los documentos fuente. Cualquier decisión sin alternativa documentada se marca como tal
en su sección (p. ej., la elección de `back_populates` frente a `backref`, §3.1).

---

## 10. Información que falta (pendiente de documentar)

- **[PENDIENTE]** Justificación formal Serial-vs-UUID (solo registrada como implícita, §2.4).
- **[PENDIENTE]** Política de `update()` parcial con sentinelas: los repos actuales
  ignoran campos `None` en update, lo que impide poner un valor a NULL deliberadamente.
  No está documentada como decisión ni como deuda — hay que decidirla cuando un flujo lo
  necesite (H3.2+).
- **[PENDIENTE]** Estrategia de concurrencia para `next_number` (max+1): con usuarios
  simultáneos, dos lecturas del max pueden colisionar; la UNIQUE lo detecta como
  `IntegrityError`, pero la política de reintento no está definida. Registrada aquí como
  limitación conocida del patrón heredado.

---

## 11. Decisiones de H3.2 (ejecutadas)

### 11.1 Dos ejes de estado en `chapters` (resuelve P6) [APROBADA]

**Decisión.** `status` única sustituida por `narrative_status` y `visual_status`
(CHECK de BD por eje, índice sobre el narrativo). La puerta visual es
`narrative_approved` (aprobación humana del capítulo completo).

**Motivo.** La decisión `separate` exige ciclos independientes; un solo string no los
permite. La aprobación humana añade el estado terminal narrativo.

**Alternativas descartadas.** Status compuesto único (viola `separate`); re-apertura
manual (aplazada, P6-b).

**Consecuencias.** CHECKs en BD; H3.4 (visual) exigirá `narrative_approved`; los tests
H3.1 se adaptaron a los nuevos nombres.

### 11.2 Atomicidad sin clase Unit of Work (resuelve la deuda por decisión) [APROBADA]

**Decisión.** No se implementa UoW propio: la unidad de trabajo es la
`AsyncSession` — un `commit()` del servicio, `rollback()` ante excepción. Los
repositorios siguen sin commitear.

**Motivo.** Evitar sobre-arquitectura en el MVP; una sesión + commit explícito ya
garantiza atomicidad para el flujo actual (escenas+beats+estado en un commit).

**Alternativa descartada.** Clase UoW formal (se reconsiderará si aparecen
transacciones multi-servicio).

### 11.3 `passive_deletes="all"` (eleva la decisión implícita de H3.1) [APROBADA — hallazgo de H3.2]

**Decisión.** Todas las colecciones padre usan `passive_deletes="all"` (antes `True`).

**Motivo (evidencia empírica).** `passive_deletes=True` solo evita *cargar* la
colección al borrar el padre, pero el UoW **sigue anulando la FK de hijos residentes
en la sesión** (`UPDATE hijo SET fk=NULL`) — con FK NOT NULL eso es una
`NotNullViolationError` *intermitente según el orden interno del UoW*
(UPDATE-antes-de-DELETE vs. DELETE-primero). Reproducido con experimentos A/B en
temp (`repro_cascade*.py`): mismo código, resultado distinto según el proceso.
Con `"all"` el ORM nunca procesa hijos al borrar el padre: el CASCADE de BD lo hace
siempre, de forma determinista.

**Consecuencias.** Los objetos hijos residentes en la sesión quedan obsoletos tras el
borrado del padre (stale en identity map) — los tests verifican en sesión nueva.
Sin cambios de esquema.

### 11.4 Extensión del contrato del provider: `generate_chapter_structure` [APROBADA]

**Decisión.** Nuevo método abstracto en `BaseAIProvider`
(`prompt -> ChapterStructure`), implementado en `OllamaProvider` y stub en
`OpenIAProvider`. El pipeline de capítulos usa su propia constante de modelo
(`CHAPTER_MODEL_NAME = "qwen-local"`) y `options` (`think: false`, `num_ctx: 8192`,
`num_predict: 4096`) respaldadas por el experimento de evaluación (4/4 runs válidos).

**Motivo.** `generate_script -> LlmResponse` es el contrato del pipeline histórico;
el capítulo requiere otra estructura. El provider valida su dialecto y traduce
(regla P0.1); el servicio nunca ve JSON crudo.

**Hallazgo crítico documentado.** `qwen-local` es un modelo *thinking*: sin
`think: false`, el razonamiento consume todo el presupuesto de tokens y el contenido
llega vacío (verificado: 4096 tokens, `content=""`, `done_reason: length`).

**Alternativa descartada.** HTTP directo desde el servicio (viola capas).

### 11.5 Validación de capítulos con límites de producto [APROBADA]

**Decisión.** `CHAPTER_SCHEMA` (contrato `chapter_parser.py`): máximo 6 escenas,
máximo 5 beats por escena, numeración consecutiva obligatoria,
`extra="forbid"`, longitudes acotadas; una sola llamada LLM por capítulo;
aprobación a nivel de capítulo completo (revisión/regeneración parcial aplazadas).

**Motivo.** Límites fijados por el usuario tras el experimento; el validador es el
control de calidad sobre un modelo pequeño sin enforcement de schema.

### 11.6 Un único canal HTTP con Ollama + límites mínimos unificados [APROBADA]

**Decisión.** Método privado `_chat(model, prompt, options, think, timeout)` como único
punto de comunicación HTTP: traduce transporte/protocolo a excepciones tipadas y
retorna el contenido; la validación semántica queda en cada método público (su modelo
Pydantic). `think` y `timeout` configurables por llamada (None = no enviar el campo).
Los límites mínimos del capítulo (4-6 escenas, 2-5 beats) se fijaron en
`chapter_parser.py` (MIN_*) y el prompt importa esas mismas constantes.

**Motivo.** Elimina ~5 bloques duplicados de manejo HTTP entre `generate_script` y
`generate_chapter_structure`; los mínimos del prompt y del validador eran divergentes
(el parser aceptaba 1-3 escenas y 1 beat que el prompt prohibía) — una sola fuente de
verdad elimina el drift.

**Alternativa descartada.** Clase de cliente HTTP genérica separada (más capas para un
único proveedor; innecesaria hoy).

**Consecuencias.** `generate_script` se conserva y sigue en uso (verificado:
`script_service.py:28` ← `/generate-script`); su `MODEL_NAME` (gemma4:12b, cambio
manual del usuario) sigue pendiente de decisión — el modelo ya no está instalado.
`CHAPTER_SCHEMA.json` creado como documento-contrato (faltaba del plan H3.2).

### 11.7 Eliminación del pipeline histórico (generate_script + tabla narrative) [APROBADA — decisión del usuario]

**Decisión.** Eliminados: ruta `/generate-script`, `ScriptService`,
`OllamaProvider.generate_script`, `BaseAIProvider.generate_script` (la interfaz queda
con un único método), `models/narrative.py`, `narrative_repository.py`,
`base_repository.py`, `llm_parser.py`, `prueba_llm_parser.py`, `_chat()` (inline en
`generate_chapter_structure`), y la tabla `narrative` (migración `0004`).
`MODEL_NAME = "qwen-local"` único (los demás modelos olvidados por decisión del
usuario). Backup previo de los 20 episodios en JSON temporal antes del DROP.

**Motivo.** El pipeline histórico no tenía consumidores externos (cadena cerrada
verificada por grep) y su modelo ya ni estaba instalado; mantenerlo era código muerto
con dos contratos de provider. El usuario decide modelo único: `qwen-local`.

**Consecuencias.** La cadena de migraciones conserva la historia (baseline crea
`narrative`, `0004` la elimina — reproducible en entornos nuevos); los datos históricos
solo existen en el backup temporal. Los tests de handlers pasan de verificarse vía
ruta (eliminada) a invocación directa de los handlers. `BaseAIProvider` tiene un solo
método abstracto; `OpenIAProvider` stub coherente.

### 11.8 Lección: autogenerate de Alembic y metadata vacía [IMPLÍCITA]

Al eliminar el último import de `app.models` (estaba acoplado al import de
`Narrative` en `env.py`), el autogenerate detectó TODAS las tablas como eliminadas
(metadata vacío) y habría generado una migración destructiva total. Detectado antes de
aplicar (revisión obligatoria del autogenerate) y corregido: `env.py` importa
explícitamente `app.models` para poblar `Base.metadata`. La revisión manual del SQL
autogenerado es la red de seguridad que funcionó.
