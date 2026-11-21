# LA GACETA NEGRA · BALAS Y ESTRELLAS

Agregador automático de titulares de TRUE CRIME, CRIME SCENE y LITERATURA NEGRA, para mostrar en la página Blogger de Balas y Estrellas.

## Estado de instalación

- Código y archivos de datos en este repositorio público.
- `.github/workflows/actualizar.yml`: busca noticias a las 08:17 y 20:17, hora de Madrid, y permite ejecutar **Run workflow** manualmente.
- `scripts/actualizar.py`: lee las fuentes RSS, clasifica y agrupa coincidencias conservadoras, conserva las noticias en `archivo/YYYY-MM.json` y actualiza `data/noticias.json`.
- `config/fuentes.json`: fuentes RSS activas. Para añadir Google Alerts, configurar entrega como RSS y añadir su URL.
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
