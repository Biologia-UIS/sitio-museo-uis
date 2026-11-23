# Museo de Historia Natural UIS — sitio web

Sitio estático (HTML, CSS y un poco de JavaScript, sin dependencias) del Museo de Historia Natural de la Escuela de Biología, Universidad Industrial de Santander.

- `index.html`: todo el contenido (Historia, Sala de exhibición, Colecciones, Visitantes, Visítanos, Contacto).
- `estilos.css`: diseño.
- `interaccion.js`: animaciones al desplazarse, contadores y visor de fotos. Sin él la página se ve completa.
- `explorador.html` y `explorador.js`: explorador de las colecciones por municipio, con mapa de Santander.
- `img/`: imágenes ya reducidas para web y sin metadatos.
- `contenido/`: documentos fuente para alimentar la página. **No se sube a GitHub** (ver `.gitignore`).
- `herramientas/visitantes.py`: regenera la sección «Nuestros visitantes» desde la agenda.

Para verlo: abrir `index.html` en el navegador. Para publicarlo: GitHub Pages desde la rama `main`.

## Actualizar los visitantes

1. Descargar la agenda actualizada y guardarla como `contenido/visitas/agenda.xlsx`.
2. Ejecutar `python3 herramientas/visitantes.py` (necesita `pip install openpyxl`).

Solo cuenta las visitas con «x» o la hora de ingreso en la columna «Realizada».

## Actualizar el explorador de colecciones

`explorador.html` se genera con datos públicos de GBIF y los límites municipales del DANE (geoBoundaries):
ejecutar `python3 herramientas/colecciones.py` (no necesita instalar nada; tarda alrededor de un minuto).
No editar `explorador.html` a mano: se sobrescribe.
