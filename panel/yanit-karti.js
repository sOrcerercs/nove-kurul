/* Kurul yanıtını kart olarak çizer (skills/kurul-yaniti düzeni). DOM'a dokunmaz; girdi sunucunun güvenli HTML'i
   (`bin/panel_defter.md_html`: `## Başlık` → <h4>), çıktı HTML metnidir. Plan: docs/superpowers/plans/2026-10-19-answer-card-rendering.md */
(function (kok) {
  const BOLUMLER = { "kısa yanıt": "kisa", "dayanak": "dayanak", "bilinmeyenler": "bilinmeyen", "not": "not" };
  const ZORUNLU = ["kisa", "dayanak", "bilinmeyen"];   // Not isteğe bağlı (SKILL.md "Düzen")
  const UYARI = "Kontrol edilmesi gerekebilir";
  const ROZET = { "✅": ["bir", "birincil"], "🟡": ["iki", "ikincil"], "⛔": ["yok", "doğrulanamadı"] };
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const duz = h => h.replace(/<[^>]*>/g, "").trim().toLocaleLowerCase("tr-TR");

  /* <h4> başlıklarına göre böler. Baştaki <h3> (soru-id — kısa ad) atılır; ondan önceki/sonraki başka içerik `on`. */
  function bolumle(html) {
    const parcalar = String(html || "").split(/<h4>([\s\S]*?)<\/h4>/);
    const on = parcalar[0].replace(/^\s*<h3>[\s\S]*?<\/h3>/, "").trim();
    const bolumler = [];
    for (let i = 1; i < parcalar.length; i += 2) {
      const ad = duz(parcalar[i]);
      bolumler.push({ tur: BOLUMLER[ad] || null, baslik: parcalar[i], html: (parcalar[i + 1] || "").trim() });
    }
    const turler = bolumler.map(b => b.tur);
    const eksik = ZORUNLU.filter(t => turler.indexOf(t) < 0);
    const bilinmeyen = bolumler.filter(b => !b.tur).length;
    return { on: on, bolumler: bolumler, kontrol: eksik.length > 0 || bilinmeyen > 0 };
  }

  function rozetle(html) {
    return html.replace(/✅|🟡|⛔/g, e => `<span class="rozet r-${ROZET[e][0]}" title="${ROZET[e][1]}">${e}</span>`);
  }

  function bolumHtml(b) {
    if (b.tur === "kisa") return `<div class="kart-kisa md">${b.html}</div>`;
    if (b.tur === "dayanak") {
      const aciklama = /✅|🟡|⛔/.test(b.html)
        ? `<div class="rozet-aciklama">${Object.keys(ROZET).map(e => rozetle(e) + " " + ROZET[e][1]).join(" · ")}</div>` : "";
      return `<div class="kart-bolum"><div class="kart-ad">Dayanak</div><div class="md">${rozetle(b.html)}</div>${aciklama}</div>`;
    }
    if (b.tur === "bilinmeyen")
      return `<div class="kart-bilinmeyen"><div class="kart-ad">Bilinmeyenler</div><div class="md">${rozetle(b.html)}</div></div>`;
    if (b.tur === "not") return `<div class="kart-not"><div class="kart-ad">Not</div><div class="md">${b.html}</div></div>`;
    return `<div class="kart-bolum"><div class="kart-ad">${b.baslik}</div><div class="md">${b.html}</div></div>`;
  }

  /* g: {etiket_lbl, yanit_html, kurula_not_html, danisman_ad, tarih, imzalar:{denetci, ceo}} — metin alanları ham, burada kaçırılır. */
  function kart(g) {
    const b = bolumle(g.yanit_html);
    let govde;
    if (!b.bolumler.length) govde = `<div class="md">${g.yanit_html || ""}</div>`;
    else {
      const sira = ["kisa", "dayanak", "bilinmeyen", "not", null];
      govde = (b.on ? `<div class="md">${b.on}</div>` : "")
        + b.bolumler.slice().sort((x, y) => sira.indexOf(x.tur) - sira.indexOf(y.tur)).map(bolumHtml).join("");
    }
    const uyari = (!b.bolumler.length || b.kontrol) ? `<div class="kart-uyari" role="note">${UYARI}</div>` : "";
    const not = g.kurula_not_html
      ? `<div class="kurulanot"><div class="lbl">KURULA NOT</div><div class="md">${g.kurula_not_html}</div></div>` : "";
    const im = g.imzalar || {};
    const imza = [g.danisman_ad, g.tarih].filter(Boolean).map(esc)
      .concat([`Denetçi ${im.denetci ? "✓" : "—"}`, `CEO ${im.ceo ? "✓" : "—"}`]).join(" · ");
    return `<div class="answer kart"><div class="lbl">${esc(g.etiket_lbl || "")}</div>${uyari}${govde}${not}`
      + `<small class="kart-imza">${imza}</small></div>`;
  }

  const api = { bolumle: bolumle, rozetle: rozetle, kart: kart, UYARI: UYARI };
  kok.NoveYanitKarti = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
