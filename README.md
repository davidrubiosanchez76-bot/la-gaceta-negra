# LA GACETA NEGRA · BALAS Y ESTRELLAS

Agregador automático de titulares de TRUE CRIME, CRIME SCENE y LITERATURA NEGRA, para mostrar en la página Blogger de Balas y Estrellas.

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
