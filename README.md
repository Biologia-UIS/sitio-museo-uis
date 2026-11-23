# Museo de Historia Natural UIS — sitio web

Sitio estático (HTML, CSS y un poco de JavaScript, sin dependencias) del Museo de Historia Natural de la Escuela de Biología, Universidad Industrial de Santander.

- `index.html`: todo el contenido (Historia, Sala de exhibición, Colecciones, Visitantes, Visítanos, Contacto).
- `estilos.css`: diseño.
- `interaccion.js`: animaciones al desplazarse, contadores y visor de fotos. Sin él la página se ve completa.
- `img/`: imágenes ya reducidas para web y sin metadatos.
- `contenido/`: documentos fuente para alimentar la página. **No se sube a GitHub** (ver `.gitignore`).
- `herramientas/visitantes.py`: regenera la sección «Nuestros visitantes» desde la agenda.

Para verlo: abrir `index.html` en el navegador. Para publicarlo: GitHub Pages desde la rama `main`.

## Actualizar los visitantes

1. Descargar la agenda actualizada y guardarla como `contenido/visitas/agenda.xlsx`.
2. Ejecutar `python3 herramientas/visitantes.py` (necesita `pip install openpyxl`).

Solo cuenta las visitas con «x» o la hora de ingreso en la columna «Realizada».
