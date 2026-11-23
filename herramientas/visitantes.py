"""Genera la sección «Nuestros visitantes» de index.html (cifras, nube de instituciones y municipios)
a partir de la agenda de reservas y de herramientas/instituciones.csv.

Uso:  python3 herramientas/visitantes.py [contenido/visitas/agenda.xlsx]
Requiere openpyxl (pip install openpyxl). La agenda tiene datos personales y vive en
contenido/ (no se sube a GitHub); a la página solo llegan cifras agregadas.
"""
import re
from html import escape
import sys
import zlib
from collections import Counter
from datetime import datetime, time
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parent.parent
INICIO, FIN = "<!-- visitantes:inicio -->", "<!-- visitantes:fin -->"
MESES = "ene feb mar abr may jun jul ago sep oct nov dic".split()

COLEGIO = re.compile(r"colegio|escuela|institut|instituci|liceo|gimnasio|seminario|jard[ií]n|\bi\.?e\b|p[uú]blic|privad|niños|profe")
UNIVERSIDAD = re.compile(r"universidad|\bu\.? ?p[uú]blica|unab|\buts\b|\bupb\b")
UIS = re.compile(r"uis|comunidad|egresad|docente|trabajador")


def clasificar(tipo, obs, nombre, cantidad):
    """Categoría de una reserva. «Tipo de pago» es texto libre, así que se usan palabras clave."""
    texto = f"{tipo} {obs} {nombre}".lower()
    if UNIVERSIDAD.search(texto):
        return "Universidades"
    if COLEGIO.search(texto):
        return "Colegios"
    # shortcut: un grupo grande sin tipo se asume institucional; revisar si la agenda empieza a marcarlos.
    if cantidad >= 16:
        return "Otros grupos"
    return "Comunidad UIS" if UIS.search(texto) else "Público general y familias"


assert clasificar("Colegio privado", "", "", 30) == "Colegios"
assert clasificar("", "", "Institución Educativa X", 25) == "Colegios"
assert clasificar("U pública", "", "", 20) == "Universidades"
assert clasificar("2 c.uis y 1 menor", "", "", 3) == "Comunidad UIS"
assert clasificar("1 combo familiar", "", "", 5) == "Público general y familias"
assert clasificar("", "", "", 30) == "Otros grupos"


def realizada(marca):
    """La visita cuenta solo si «Realizada» tiene una x o la hora de ingreso; notas como «?» o «por confirmar» no."""
    return isinstance(marca, (time, datetime)) or str(marca or "").strip().lower() == "x"


assert realizada("x") and realizada(" X ") and realizada(time(10, 13))
assert not realizada(None) and not realizada("?") and not realizada("por confirmar")


def cargar_instituciones(ruta):
    """Tabla curada de instituciones: (patrón, nombre, municipio, departamento)."""
    lineas = [l for l in ruta.read_text(encoding="utf-8").splitlines()[1:] if l.strip() and not l.startswith("#")]
    return [(re.compile(p, re.I), n, m, d or "Santander") for p, n, m, d in (l.split(";") for l in lineas)]


INSTITUCIONES = cargar_instituciones(Path(__file__).with_name("instituciones.csv"))


def institucion(texto):
    """Primera institución de la tabla cuyo patrón aparece en el texto de la reserva, o None."""
    return next(((n, m, d) for p, n, m, d in INSTITUCIONES if p.search(texto)), None)


assert institucion("Grupo Colegio Nieves Cortés Picón de Girón SENA")[0] == "Colegio Nieves Cortés Picón"
assert institucion("Colegio Americano Santander de Lebrija")[2] == "Santander"
assert institucion("I.E. INEM Custodio García Rovira")[1] == "Bucaramanga"
assert institucion("2 c.uis y 1 menor") is None


def cuenta(marca, fecha, hoy):
    """Reserva con fecha pasada: cuenta si está marcada como realizada o si nadie la marcó.
    Notas como «?» o «por confirmar» la excluyen."""
    return fecha <= hoy and (realizada(marca) or not str(marca or "").strip())


assert cuenta(None, datetime(2026, 1, 1), datetime(2026, 2, 1))
assert not cuenta("?", datetime(2026, 1, 1), datetime(2026, 2, 1))
assert not cuenta(None, datetime(2026, 3, 1), datetime(2026, 2, 1))


def leer(ruta, hoy):
    """Filas (fecha, categoría, personas, institución) de las reservas que cuentan, en todas las hojas."""
    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    for hoja in libro.worksheets:
        filas = hoja.iter_rows(values_only=True)
        col = {str(h).strip(): i for i, h in enumerate(next(filas)) if h}
        for f in filas:
            dato = lambda k: f[col[k]] if k in col and col[k] < len(f) else None
            fecha, cantidad = dato("Fecha"), dato("Cantidad")
            if not isinstance(fecha, datetime) or not isinstance(cantidad, (int, float)) or cantidad <= 0:
                continue
            if not cuenta(dato("Realizada"), fecha, hoy):
                continue
            nombre, tipo, obs = (str(dato(k) or "") for k in ("Nombre completo", "Tipo de pago", "Observación"))
            cat = clasificar(tipo, obs, nombre, cantidad)
            yield fecha, cat, int(cantidad), institucion(f"{nombre} {tipo} {obs}")


def miles(n):
    return f"{n:,}".replace(",", ".")


def gente(n):
    return f"{miles(n)} persona" + ("" if n == 1 else "s")


def html(filas):
    personas, visitas, por_mes = Counter(), Counter(), Counter()
    por_inst, lugar = Counter(), {}
    for fecha, cat, n, inst in filas:
        personas[cat] += n
        visitas[cat] += 1
        por_mes[(fecha.year, fecha.month)] += n
        if inst:
            por_inst[inst[0]] += n
            lugar[inst[0]] = inst[1:]
    total, n_visitas = sum(personas.values()), sum(visitas.values())
    meses = sorted(por_mes)
    desde, hasta = meses[0], meses[-1]
    nombre_mes = lambda m: f"{MESES[m[1] - 1]} {m[0]}"
    escolar = personas["Colegios"] + personas["Universidades"]

    # Nube: tamaño según la raíz de las personas, para que las instituciones pequeñas sigan legibles.
    tope = max(por_inst.values()) ** 0.5
    nube = "\n".join(
        f'    <li style="--peso:{p ** 0.5 / tope:.2f}" title="{escape(n)}: {gente(p)}">{escape(n)}</li>'
        for n, p in sorted(por_inst.items(), key=lambda x: zlib.crc32(x[0].encode())))  # mezcla fija, no alfabética

    insts_por_mun = Counter((m, d) for m, d in lugar.values() if m)
    santander = [(m, k) for (m, d), k in insts_por_mun.items() if d == "Santander"]
    fuera = sorted(m if m == d else f"{m} ({d})" for (m, d) in insts_por_mun if d != "Santander")
    fuera = ", ".join(fuera[:-1]) + " y " + fuera[-1] if len(fuera) > 1 else "".join(fuera)
    sin_mun = sum(1 for m, d in lugar.values() if not m)
    municipios = "\n".join(
        f"    <li><b>{escape(m)}</b> {k} {'institución' if k == 1 else 'instituciones'}</li>"
        for m, k in sorted(santander, key=lambda x: (-x[1], x[0])))
    tabla = "\n".join(f"          <tr><td>{nombre_mes(m)}</td><td>{miles(por_mes[m])}</td></tr>" for m in meses)

    return f"""{INICIO}
<section id="visitantes" class="seccion">
  <h2>Nuestros visitantes</h2>
  <p class="intro">Entre {nombre_mes(desde)} y {nombre_mes(hasta)} recibimos {miles(total)} personas en {miles(n_visitas)} reservas, entre ellas {len(por_inst)} colegios, universidades y fundaciones de {len(santander)} municipios de Santander y de otras regiones del país.</p>
  <ul class="cifras">
    <li><b>{miles(total)}</b> personas con reserva</li>
    <li><b>{len(por_inst)}</b> instituciones educativas y sociales</li>
    <li><b>{len(santander)}</b> municipios de Santander</li>
    <li><b>{round(100 * escolar / total)} %</b> estudiantes de colegios y universidades</li>
  </ul>
  <h3>Instituciones que nos han visitado</h3>
  <ul class="nube">
{nube}
  </ul>
  <h3>De dónde vienen</h3>
  <ul class="municipios">
{municipios}
  </ul>
  <p>También nos han visitado desde {fuera}.</p>
  <details>
    <summary>Ver las personas por mes</summary>
    <table class="tabla-datos">
      <tr><th>Mes</th><th>Personas</th></tr>
{tabla}
    </table>
  </details>
  <p class="nota">Fuente: agenda de reservas del museo. Se cuentan las reservas con fecha pasada, salvo las marcadas como dudosas o por confirmar. El tamaño de cada nombre indica cuántas personas trajo la institución. {sin_mun} instituciones aún no tienen municipio confirmado.</p>
</section>
{FIN}"""


def main():
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "contenido/visitas/agenda.xlsx"
    pagina = RAIZ / "index.html"
    texto = pagina.read_text(encoding="utf-8")
    if INICIO not in texto or FIN not in texto:
        sys.exit(f"No encuentro los marcadores {INICIO} / {FIN} en index.html")
    antes, resto = texto.split(INICIO, 1)
    despues = resto.split(FIN, 1)[1]
    pagina.write_text(antes + html(leer(ruta, datetime.now())) + despues, encoding="utf-8")
    print("Sección de visitantes actualizada en index.html")


if __name__ == "__main__":
    main()
