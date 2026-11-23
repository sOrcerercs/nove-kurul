/* Rapor postasındaki bağlantı: `/?soru=<id>`. DOM'a dokunmaz. Desen `bin/panel_defter.ID_DESENI` ile aynı. */
(function (kok) {
  const DESEN = /^[a-z0-9-]{1,64}$/;

  function oku(search) {
    const d = new URLSearchParams(search || "").get("soru");
    return d !== null && DESEN.test(d) ? d : null;
  }

  function temiz(search) {
    const p = new URLSearchParams(search || "");
    p.delete("soru");
    const s = p.toString();
    return s ? "?" + s : "";
  }

  const api = { oku: oku, temiz: temiz };
  kok.NoveSoruBaglantisi = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
