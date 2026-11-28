# LA GACETA NEGRA · BALAS Y ESTRELLAS

Agregador automático de titulares de TRUE CRIME, CRIME SCENE y FICCIÓN NEGROCRIMINAL, para mostrar en la página Blogger de Balas y Estrellas.

## Estado de instalación

- Código y archivos de datos en este repositorio público.
- `.github/workflows/actualizar.yml`: busca noticias a las 08:17 y 20:17, hora de Madrid, y permite ejecutar **Run workflow** manualmente.
- `scripts/actualizar.py`: lee las fuentes RSS, clasifica y agrupa coincidencias conservadoras, conserva las noticias en `archivo/YYYY-MM.json` y actualiza `data/noticias.json`.
- `config/fuentes.json`: **16 fuentes RSS configuradas (15 activas)**, incluyendo noticias catalanas, españolas, europeas, estadounidenses y mundiales. Para añadir Google Alerts, configurar entrega como RSS y añadir su URL.
- `config/expedientes.json`: expedientes en seguimiento (Isak Andic y Lindsay Clancy). Las noticias se asignan por coincidencia con alias configurados.
- `archivo/indice.json`: meses y filtros disponibles para hemeroteca.
- `tests/test_actualizar.py`: pruebas básicas de lector y agrupación.

## Primera ejecución

Ve a [GitHub Actions](https://github.com/davidrubiosanchez76-bot/la-gaceta-negra/actions/workflows/actualizar.yml), selecciona **Actualizar La Gaceta Negra** y pulsa **Run workflow** (rama main).

Abre el registro de ejecución: debe finalizar en verde y mostrar en el paso «Recopilar y clasificar noticias» cuántas fuentes han respondido. Comprueba [data/noticias.json](https://github.com/davidrubiosanchez76-bot/la-gaceta-negra/blob/main/data/noticias.json): tendrá titulares cuando los RSS devuelvan artículos relevantes recientes. Al principio es normal encontrar categorías vacías.

## Blogger

La página ya pegada en Blogger espera leer estos tres archivos:
- `https://cdn.jsdelivr.net/gh/davidrubiosanchez76-bot/la-gaceta-negra@main/data/noticias.json`
- `https://cdn.jsdelivr.net/gh/davidrubiosanchez76-bot/la-gaceta-negra@main/archivo/indice.json`
- `https://cdn.jsdelivr.net/gh/davidrubiosanchez76-bot/la-gaceta-negra@main/config/expedientes.json`

**Importante:** jsDelivr mantiene caché de URLs referidas a la rama durante un período, por lo que Blogger puede tardar horas en mostrar nuevos titulares incluso después de un trabajo correcto. El lector carga la misma URL sin pedir cambios manuales.

## Criterios de publicación

Ficha: titular, medio original, fecha, categoría, enlace; no se reproduce el cuerpo de la noticia. El archivo conserva la clasificación por temas, la posible relación con expedientes y todas las fuentes asociadas a un mismo acontecimiento.

Agrupación por similitud de titular, misma categoría, proximidad temporal y ciertas salvaguardas geográficas. Es una aproximación conservadora, no una garantía de deduplicación perfecta.

Las noticias del RSS se filtran por actualidad (últimos 15 días), los JSON de portada contienen los últimos 60 días y los archivos históricos se conservan por mes.

## Mantenimiento

- Fuentes: editar `config/fuentes.json`.
- Seguimientos: editar `config/expedientes.json`.
- Ejecuciones y errores: pestaña **Actions**.
- Si una fuente deja de responder, el error se registra en el trabajo, sin eliminar noticias antiguas.
- **Google Alerts aún no se ha conectado:** hace falta incorporar las URLs RSS concretas.

El prototipo es una prueba técnica: conviene revisar la relevancia y los posibles falsos positivos durante las primeras ejecuciones.

## Cobertura geográfica (21/11/2026)

La Gaceta incorpora el campo `region`: ESPAÑA, EUROPA, ESTADOS UNIDOS y MUNDO. El país del periódico **no equivale** al lugar del acontecimiento: cuando el titular no permite determinarlo y el feed no está circunscrito a una zona, la noticia pasa a MUNDO para evitar clasificaciones arbitrarias. Los sucesos de cualquier lugar de España se agrupan en ESPAÑA, sin filtro específico para Cataluña.

La nueva versión del HTML de Blogger incorpora el selector geográfico y abre la Hemeroteca con los resultados del último mes, sin exigir pulsar «Buscar». El HTML ya publicado en Blogger debe sustituirse por esa versión, porque modificar los datos en GitHub no altera la interfaz pegada en Blogger.

Los expedientes de Andic y Clancy pueden seguir sin noticias hasta que alguna fuente publique novedades que identifiquen los nombres/alias; no se ha inventado un histórico retrospectivo.


## Titulares de La Gaceta (21/11/2026)

La página lee `titular`, que puede ser una **reformulación editorial conservadora** de `titular_original` cuando existe una regla suficientemente precisa. Se conserva `titular_original` para la deduplicación, clasificación, regiones y seguimiento. El campo `metodo_titular` indica `regla` u `original`.

**Criterio:** nunca inventar delito, modo de comisión, lugar, parentesco, fechas ni identidad; conservar expresiones de presunción/acusación cuando no exista condena. Si una reformulación segura no es posible con las reglas actuales, se mantiene el titular original en lugar de inventar detalles o mostrar un titular genérico.

**Alcance inicial comprobado:** 13 de las 70 noticias existentes reescritas mediante reglas; el resto permanecen con su título original. La reformulación general de noticias muy distintas o su traducción flexible requerirá integrar un modelo de lenguaje externo; no se han activado servicios de pago ni se han incorporado claves de API.

## Alcance geográfico y fuentes (noviembre 2026)

La Gaceta no publica titulares de RSS en catalán y elimina la categoría geográfica CATALUÑA. El RSS de 3CatInfo y el canal exclusivamente local «La Vanguardia — Barcelona» se han retirado del sistema y del histórico. Las noticias que sucedan en Cataluña pero procedan de fuentes generales pueden aparecer bajo ESPAÑA. La selección queda en ESPAÑA, EUROPA, ESTADOS UNIDOS y MUNDO.

## Expedientes temáticos (21/11/2026)

Ahora se admiten dos tipos de expediente en `config/expedientes.json`:

- `tipo` ausente: **expediente de caso**, asociado a nombres/alias concretos (Isak Andic, Lindsay Clancy, Luigi Mangione).
- `tipo: "tematico"`: **expediente de fenómeno criminal**, asociado a un detector específico y conservador. El primero es `extremismo-nihilista-violento` (`detector: "nve"`).

El expediente **EXTREMISMO VIOLENTO NIHILISTA** incorpora una hemeroteca inicial de 13 noticias verificadas de 2025-2026, con fuentes originales, seleccionadas una a una. También sigue nuevas noticias en los RSS generales y en un RSS oficial del Departamento de Justicia de EE. UU. limitado a este expediente (`solo_expediente`). El detector distingue las expresiones de extremismo nihilista y referencias relevantes a 764 o The Com de las coincidencias accidentales con “764”, “nihilismo” o “terrorismo” por separado. No asigna por sí mismo una calificación penal de terrorismo.

La Hemeroteca general sigue siendo independiente; el archivo aparece en **Expedientes → True Crime → EXTREMISMO VIOLENTO NIHILISTA**. El HTML vigente lee la lista de expedientes desde GitHub, por lo que no requiere añadir manualmente una nueva tarjeta. No se guardan ni reproducen imágenes o textos de explotación ni otro material gráfico sensible.

Los titulares históricos se conservarán durante las siguientes actualizaciones al tener `origen: "hemeroteca_manual"`. Cualquier información de carácter judicial distingue la acusación de la condena. El concepto académico y policial de extremismo nihilista violento es debatido y no todos los delitos relacionados constituyen jurídicamente terrorismo.

## Enlaces de lectura pública (noviembre de 2026)

Cuando varias fuentes cubren el mismo acontecimiento, el primer enlace favorece a medios habitualmente abiertos. Se conservan las demás referencias en «Más fuentes»; si sólo existe una fuente de suscripción, se mantiene. La regla utiliza el dominio del medio y no garantiza que cada artículo individual sea gratuito. Puede señalarse el acceso contrastado de una fuente con `acceso: "abierto"` o `acceso: "restringido"`. La política editable está en `config/acceso_medios.json`. Se guarda `medio_titular` para preservar la procedencia del titular original al ordenar enlaces.

## Ampliación de fuentes españolas y especializados (23/11/2026)

Se añaden **OKDIARIO, THE OBJECTIVE, El Debate, ABC, El Confidencial y EL MUNDO** para ampliar la cobertura de sucesos y tribunales. También se consultan **Solo Novela Negra, Inmisericordes, Interrobang y Zenda (etiqueta novela negra)**, utilizando sus RSS públicos.

Los cuatro medios literarios llevan `solo_noticias_genero: true`: únicamente se incorporan titulares con indicios claros de actualidad (premios, festivales, presentaciones, convocatorias, reediciones, novedades, etc.). No se importa indiscriminadamente su archivo de reseñas, artículos o listas. El filtro es deliberadamente conservador, y algunas noticias pueden quedar fuera si su titular no contiene esas señales.

La disponibilidad del RSS se comprueba en GitHub Actions: los canales inaccesibles se registran como aviso sin bloquear el resto del agregado. Los enlaces de medios con modelos de suscripción mantienen la preferencia de lectura pública configurada en `config/acceso_medios.json`.

## Revisión editorial (27/11/2026)

- Se rechazan titulares de debate político, enfrentamiento partidista, campaña o declaraciones que no identifiquen un hecho criminal concreto. La regla se aplica de modo neutral a todas las fuentes y conserva noticias sobre delitos, causas judiciales y corrupción incluso cuando afectan a políticos.
- Se incorpora el registro de exclusiones editoriales para evitar que vuelvan a publicarse titulares concretos descartados. Los artículos quedan fuera de Portada y Hemeroteca al siguiente refresco de GitHub Actions.
- Las etiquetas temáticas se calculan para todos los artículos (homicidios, agresiones sexuales, estafas, narcotráfico, ciberdelincuencia, juicios, investigaciones, etc.), con una etiqueta genérica cuando el titular no permite una subclasificación segura. Blogger ya muestra `temas` y no necesita modificar su HTML.
- Para Law & Crime, se han revisado manualmente quince traducciones defectuosas; los titulares nuevos largos o enrevesados no pasan automáticamente si no tienen revisión editorial. Así se prioriza la fidelidad factual frente a la publicación a cualquier precio.

## Ampliación editorial y geográfica (28/11/2026)

Se han añadido **11 canales RSS** a `config/fuentes.json`: FBI, FTC (fraudes al consumidor), NIST (ciencia forense), Europol, Mystery Tribune, Valencia Negra, The Moscow Times (inglés), Meduza (inglés), Deutsche Welle (inglés), ANSA (inglés) e Infobae. Sus enlaces de sindicación se identificaron en páginas oficiales o se reconocieron como contenidos RSS/XML en consultas previas. GitHub Actions comprueba su funcionamiento real y deja constancia de los errores sin bloquear la hemeroteca.

`config/fuentes_candidatas.json` contiene medios que **no se han activado** por ausencia de un feed comprobado, dificultad lingüística o posible muro de pago. Se han registrado candidatas para Francia, China, Reino Unido, Alemania, Italia, España y los dos circuitos especializados. No se ha inventado ninguna URL RSS ni activado una fuente por el mero hecho de aparecer en una lista.

**Criterios editoriales aplicados:**
- Las editoriales se consultan de forma plural para contrastar datos, pero no se importan sus catálogos como noticias ni se da preferencia a Penguin u otro grupo.
- En literatura se priorizan noticias de premios, novedades periodísticas, adaptaciones y festivales; se excluyen las reseñas rutinarias de los feeds especializados.
- Se amplía el rastreo de estafas, timos y suplantaciones, así como criminología y especialidades forenses. NIST permite verificar el contexto forense también en el resumen de un RSS monográfico y FTC filtra por fraude.
- Se omiten **nuevas incorporaciones automáticas** de dominios clasificados como de suscripción frecuente. La clasificación por dominio es orientativa; no garantiza que cada artículo de los demás medios sea gratuito.
- El registro de exclusiones persiste para que once falsos positivos ya identificados no reaparezcan. La siguiente ejecución de GitHub Actions materializa las exclusiones en la hemeroteca; los casos históricos verificados se conservan.
- Se almacena `pais` cuando el título indica un país de los hechos de modo inequívoco (o el feed es oficial de ámbito nacional), y la lista de países por mes en `archivo/indice.json`. Blogger continúa usando las regiones anteriores, por compatibilidad. Para mostrar un filtro por país en la página hay que modificar su HTML.

Las fuentes institucionales se interpretan como información sobre investigaciones y acusaciones, no como determinaciones de culpabilidad. No se asignan puntuaciones automáticas de veracidad según el perfil ideológico de cada periódico. La prioridad editorial es el hecho delictivo y la pluralidad de fuentes.

## Equilibrio editorial de portada y revisión forense (28/11/2026)

Se detectaron falsos positivos por la subcadena "timo" dentro de "último", "íntimo", "céntimos" y similares. Se corrigió el detector de texto completo y las etiquetas para exigir la palabra completa. Se añadieron exclusiones persistentes de nueve titulares inapropiados (opiniones y episodios ajenos a sucesos criminales, anécdotas políticas, un accidente y una nota religiosa).

Las noticias archivadas se mantienen completas, pero **la portada** muestra como máximo tres entradas por medio y día. Sus primeras veinte tarjetas se diversifican con un máximo preferente de tres por medio, usando acontecimientos recientes de otras fuentes. Ninguna cabecera es excluida por su orientación ideológica; la representación responde exclusivamente a evitar duplicación editorial y acumulación de noticias en un único RSS. El HTML de Blogger deberá respetar el orden recibido desde data/noticias.json para conservar la mezcla; si vuelve a ordenar por fecha, seguirá vigente el máximo por medio y día.

CASO EPSTEIN: añadido el análisis forense presentado el 16/11/2026 (Michael Freeman, Anders Eriksson e Itiel Dror) con fuentes independientes CNN/BBC/CBS, describiendo tanto sus dudas sobre el suicidio como el dictamen contrario del Médico Forense de Nueva York. No se atribuye como hecho probado un homicidio.

## Corrección efectiva de la infrarrepresentación — 28/11/2026

La auditoría del ciclo 46130886672 confirmó un **problema de cobertura real**: CrimeReads, Revista Calibre .38, Mystery Tribune, Valencia Negra y NIST devolvían cero noticias pertinentes; la combinación de RSS limitados a los últimos 10-40 artículos, ventana de 15 días y palabras clave en el título impedía aprovechar noticias especializadas.

Desde esta revisión las fuentes de categoría **CRIME SCENE** o **FICCIÓN NEGROCRIMINAL** disponen de **90 días** para recuperar noticias de sus canales; True Crime general sigue con 15 días. Se mantienen las salvaguardas: excluir reseñas rutinarias, opiniones y publicidad; exigir pertinencia forense en fuentes generalistas; no incorporar catálogos editoriales.

Se han sembrado **12 fichas de actualidad respaldadas por noticias abiertas de 2026**, con fuente directa y fecha documental: siete Crime Scene (ADN y genealogía, prueba informática, criminología) y cinco Ficción negrocriminal (premios literarios, festival Vallekas Negra, adaptación audiovisual), evitando notas promocionales comerciales salvo documentación primaria de un estreno audiovisual.

El sembrado histórico y las nuevas reglas se reflejarán en Blogger tras la próxima ejecución completa de GitHub Actions, que reconstruye `data/noticias.json` y `archivo/indice.json`. La publicación de nuevas noticias automáticas depende de que los RSS entreguen títulos pertinentes, no de cuotas impuestas.
