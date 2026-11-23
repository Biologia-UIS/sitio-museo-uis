// Explorador de colecciones (explorador.html). Sin este archivo se ve el municipio con más registros, sin mapa.
const sinMovimiento = matchMedia("(prefers-reduced-motion: reduce)").matches;

// Muestra solo el panel del municipio elegido.
const municipio = document.querySelector("#explorador select");
municipio?.addEventListener("change", () => {
  document.querySelectorAll("#explorador [data-municipio]").forEach((p) => { p.hidden = p.dataset.municipio !== municipio.value; });
});

// Mapa del explorador: municipios de Santander (el elegido resaltado) y, encima, los puntos de colecta publicados en GBIF.
const datosMapa = document.getElementById("municipios-geo");
if (datosMapa && municipio && window.L) {
  const caja = document.getElementById("mapa-santander");
  const mapa = L.map(caja, { scrollWheelZoom: false });
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(mapa);
  const normal = (f) => ({ color: "#2f5d2a", weight: 1, fillColor: "#2f5d2a", fillOpacity: f.properties.n ? 0.12 : 0.03 });
  const capas = {};
  const limites = L.geoJSON(JSON.parse(datosMapa.textContent), {
    style: normal,
    onEachFeature: (f, capa) => {
      capas[f.properties.gid] = capa;
      capa.bindTooltip(`${f.properties.nombre}: ${f.properties.n ? f.properties.n.toLocaleString("es-CO") + " especímenes" : "sin registros"}`);
      capa.on("click", () => {
        if (!f.properties.n) return;
        municipio.value = f.properties.gid;
        municipio.dispatchEvent(new Event("change"));
      });
    },
  }).addTo(mapa);
  // Los puntos van en un panel propio por encima de los municipios y sin bloquear los clics.
  mapa.createPane("puntos").style.cssText = "z-index: 450; pointer-events: none";
  L.tileLayer(`https://api.gbif.org/v2/map/occurrence/adhoc/{z}/{x}/{y}@1x.png?srs=EPSG:3857&style=orange.marker&${caja.dataset.gbif}`, {
    pane: "puntos", attribution: 'Registros: <a href="https://www.gbif.org">GBIF</a>',
  }).addTo(mapa);

  const resaltar = (acercar) => {
    limites.resetStyle();
    const capa = capas[municipio.value];
    if (!capa) return;
    capa.setStyle({ color: "#1d241b", weight: 3, fillColor: "#ffcf33", fillOpacity: 0.8 }).bringToFront();
    if (acercar) mapa.flyToBounds(capa.getBounds(), { maxZoom: 11, padding: [20, 20], duration: sinMovimiento ? 0 : 0.8 });
  };
  mapa.fitBounds(limites.getBounds());
  resaltar(false);
  municipio.addEventListener("change", () => resaltar(true));
}
