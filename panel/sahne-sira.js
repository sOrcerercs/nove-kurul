/* Gerçek modda sahnenin hangi aşamaları oynayacağını belirler. DOM'a dokunmaz. */
(function (kok) {
  const TIPLER = ["qa_al", "dagit", "analiz", "denetim", "ceo_sorgu", "revize", "ceo_onay", "qa_ilet"];
  const SAHNE = { finans: "finans", kalite: "kalite", okr: "okr", raporlama: "rapor", "satis-muduru": "satisMuduru" };
  function sira(onceki, liste, danisman) {
    let l = Array.isArray(liste) ? liste.filter(t => TIPLER.indexOf(t) >= 0) : [];
    const dept = Object.prototype.hasOwnProperty.call(SAHNE, danisman) ? SAHNE[danisman] : null;
    if (!dept) l = l.filter(t => t === "qa_al");
    const oyna = onceki === null ? l.slice(-1) : l.slice(onceki);
    return { oyna: oyna, gorulen: Math.max(onceki || 0, l.length), dept: dept };
  }
  const api = { TIPLER: TIPLER, SAHNE: SAHNE, sira: sira };
  kok.NoveSahneSira = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
