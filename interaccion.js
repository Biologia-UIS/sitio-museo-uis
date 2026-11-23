// Animaciones al desplazarse, contadores y visor de fotos. Sin este archivo la página se ve completa, solo sin movimiento.
const quieto = matchMedia("(prefers-reduced-motion: reduce)").matches;

// Aparición suave de bloques y crecimiento de las gráficas al entrar en pantalla.
if (!quieto && "IntersectionObserver" in window) {
  const bloques = document.querySelectorAll(".seccion > h2, .seccion > .intro, .linea-tiempo li, .cifras, .ecosistemas li, .galeria li, .tarjetas article, .grafica-tipos, .grafica-meses, .dos-columnas > div");
  bloques.forEach((el) => el.classList.add("revelar"));
  const vigia = new IntersectionObserver((entradas) => {
    for (const e of entradas) {
      if (!e.isIntersecting) continue;
      e.target.classList.add("visible");
      if (e.target.matches(".cifras")) e.target.querySelectorAll("b").forEach(contar);
      vigia.unobserve(e.target);
    }
  }, { threshold: 0.15 });
  bloques.forEach((el) => vigia.observe(el));
}

// Cuenta desde 0 hasta la cifra escrita, conservando prefijos y sufijos ("+54.000", "63 %").
function contar(b) {
  const [, antes, numero, despues] = b.textContent.match(/^(\D*)([\d.]+)(.*)$/) || [];
  if (!numero) return;
  const meta = Number(numero.replace(/\./g, ""));
  const inicio = performance.now();
  const paso = (t) => {
    const avance = Math.min((t - inicio) / 1200, 1);
    b.textContent = antes + Math.round(meta * (1 - (1 - avance) ** 3)).toLocaleString("es-CO") + despues;
    if (avance < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
}

// Visor: las fotos de la sala y los ecosistemas se abren en grande.
const visor = document.createElement("dialog");
visor.className = "visor";
visor.innerHTML = '<img alt=""><p></p><button type="button" aria-label="Cerrar">×</button>';
document.body.append(visor);
visor.addEventListener("click", (e) => { if (e.target === visor || e.target.matches("button")) visor.close(); });

document.querySelectorAll(".ecosistemas img, .galeria img").forEach((img) => {
  const titulo = img.nextElementSibling?.textContent || img.alt;
  img.tabIndex = 0;
  img.setAttribute("role", "button");
  img.setAttribute("aria-label", `Ampliar: ${titulo}`);
  const abrir = () => {
    visor.querySelector("img").src = img.src;
    visor.querySelector("img").alt = img.alt;
    visor.querySelector("p").textContent = titulo;
    visor.showModal();
  };
  img.addEventListener("click", abrir);
  img.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); abrir(); } });
});
