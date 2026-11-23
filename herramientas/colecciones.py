"""Genera explorador.html («Explora las colecciones») con datos públicos de GBIF.

Uso:  python3 herramientas/colecciones.py
Sin dependencias externas. Cuenta los especímenes de las colecciones del museo publicados
en GBIF cuyas coordenadas caen en cada municipio de Santander (división GADM de GBIF) y
dibuja el mapa con los límites municipales del DANE publicados por geoBoundaries (CC BY 4.0).
"""
import json
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
import urllib.request
from html import escape
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
API = "https://api.gbif.org/v1/"
SANTANDER = "COL.28_2"  # GADM de Santander en GBIF; se confirma abajo por nombre.
LIMITES = "https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/COL/ADM2/geoBoundaries-COL-ADM2_simplified.geojson"
# Nombre en GBIF (GADM) -> nombre en el DANE, cuando no coinciden.
ALIAS = {"jordan": "jordan sube"}
# GADM llama «San Andrés de Cuerquia» (un municipio de Antioquia) al San Andrés de Santander y escribe «Lebríja».
CORRECCIONES = {"San Andrés de Cuerquia": "San Andrés", "Lebríja": "Lebrija"}

COLECCIONES = {
    "34ca7b9c-6a2f-465e-9cac-7d71c792c670": "Aves",
    "83964202-07d9-4a27-8391-975144bcc1da": "Mamíferos",
    "95f8be9e-48a3-490b-8bd8-b03cc775b14e": "Microorganismos (Cepario)",
    "c0717c48-e182-4bcf-b722-71c9af936058": "Hidrobiología",
    "c1316d40-133e-485a-aa5b-e62091ebfdf5": "Anfibios",
    "c816ec3b-ed12-4891-b304-d4e626e43cb3": "Reptiles",
    "cc5e1e3d-0850-4cde-a282-656657752e13": "Plantas (Herbario)",
    "eaad657f-7bda-4705-a181-053d9e38033f": "Peces",
}


def pedir(ruta, **params):
    """GET a la API de GBIF; datasetKey va repetido para cubrir todas las colecciones."""
    url = API + ruta + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    for intento in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except OSError:
            if intento == 2:
                raise
            time.sleep(3)


def leer_url(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def norm(nombre):
    """Minúsculas y sin tildes, para comparar nombres de municipios entre fuentes."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", nombre.lower()) if unicodedata.category(c) != "Mn")
    return sin_tildes.replace(".", "").strip()


assert norm("Jordán ") == "jordan" and norm("San Andrés") == "san andres"


def anillos(geom):
    return geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]


def en_santander(geom):
    """El centro aproximado cae en el recuadro de Santander (separa municipios homónimos de otros departamentos)."""
    puntos = [p for poligono in anillos(geom) for p in poligono[0]]
    lon = sum(p[0] for p in puntos) / len(puntos)
    lat = sum(p[1] for p in puntos) / len(puntos)
    return -74.6 < lon < -72.4 and 5.6 < lat < 8.2


def aligerar(geom):
    """Coordenadas a 3 decimales (~100 m) sin puntos repetidos: basta para un mapa del departamento."""
    def anillo(a):
        out = []
        for x, y in a:
            p = [round(x, 3), round(y, 3)]
            if not out or out[-1] != p:
                out.append(p)
        return out
    return {"type": "MultiPolygon", "coordinates": [[anillo(a) for a in pol] for pol in anillos(geom)]}


def limites(municipios_gbif):
    """GeoJSON de los municipios de Santander, con el gid de GBIF de cada uno."""
    por_nombre = {}
    for f in leer_url(LIMITES)["features"]:
        if en_santander(f["geometry"]):
            por_nombre.setdefault(norm(f["properties"]["shapeName"]), []).append(f)
    salida = []
    for gid, nombre in municipios_gbif.items():
        clave = ALIAS.get(norm(nombre), norm(nombre))
        encontrados = por_nombre.get(clave, [])
        assert len(encontrados) == 1, f"Límite de {nombre}: {len(encontrados)} coincidencias en el DANE"
        f = encontrados[0]
        salida.append({"type": "Feature", "geometry": aligerar(f["geometry"]),
                       "properties": {"gid": gid, "nombre": nombre}})
    return salida


def facetas(respuesta):
    return {f["field"]: f["counts"] for f in respuesta["facets"]}


def miles(n):
    return f"{n:,}".replace(",", ".")


assert miles(30145) == "30.145" and miles(7) == "7"


def panel(gid, nombre, total, por_coleccion, especies, visible):
    tope = por_coleccion[0]["count"]
    barras = "\n".join(
        f'        <li><span>{escape(COLECCIONES[c["name"]])}</span><span class="valor" style="--v:{c["count"] / tope:.3f}"></span><span>{miles(c["count"])}</span></li>'
        for c in por_coleccion)
    lista = "\n".join(
        f"        <li><i>{escape(cientifico)}</i> <span>({miles(n)})</span></li>"
        for cientifico, n in especies)
    enlace = "https://www.gbif.org/occurrence/search?" + urllib.parse.urlencode(
        {"gadm_gid": gid, "dataset_key": list(COLECCIONES)}, doseq=True)
    return f"""    <div data-municipio="{escape(gid)}"{'' if visible else ' hidden'}>
      <p class="explorador-total"><b>{miles(total)}</b> especímenes de {escape(nombre)} se conservan en el museo.</p>
      <h3>Por colección</h3>
      <ul class="grafica-tipos">
{barras}
      </ul>
      <h3>Las especies más registradas</h3>
      <ol class="explorador-especies">
{lista}
      </ol>
      <p><a href="{escape(enlace)}" target="_blank" rel="noopener">Ver todos los registros de {escape(nombre)} en GBIF</a></p>
    </div>"""


def html():
    datasets = {"datasetKey": list(COLECCIONES)}
    municipios = {d["id"]: d["name"] for d in pedir(f"geocode/gadm/{SANTANDER}/subdivisions")}
    assert "Bucaramanga" in municipios.values(), "El código GADM de Santander cambió"
    municipios = {gid: CORRECCIONES.get(n, n) for gid, n in municipios.items()}  # los de GBIF traen bien las tildes
    mapa = limites(municipios)

    conteos = facetas(pedir("occurrence/search", gadmGid=SANTANDER, limit=0,
                            facet="gadmLevel2Gid", facetLimit=200, **datasets))["GADM_LEVEL_2_GID"]
    conteos = [c for c in conteos if c["name"] in municipios]
    total = sum(c["count"] for c in conteos)
    ordenados = sorted(conteos, key=lambda c: norm(municipios[c["name"]]))
    mayor = max(conteos, key=lambda c: c["count"])["name"]

    def un_panel(c):
        gid = c["name"]
        f = facetas(pedir("occurrence/search", gadmGid=gid, limit=0, facet=["datasetKey", "speciesKey"],
                          facetLimit=5, **datasets))
        especies = [(pedir(f"species/{s['name']}")["canonicalName"], s["count"]) for s in f.get("SPECIES_KEY", [])]
        print(municipios[gid], file=sys.stderr)
        return panel(gid, municipios[gid], c["count"], f["DATASET_KEY"], especies, gid == mayor)

    with ThreadPoolExecutor(8) as hilos:  # GBIF responde lento; 8 consultas a la vez sin abusar del servicio
        paneles = list(hilos.map(un_panel, ordenados))
    n_por_gid = {c["name"]: c["count"] for c in conteos}
    for f in mapa:
        f["properties"]["n"] = n_por_gid.get(f["properties"]["gid"], 0)
    # </ no puede aparecer dentro de <script>; los nombres no lo traen, pero se escapa por si acaso.
    geojson = json.dumps({"type": "FeatureCollection", "features": mapa}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    opciones = "\n".join(
        f'      <option value="{escape(c["name"])}"{" selected" if c["name"] == mayor else ""}>{escape(municipios[c["name"]])} ({miles(c["count"])})</option>'
        for c in ordenados)
    paneles = "\n".join(paneles)
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Explora las colecciones · Museo de Historia Natural UIS</title>
  <meta name="description" content="Especímenes de las colecciones del Museo de Historia Natural UIS por municipio de Santander.">
  <link rel="icon" href="img/icono-museo.png">
  <link href="https://fonts.googleapis.com/css2?family=Anton&family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" integrity="sha512-h9FcoyWjHcOcmEVkxOfTLnmZFWIH0iZhZT1H2TbOq55xssQGEJHEaIm+PgoUaZbRvQTNTluNOEfb1ZRy6D3BOw==" crossorigin="anonymous">
  <link rel="stylesheet" href="estilos.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js" integrity="sha512-puJW3E/qXDqYp9IfhAI54BJEaWIfloJ7JWs7OeD5i6ruC9JZL1gERT1wjtwXFlh7CjE7ZJ+/vcRZRkIYIb6p4g==" crossorigin="anonymous" defer></script>
  <script src="interaccion.js" defer></script>
  <script src="explorador.js" defer></script>
</head>
<body>
<!-- Archivo generado por herramientas/colecciones.py: no editar a mano. -->
<header class="cabecera">
  <a class="marca" href="index.html"><img src="img/logo-museo.png" alt="Museo de Historia Natural UIS, volver al inicio" width="141" height="48"></a>
  <nav aria-label="Secciones"><a href="index.html">Volver al inicio</a></nav>
</header>
<main>
<section id="explorador" class="seccion">
  <h2>Explora las colecciones</h2>
  <p class="intro">¿Qué se ha encontrado en tu municipio? Las colecciones del museo guardan {miles(total)} especímenes colectados en {len(conteos)} municipios de Santander. Elige el tuyo.</p>
  <label class="explorador-elegir">Municipio
    <select>
{opciones}
    </select>
  </label>
  <div class="explorador-cuerpo">
    <div id="mapa-santander" class="explorador-mapa" data-gbif="{escape(urllib.parse.urlencode(datasets, doseq=True))}" role="img" aria-label="Mapa de Santander: toca un municipio para elegirlo. Los puntos naranjas son los lugares donde se colectaron los especímenes."></div>
    <div class="explorador-resultado" aria-live="polite">
{paneles}
    </div>
  </div>
  <script type="application/json" id="municipios-geo">{geojson}</script>
  <p class="nota">Fuente: registros de las colecciones del museo publicados en <a href="https://www.gbif.org" target="_blank" rel="noopener">GBIF</a>. Solo se cuentan los especímenes con coordenadas. Entre paréntesis, el número de especímenes de cada especie. Límites municipales: DANE, vía <a href="https://www.geoboundaries.org" target="_blank" rel="noopener">geoBoundaries</a> (CC BY 4.0).</p>
</section>
</main>
</body>
</html>
"""


def main():
    nuevo = html()  # se calcula todo antes de escribir: si GBIF falla, la página anterior queda intacta
    (RAIZ / "explorador.html").write_text(nuevo, encoding="utf-8")
    print("explorador.html actualizado")


if __name__ == "__main__":
    main()
