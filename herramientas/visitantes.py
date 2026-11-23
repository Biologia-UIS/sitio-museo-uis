"""Genera la sección «Nuestros visitantes» de index.html a partir de la agenda de reservas.

Uso:  python3 herramientas/visitantes.py [contenido/visitas/agenda.xlsx]
Requiere openpyxl (pip install openpyxl). La agenda tiene datos personales y vive en
contenido/ (no se sube a GitHub); a la página solo llegan cifras agregadas.
"""
import re
import sys
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


def leer(ruta):
    """Filas (fecha, categoría, personas) de las visitas realizadas, en todas las hojas mensuales."""
    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    for hoja in libro.worksheets:
        filas = hoja.iter_rows(values_only=True)
        col = {str(h).strip(): i for i, h in enumerate(next(filas)) if h}
        for f in filas:
            dato = lambda k: f[col[k]] if k in col and col[k] < len(f) else None
            fecha, cantidad = dato("Fecha"), dato("Cantidad")
            if not realizada(dato("Realizada")) or not isinstance(fecha, datetime) or not isinstance(cantidad, (int, float)) or cantidad <= 0:
                continue
            cat = clasificar(dato("Tipo de pago") or "", dato("Observación") or "", dato("Nombre completo") or "", cantidad)
            yield fecha, cat, int(cantidad)


def miles(n):
    return f"{n:,}".replace(",", ".")


def gente(n):
    return f"{miles(n)} persona" + ("" if n == 1 else "s")


def html(filas):
    personas, visitas, por_mes = Counter(), Counter(), Counter()
    for fecha, cat, n in filas:
        personas[cat] += n
        visitas[cat] += 1
        por_mes[(fecha.year, fecha.month)] += n
    total, n_visitas = sum(personas.values()), sum(visitas.values())
    # Solo meses con visitas marcadas como realizadas; la nota de la página explica que faltan meses sin marcar.
    meses = sorted(por_mes)
    desde, hasta = meses[0], meses[-1]
    mayor, mayor_p = personas.most_common(1)[0]
    nombre_mes = lambda m: f"{MESES[m[1] - 1]} {m[0]}"
    escolar = personas["Colegios"] + personas["Universidades"]
    tope_cat, tope_mes = max(personas.values()), max(por_mes.values())

    barras = "\n".join(
        f'      <li><span>{c}</span><span class="valor" style="--v:{p / tope_cat:.3f}"></span>'
        f"<span>{miles(p)} · {round(100 * p / total)} %</span></li>"
        for c, p in personas.most_common())
    columnas = "\n".join(
        f'      <li style="--v:{por_mes[m] / tope_mes:.3f}" tabindex="0" data-tip="{nombre_mes(m)}: {gente(por_mes[m])}" aria-label="{nombre_mes(m)}: {gente(por_mes[m])}">'
        f"<span class=\"valor\"></span><span aria-hidden=\"true\">{MESES[m[1] - 1]} {str(m[0])[2:]}</span></li>"
        for m in meses)
    tabla = "\n".join(f"          <tr><td>{nombre_mes(m)}</td><td>{miles(por_mes[m])}</td></tr>" for m in meses)

    return f"""{INICIO}
<section id="visitantes" class="seccion">
  <h2>Nuestros visitantes</h2>
  <p class="intro">Entre {nombre_mes(desde)} y {nombre_mes(hasta)} registramos {miles(n_visitas)} visitas realizadas, con {miles(total)} personas. El grupo más numeroso: {mayor.lower()}, con el {round(100 * mayor_p / total)} % de los visitantes.</p>
  <ul class="cifras">
    <li><b>{miles(total)}</b> personas nos visitaron</li>
    <li><b>{miles(n_visitas)}</b> visitas realizadas</li>
    <li><b>{round(100 * escolar / total)} %</b> estudiantes de colegios y universidades</li>
  </ul>
  <h3>¿Quiénes nos visitan?</h3>
  <ul class="grafica-tipos">
{barras}
  </ul>
  <h3>Personas por mes</h3>
  <ul class="grafica-meses">
{columnas}
  </ul>
  <details>
    <summary>Ver los datos en tabla</summary>
    <table class="tabla-datos">
      <tr><th>Mes</th><th>Personas</th></tr>
{tabla}
    </table>
  </details>
  <p class="nota">Fuente: agenda de reservas del museo. Solo se cuentan las visitas marcadas como realizadas; los meses que no aparecen no tienen esa marca en la agenda, así que el número real de visitantes es mayor. El tipo de visitante se estima a partir de las notas de cada reserva; los grupos grandes sin descripción aparecen como «otros grupos».</p>
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
    pagina.write_text(antes + html(leer(ruta)) + despues, encoding="utf-8")
    print("Sección de visitantes actualizada en index.html")


if __name__ == "__main__":
    main()
