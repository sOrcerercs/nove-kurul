(function () {
  if (customElements.get('nove-ofis-4')) return;
  const URL3 = 'https://unpkg.com/three@0.160.0/build/three.module.js';

  const KISI = {
    finans:   { ad: 'Finans',       kravat: '#2e9e74', ceket: '#25324a', sac: '#2a1d14', ten: '#e3b98f' },
    kalite:   { ad: 'Kalite',       kravat: '#4a6fb5', ceket: '#3a3d44', sac: '#5a3a22', ten: '#efcfaa' },
    okr:      { ad: 'OKR',          kravat: '#c95564', ceket: '#2f3640', sac: '#17120e', ten: '#c99a6e' },
    rapor:    { ad: 'Raporlama',    kravat: '#c08a22', ceket: '#4a433c', sac: '#9a9792', ten: '#eac39b' },
    qa:       { ad: 'Q&A',          kravat: '#8a5cc0', ceket: '#27314a', sac: '#3a2618', ten: '#dcb088' },
    dagitici: { ad: 'İş Dağıtımcı', kravat: '#a77b3c', ceket: '#44403a', sac: '#2a1d14', ten: '#efcfaa' },
    denetci:  { ad: 'Denetçi',      kravat: '#3b8fc4', ceket: '#5b616c', sac: '#2a1d14', ten: '#e3b98f' },
    satisMuduru: { ad: 'Satış Müdürü', kravat: '#d06a3a', ceket: '#2b2f38', sac: '#3a2618', ten: '#dcb088' },
    ceo:      { ad: 'CEO',          kravat: '#c9962f', ceket: '#1d1f24', sac: '#c9c4bb', ten: '#e3b98f' }
  };
  const ODA_AD = { finans: 'FİNANS', kalite: 'KALİTE', okr: 'OKR', rapor: 'RAPORLAMA', qa: 'Q&A', dagitici: 'İŞ DAĞITIM' };
  const SLOT_Z = [-3.3, 0.5, 4.3, 8.1];
  const ODA = {};
  [['L', -1], ['R', 1]].forEach(([s, side]) => SLOT_Z.forEach((zc, i) => {
    const lz = zc - 0.55;
    ODA[s + i] = { side, zc, cx: side * 7.4, lz, hub: { x: side * 4.2, z: lz }, yol: [{ x: side * 1.5, z: lz }, { x: side * 3.2, z: lz }, { x: side * 4.2, z: lz }], sz: lz };
  }));
  ODA.ceo = { hub: { x: 0, z: -7.0 }, yol: [{ x: 0, z: -7.0 }], sz: -5.9 };
  const YER = { finans: 'L0', kalite: 'L1', okr: 'L2', rapor: 'L3', satisMuduru: 'R0', bos2: 'R1', dagitici: 'R2', qa: 'R3' };
  const HOL = -5.9, LOBI = 10.45;
  const S_X = [-7.2, -3.6, 0, 3.6, 7.2], S_Z = [15.6, 17.8, 20.0, 22.2], S_LANE = [14.15, 16.45, 18.65, 20.85, 23.1], S_AISLE = 5.4;
  ODA.satis = { hub: { x: S_AISLE, z: 14.15 }, yol: [{ x: 4.6, z: LOBI }, { x: 4.6, z: 14.15 }, { x: S_AISLE, z: 14.15 }], sz: LOBI };
  const SATIS = {}, ZIL = { x: -11.15, z: 14.2 };
  (function () {
    const CK = ['#25324a', '#3a3d44', '#2f3640', '#4a433c', '#27314a', '#1d1f24', '#44403a', '#5b616c'], KR = ['#2e9e74', '#4a6fb5', '#c95564', '#c08a22', '#8a5cc0', '#3b8fc4', '#d06a3a', '#6b8f3a'];
    const SC = ['#2a1d14', '#5a3a22', '#17120e', '#9a9792', '#3a2618', '#7a4a28'], TN = ['#e3b98f', '#efcfaa', '#c99a6e', '#eac39b', '#dcb088', '#b5835a'];
    for (let i = 0; i < 20; i++) { const r = Math.floor(i / 5), c = i % 5, k = 'satis' + i; SATIS[k] = { x: S_X[c], zd: S_Z[r], r }; KISI[k] = { ad: 'Satış', kravat: KR[(i * 3) % 8], ceket: CK[(i * 5) % 8], sac: SC[(i * 7) % 6], ten: TN[(i * 5) % 6], ekip: true }; }
  })();

  const N = {
    seat: (k) => {
      if (SATIS[k]) { const S = SATIS[k], L = S_LANE[S.r]; return { x: S.x, z: S.zd - 0.75, oda: 'satis', ek: [{ x: S_AISLE, z: L }, { x: S.x, z: L }], oturur: true }; }
      if (k === 'ceo') return { x: 0, z: -9.2, oda: 'ceo', ek: [{ x: 2.4, z: -7.0 }, { x: 2.4, z: -9.2 }], oturur: true };
      const o = YER[k], R = ODA[o]; return { x: R.cx, z: R.lz, oda: o, oturur: true };
    },
    ziyaret: (k) => {
      if (k === 'ceo') return { x: 0.45, z: -7.15, oda: 'ceo', yuz: Math.PI };
      const o = YER[k], R = ODA[o]; return { x: R.cx - R.side * 1.75, z: R.zc - 0.4, oda: o, yuz: R.side * Math.PI / 2 };
    },
    ziyaretSol: (k) => {
      const o = YER[k], R = ODA[o], bz = R.zc - 1.3, x = R.cx + R.side * 1.75;
      return { x, z: R.zc - 0.4, oda: o, yuz: -R.side * Math.PI / 2, ek: [{ x: R.hub.x, z: bz }, { x, z: bz }] };
    },
    zil: () => ({ x: -10.4, z: 14.15, oda: 'satis', ek: [], yuz: -Math.PI / 2 }),
    kurul: () => ({ x: 0, z: LOBI, sz: LOBI, yuz: 0 }),
    kahve: () => ({ x: -7.8, z: -8.95, yol: [{ x: -7.8, z: HOL }], sz: HOL, yuz: Math.PI })
  };
  const DEVRIYE = [];
  [0, 1, 2, 3].forEach((i) => DEVRIYE.push({ x: -1.5, z: ODA['L' + i].lz, sz: ODA['L' + i].lz, yuz: -Math.PI / 2, dur: 1100 }));
  DEVRIYE.push({ x: 0, z: LOBI - 0.2, sz: LOBI - 0.2, yuz: 0, dur: 900 });
  [3, 2, 1, 0].forEach((i) => DEVRIYE.push({ x: 1.5, z: ODA['R' + i].lz, sz: ODA['R' + i].lz, yuz: Math.PI / 2, dur: 1100 }));
  DEVRIYE.push({ x: 0, z: HOL, sz: HOL, yuz: Math.PI, dur: 900 });

  const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
  const rev = (a) => (a ? a.slice().reverse() : []);
  const cl = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerpA = (a, b, t) => { let d = ((b - a + Math.PI) % (Math.PI * 2)) - Math.PI; if (d < -Math.PI) d += Math.PI * 2; return a + d * t; };

  class NoveOfis4 extends HTMLElement {
    connectedCallback() {
      if (this._init) return;
      this._init = true;
      Object.assign(this.style, { display: 'block', position: 'relative', width: '100%', height: '100%', overflow: 'hidden', background: '#ffffff' });
      import(URL3).then((T) => { if (this.isConnected) this.kur(T); });
    }
    disconnectedCallback() {
      cancelAnimationFrame(this._raf); clearInterval(this._gez); clearTimeout(this._satT);
      if (this._ro) this._ro.disconnect();
      window.removeEventListener('nove-akis', this._onAkis); window.removeEventListener('nove-komut', this._onKomut); window.removeEventListener('nove-ayar', this._onAyar);
      if (this.renderer) { this.renderer.dispose(); this.renderer.domElement.remove(); }
      if (this.katman) this.katman.remove();
      this._init = false; window.__noveOfisHazir = false;
    }

    kur(T) {
      this.T = T;
      const r = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
      r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      r.shadowMap.enabled = true; r.shadowMap.type = T.PCFSoftShadowMap;
      r.outputColorSpace = T.SRGBColorSpace;
      Object.assign(r.domElement.style, { display: 'block', width: '100%', height: '100%', touchAction: 'none' });
      this.appendChild(r.domElement);
      this.renderer = r;
      this.katman = document.createElement('div');
      Object.assign(this.katman.style, { position: 'absolute', inset: '0', pointerEvents: 'none', overflow: 'hidden', fontFamily: "'IBM Plex Sans', sans-serif" });
      this.appendChild(this.katman);

      const s = new T.Scene(); s.background = new T.Color('#ffffff'); this.sahne = s;
      this.kamera = new T.OrthographicCamera(-10, 10, 10, -10, 0.1, 200);
      this.kamera.position.set(14, 19.6, 15.4); this.kamera.lookAt(0, 0, 1.4);
      s.add(new T.HemisphereLight(0xffffff, 0xeeeae2, 1.75));
      const g = new T.DirectionalLight(0xffffff, 1.7);
      g.position.set(-6, 24, 20); g.target.position.set(0, 0, 6.5); s.add(g.target); g.castShadow = true;
      g.shadow.mapSize.set(3072, 3072);
      Object.assign(g.shadow.camera, { left: -25, right: 25, top: 25, bottom: -25, near: 1, far: 90 });
      g.shadow.bias = -0.0006; g.shadow.radius = 5;
      s.add(g);

      this._mat = {};
      this.cam = new T.MeshStandardMaterial({ color: '#d6e7f0', transparent: true, opacity: 0.16, roughness: 0.1, depthWrite: false });
      this._secimHedef = [];
      this.ofis();
      this.ajan = {};
      Object.keys(KISI).forEach((k) => this.ajanEkle(k));
      this.etiketler();

      this.ray = new T.Raycaster(); this.zemin = new T.Plane(new T.Vector3(0, 1, 0), 0);
      this.olaylar();
      this.boyut();
      this._ro = new ResizeObserver(() => this.boyut()); this._ro.observe(this);

      this.hiz = (window.__noveAyar && window.__noveAyar.hiz) || 1;
      this._onAyar = (e) => { this.hiz = (e.detail && e.detail.hiz) || 1; };
      this._onAkis = (e) => this.akis(e.detail);
      this._onKomut = (e) => this.komut(e.detail);
      window.addEventListener('nove-ayar', this._onAyar);
      window.addEventListener('nove-akis', this._onAkis);
      window.addEventListener('nove-komut', this._onKomut);
      window.__noveOfisHazir = true;

      this.devriye();
      this._gez = setInterval(() => this.gezinti(), 10000);
      this._satT = setTimeout(() => this.satisDongu(), 2500);
      this.saat = new T.Clock();
      const dongu = () => { this._raf = requestAnimationFrame(dongu); this.kare(); };
      dongu();
    }

    mat(c, o) {
      const key = c + JSON.stringify(o || {});
      if (!this._mat[key]) this._mat[key] = new this.T.MeshStandardMaterial(Object.assign({ color: c, roughness: 0.85, metalness: 0 }, o || {}));
      return this._mat[key];
    }
    kutu(w, h, d, c, x, y, z, ust, o) {
      const T = this.T;
      const m = new T.Mesh(new T.BoxGeometry(w, h, d), o && o.mat ? o.mat : this.mat(c));
      m.position.set(x, y, z); m.castShadow = !(o && o.golgesiz); m.receiveShadow = true;
      (ust || this.sahne).add(m); return m;
    }
    silindir(rt, rb, h, c, x, y, z, ust) {
      const T = this.T;
      const m = new T.Mesh(new T.CylinderGeometry(rt, rb, h, 20), this.mat(c));
      m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; (ust || this.sahne).add(m); return m;
    }
    bitki(x, z, k) {
      const T = this.T; k = k || 1;
      this.silindir(0.28 * k, 0.22 * k, 0.5 * k, '#e4ded3', x, 0.25 * k, z);
      const y = new T.Mesh(new T.IcosahedronGeometry(0.55 * k, 0), this.mat('#6fa883', { flatShading: true }));
      y.position.set(x, 0.95 * k, z); y.castShadow = true; this.sahne.add(y);
      const y2 = new T.Mesh(new T.IcosahedronGeometry(0.38 * k, 0), this.mat('#5a9670', { flatShading: true }));
      y2.position.set(x + 0.2 * k, 1.35 * k, z - 0.1 * k); y2.castShadow = true; this.sahne.add(y2);
    }
    duvarX(x1, x2, z, h, renk) {
      const L = x2 - x1, mx = (x1 + x2) / 2;
      this.kutu(L, h, 0.14, renk || '#f2f0eb', mx, h / 2, z);
      this.kutu(L + 0.02, 0.03, 0.16, '#cbc5ba', mx, h + 0.015, z, this.sahne, { golgesiz: true });
    }
    duvarZ(x, z1, z2, h, renk) {
      const L = z2 - z1, mz = (z1 + z2) / 2;
      this.kutu(0.14, h, L, renk || '#f2f0eb', x, h / 2, mz);
      this.kutu(0.16, 0.03, L + 0.02, '#cbc5ba', x, h + 0.015, mz, this.sahne, { golgesiz: true });
    }
    panjur(x, y, z, w, h, yon) {
      const s = this.sahne, n = Math.floor(h / 0.11), o = { golgesiz: true };
      if (yon === 'x') {
        this.kutu(w + 0.1, h + 0.1, 0.03, '#d9d5cd', x, y, z, s, o);
        this.kutu(w, h, 0.02, '#46505c', x, y, z + 0.02, s, o);
        for (let i = 0; i < n; i++) this.kutu(w - 0.04, 0.045, 0.02, '#eceae5', x, y - h / 2 + 0.06 + i * 0.11, z + 0.04, s, o);
      } else {
        this.kutu(0.03, h + 0.1, w + 0.1, '#d9d5cd', x, y, z, s, o);
        this.kutu(0.02, h, w, '#46505c', x + 0.02, y, z, s, o);
        for (let i = 0; i < n; i++) this.kutu(0.02, 0.045, w - 0.04, '#eceae5', x + 0.04, y - h / 2 + 0.06 + i * 0.11, z, s, o);
      }
    }
    tablo(x, y, z, w, h, renk, yon) {
      const s = this.sahne, o = { golgesiz: true };
      if (yon === 'z') { this.kutu(0.03, h, w, '#6b4a2e', x, y, z, s, o); this.kutu(0.02, h - 0.08, w - 0.08, renk, x + 0.02, y, z, s, o); }
      else { this.kutu(w, h, 0.03, '#6b4a2e', x, y, z, s, o); this.kutu(w - 0.08, h - 0.08, 0.02, renk, x, y, z + 0.02, s, o); }
    }
    kapi(x, z1, z2, yon) {
      const s = this.sahne;
      if (yon === 'z') { this.kutu(0.05, 1.2, z2 - z1, '#b4895c', x, 0.6, (z1 + z2) / 2); this.silindir(0.025, 0.025, 0.05, '#c9c4bb', x - Math.sign(x) * 0.05, 0.6, z2 - 0.12, s); }
      else { this.kutu(z2 - z1, 1.2, 0.05, '#b4895c', (z1 + z2) / 2, 0.6, x); }
    }

    ofis() {
      const T = this.T, s = this.sahne;
      const H = 1.25;
      this.kutu(23.8, 0.42, 34.2, '#d3cbbd', 0, -0.21, 6.5);
      this.kutu(23.5, 0.02, 33.9, '#e4ded4', 0, 0.002, 6.5, s, { golgesiz: true });
      this.kutu(6.2, 0.02, 15.0, '#ece8e1', 0, 0.01, 2.4, s, { golgesiz: true });
      this.kutu(23.2, 0.02, 1.3, '#ece8e1', 0, 0.01, HOL, s, { golgesiz: true });
      this.kutu(11.0, 0.02, 3.5, '#ddd5c7', 0, 0.012, 11.9, s, { golgesiz: true });
      // dış duvarlar: arka ve sol yüksek, sağ ve ön kesik
      this.duvarX(-11.85, 11.85, -10.55, 2.5);
      this.duvarZ(-11.85, -10.55, 23.6, 2.5);
      this.duvarZ(11.85, -10.55, 23.6, 0.35);
      this.duvarX(-11.85, 3.9, 13.8, 1.0); this.duvarX(5.3, 11.85, 13.8, 1.0); this.duvarX(-11.85, 11.85, 23.6, 0.35);
      [-9.6, -6.3, 6.3, 9.6].forEach((x) => this.panjur(x, 1.5, -10.47, 2.2, 1.3, 'x'));
      this.kutu(6.9, 2.3, 0.02, '#e3d8c6', 0, 1.2, -10.47, s, { golgesiz: true });
      SLOT_Z.forEach((zc) => this.panjur(-11.77, 1.45, zc, 2.4, 1.2, 'z'));
      this.panjur(-11.77, 1.45, 11.9, 2.6, 1.2, 'z');
      // oda duvarları
      [-5.2, -1.4, 2.4, 6.2, 10.0].forEach((z) => { this.duvarX(-11.8, -3.2, z, H); this.duvarX(3.2, 11.8, z, H); });
      [-1, 1].forEach((sd) => SLOT_Z.forEach((zc) => {
        const lz = zc - 0.55;
        this.duvarZ(sd * 3.2, zc - 1.9, lz - 0.7, H); this.duvarZ(sd * 3.2, lz + 0.7, zc + 1.9, H);
        this.kapi(sd * 3.12 - sd * 0.0 - sd * 0.1, lz + 0.72, lz + 1.85, 'z');
      }));
      // CEO odası duvarları
      this.duvarZ(-3.6, -10.5, -6.6, 1.6); this.duvarZ(3.6, -10.5, -6.6, 1.6);
      this.duvarX(-3.6, -0.75, -6.6, H); this.duvarX(0.75, 3.6, -6.6, H);
      this.kutu(1.2, 1.2, 0.05, '#b4895c', 1.4, 0.6, -6.5);
      this.panjur(-2.2, 0.75, -6.5, 2.0, 0.7, 'x');
      // kurul odası
      this.duvarZ(-5.6, 10.0, 13.8, H); this.duvarZ(5.6, 10.0, 13.8, H);
      this.kutu(0.03, 0.8, 2.2, '#fbfbfa', -5.5, 0.85, 12.0, s, { golgesiz: true });
      this.kutu(0.04, 0.86, 2.26, '#b9b5ad', -5.53, 0.85, 12.0, s, { golgesiz: true });
      this.kutu(0.6, 0.85, 0.5, '#e2ded6', -4.9, 0.42, 13.3);
      this.kutu(0.5, 0.12, 0.4, '#3a3d44', -4.9, 0.9, 13.3);
      this.satisOdasi();

      // CEO odası
      this.kutu(7.1, 0.02, 3.7, '#dcc8a6', 0, 0.014, -8.5, s, { golgesiz: true });
      this.kutu(3.0, 0.08, 1.1, '#6b4a2e', 0, 0.76, -8.3);
      this.kutu(0.08, 0.72, 1.0, '#5a3d25', -1.42, 0.36, -8.3);
      this.kutu(0.08, 0.72, 1.0, '#5a3d25', 1.42, 0.36, -8.3);
      this.kutu(2.8, 0.5, 0.04, '#5a3d25', 0, 0.45, -7.78);
      this.monitor(-0.45, -8.55, '#c9962f', 0.15);
      this.monitor(0.55, -8.55, '#c9962f', -0.15);
      this.kutu(0.5, 0.02, 0.35, '#efe9dc', -1.0, 0.81, -8.05);
      this.sandalye(0, -9.2, true);
      this.kutu(3.2, 2.0, 0.4, '#ece7dd', 0, 1.0, -10.15);
      const kitap = ['#8a5a3c', '#3d5a80', '#c9962f', '#6b6b6b', '#a33b3b', '#2e7d5b'];
      for (let raf = 0; raf < 3; raf++) {
        this.kutu(3.1, 0.04, 0.38, '#d8d1c3', 0, 0.35 + raf * 0.6, -10.0, s, { golgesiz: true });
        for (let i = 0; i < 9; i++) this.kutu(0.14, 0.38, 0.26, kitap[(i + raf * 2) % kitap.length], -1.3 + i * 0.22 + (raf % 2) * 0.1, 0.56 + raf * 0.6, -10.0, s, { golgesiz: true });
      }
      this.bitki(-3.05, -9.85, 0.85);
      this.bitki(3.05, -7.2, 0.7);
      this.kutu(0.9, 0.42, 0.85, '#c8bba6', -2.6, 0.21, -7.4);
      this.kutu(0.9, 0.5, 0.2, '#b8aa93', -2.6, 0.55, -7.75);
      this._secimHedef.push(this.hedef(0, -8.7, 3.4, 2.4, 'ceo'));

      // Kahve köşesi (sol üst)
      this.kutu(5.0, 0.92, 0.65, '#ece8e0', -8.0, 0.46, -10.05);
      this.kutu(5.05, 0.05, 0.7, '#cfc8bb', -8.0, 0.945, -10.05);
      this.kutu(0.45, 0.55, 0.4, '#2b2d31', -9.7, 1.25, -10.1);
      this.kutu(0.75, 1.9, 0.6, '#2d3036', -11.2, 0.95, -9.95);
      this.kutu(0.5, 1.2, 0.02, '#6f8fa8', -11.25, 1.15, -9.64, this.sahne, { golgesiz: true });
      this.kutu(0.7, 1.75, 0.6, '#f2f1ee', -5.0, 0.875, -9.95);
      this.silindir(0.17, 0.17, 0.5, '#cfe3ef', -4.4, 1.2, -9.95);
      this.kutu(0.36, 0.95, 0.36, '#e4e2de', -4.4, 0.475, -9.95);
      this.silindir(0.07, 0.06, 0.12, '#ffffff', -8.4, 1.03, -9.9);
      this.silindir(0.07, 0.06, 0.12, '#ffffff', -8.1, 1.03, -10.0);
      this.silindir(0.42, 0.42, 0.04, '#dcc7a2', -10.3, 1.05, -7.6);
      this.silindir(0.05, 0.05, 1.03, '#8c8a85', -10.3, 0.52, -7.6);
      this.silindir(0.25, 0.25, 0.03, '#8c8a85', -10.3, 0.02, -7.6);


      // Bekleme (sağ üst)
      this.kutu(3.0, 0.42, 0.9, '#c8cdd4', 7.6, 0.21, -9.6);
      this.kutu(3.0, 0.6, 0.25, '#b7bdc6', 7.6, 0.62, -10.05);
      this.kutu(1.3, 0.04, 0.7, '#d8c29d', 7.6, 0.4, -8.35);
      this.silindir(0.04, 0.04, 0.38, '#8c8a85', 7.6, 0.19, -8.35);
      this.bitki(4.4, -9.9, 0.9);
      this.bitki(11.0, -9.9, 0.9);

      Object.keys(YER).forEach((k) => this.odaKur(YER[k], k));
      this.bitki(-2.75, ODA.L1.zc + 1.45, 0.6); this.bitki(-2.75, ODA.L3.zc + 1.45, 0.6);
      this.bitki(2.75, ODA.R0.zc + 1.45, 0.6); this.bitki(2.75, ODA.R2.zc + 1.45, 0.6);

      // Kurul masası (lobi)
      this.kutu(8.6, 0.02, 2.8, '#e6dfd2', 0, 0.012, 11.9, s, { golgesiz: true });
      this.kutu(7.0, 0.09, 1.6, '#7a5636', 0, 0.76, 11.8);
      this.kutu(6.4, 0.7, 0.8, '#5f4229', 0, 0.37, 11.8);
      for (let i = 0; i < 5; i++) {
        const x = -2.8 + i * 1.4;
        this.sandalyeYon(x, 12.95, Math.PI);
        if (i > 0 && i < 4) this.kutu(0.42, 0.02, 0.3, '#f4efe4', x, 0.815, 12.2, s, { golgesiz: true });
      }
      this.silindir(0.09, 0.07, 0.28, '#e6eef2', 1.9, 0.94, 11.6);
      this.silindir(0.09, 0.07, 0.28, '#e6eef2', -1.7, 0.94, 11.7);
      this.bitki(-11.0, 13.0, 1.0); this.bitki(11.0, 13.0, 1.0); this.bitki(-11.0, 10.6, 0.7); this.bitki(11.0, 10.6, 0.7);
    }

    satisOdasi() {
      const T = this.T, s = this.sahne, o = { golgesiz: true };
      this.kutu(23.4, 0.02, 9.6, '#dbd3c5', 0, 0.006, 18.75, s, o);
      this.kutu(23.4, 0.02, 0.5, '#ece8e1', 0, 0.012, 14.15, s, o);
      [16.6, 19.4, 22.2].forEach((z) => this.panjur(-11.77, 1.45, z, 2.2, 1.2, 'z'));
      this.kutu(3.2, 0.62, 0.03, '#fbfbfa', -3.2, 0.55, 13.9, s, o);
      this.kutu(3.28, 0.7, 0.02, '#b9b5ad', -3.2, 0.55, 13.885, s, o);
      this.kutu(1.2, 0.05, 0.02, '#d06a3a', -3.9, 0.7, 13.92, s, o);
      this.kutu(0.8, 0.05, 0.02, '#2e9e74', -2.6, 0.55, 13.92, s, o);
      S_Z.forEach((zd, r) => S_X.forEach((x, c) => {
        const k = 'satis' + (r * 5 + c);
        this.kutu(1.8, 0.06, 0.8, '#c9a173', x, 0.75, zd);
        this.kutu(1.7, 0.66, 0.04, '#b4895c', x, 0.38, zd + 0.37);
        this.kutu(0.05, 0.72, 0.74, '#b4895c', x - 0.86, 0.36, zd);
        this.kutu(0.05, 0.72, 0.74, '#b4895c', x + 0.86, 0.36, zd);
        this.kutu(1.8, 0.32, 0.04, '#d9d4ca', x, 0.94, zd + 0.41);
        this.monitor(x + 0.2, zd + 0.1, KISI[k].kravat, 0);
        this.kutu(0.45, 0.02, 0.18, '#d4d0c8', x + 0.15, 0.79, zd - 0.22);
        this.silindir(0.06, 0.05, 0.12, '#ffffff', x - 0.6, 0.84, zd - 0.15);
        this.sandalye(x, zd - 0.75);
      }));
      this.silindir(0.3, 0.32, 0.06, '#5a3d25', ZIL.x - 0.25, 0.03, ZIL.z);
      this.silindir(0.045, 0.045, 1.75, '#6b4a2e', ZIL.x - 0.25, 0.875, ZIL.z);
      this.kutu(0.42, 0.05, 0.05, '#6b4a2e', ZIL.x - 0.06, 1.72, ZIL.z);
      const zil = new T.Group(); zil.position.set(ZIL.x + 0.08, 1.7, ZIL.z); s.add(zil);
      const altin = this.mat('#d4a632', { metalness: 0.55, roughness: 0.3 });
      const can = new T.Mesh(new T.CylinderGeometry(0.08, 0.22, 0.3, 28), altin); can.position.y = -0.19; can.castShadow = true; zil.add(can);
      const tep = new T.Mesh(new T.SphereGeometry(0.08, 16, 10), altin); tep.position.y = -0.05; zil.add(tep);
      const dil = new T.Mesh(new T.SphereGeometry(0.045, 10, 8), this.mat('#6b4a2e')); dil.position.y = -0.36; zil.add(dil);
      this.zil = zil;
      const halka = new T.Mesh(new T.RingGeometry(0.3, 0.36, 40), new T.MeshBasicMaterial({ color: '#c9962f', transparent: true, opacity: 0, side: T.DoubleSide, depthWrite: false }));
      halka.position.set(ZIL.x + 0.08, 1.5, ZIL.z); halka.lookAt(this.kamera.position.clone().add(new T.Vector3(ZIL.x, 0, ZIL.z))); halka.visible = false; s.add(halka);
      this.zilHalka = halka;
      this.bitki(11.0, 14.6, 0.8); this.bitki(11.0, 22.9, 0.9); this.bitki(-11.0, 22.9, 0.8);
    }
    satisDongu() {
      if (!this.isConnected) return;
      this._satT = setTimeout(() => this.satisDongu(), 3000 + Math.random() * 4500);
      const now = performance.now();
      if (this._zilAktif && now - this._zilAktif < 20000) return;
      const aday = Object.keys(SATIS).map((k) => this.ajan[k]).filter((a) => a.oturuyor && !a.mesgul && this.secili !== a.key);
      if (!aday.length) return;
      const a = aday[Math.floor(Math.random() * aday.length)];
      a.mesgul = true; this._zilAktif = now;
      const p = this.yuru(a, N.zil()), id = a.cmd;
      p.then(() => { this.zilCal(); this.balon(a.key, 'Satış kapandı!', 2200); return bekle(1700); })
        .then(() => (a.cmd === id ? this.yuru(a, N.seat(a.key)) : null))
        .then(() => { a.mesgul = false; this._zilAktif = 0; });
    }
    zilCal() {
      this._zilT = performance.now();
      this.satisSay = (this.satisSay || 0) + 1;
      if (this.zilEl) this.zilEl.firstChild.textContent = 'ZİL · ' + this.satisSay + ' SATIŞ';
      if (Math.random() < 0.45) this.balon('satisMuduru', 'Tebrikler ekip!', 1800);
      window.dispatchEvent(new CustomEvent('nove-satis', { detail: { adet: this.satisSay } }));
    }

    hedef(x, z, w, d, secim) {
      const m = this.kutu(w, 1.6, d, '#000', x, 0.8, z, this.sahne, { mat: new this.T.MeshBasicMaterial({ visible: false }), golgesiz: true });
      m.userData.secim = secim; return m;
    }

    odaKur(key, ak) {
      const T = this.T, R = ODA[key], sd = R.side, cx = R.cx, zc = R.zc, s = this.sahne;
      const bos = ak.indexOf('bos') === 0, renk = bos ? '#cfc9bf' : KISI[ak].kravat;
      const acik = new T.Color(renk).lerp(new T.Color('#ffffff'), 0.84).getStyle();
      this.kutu(4.4, 0.02, 2.5, acik, cx + sd * 0.2, 0.012, zc + 0.05, s, { golgesiz: true });
      const vurgu = bos ? '#ece9e3' : new T.Color(renk).lerp(new T.Color('#f2f0eb'), 0.62).getStyle();
      this.kutu(8.3, 1.15, 0.02, vurgu, sd * 7.5, 0.6, zc - 1.82, s, { golgesiz: true });
      if (!bos) { this.tablo(cx - 0.6, 1.0, zc - 1.8, 0.55, 0.32, new T.Color(renk).lerp(new T.Color('#ffffff'), 0.4).getStyle()); this.tablo(cx + 0.3, 1.0, zc - 1.8, 0.35, 0.32, '#d9cbb0'); }
      this.kutu(3.4, 0.7, 0.3, '#ece7dd', cx, 0.35, zc - 1.72);
      this.kutu(3.45, 0.04, 0.32, '#d8d1c3', cx, 0.72, zc - 1.72);
      this.kutu(0.4, 1.3, 1.2, '#e4dfd5', sd * 11.3, 0.65, zc + 0.3);
      this.bitki(sd * 11.0, zc - 1.45, 0.65);
      const x = cx, z = zc + 0.35;
      this.kutu(2.4, 0.07, 1.0, '#c9a173', x, 0.75, z);
      this.kutu(0.06, 0.72, 0.9, '#b4895c', x - 1.12, 0.36, z);
      this.kutu(0.06, 0.72, 0.9, '#b4895c', x + 1.12, 0.36, z);
      this.kutu(2.2, 0.66, 0.04, '#b4895c', x, 0.38, z + 0.47);
      this.sandalye(x, R.lz);
      if (!bos) {
        this.monitor(x + 0.25, z + 0.1, renk, 0);
        this.kutu(0.6, 0.02, 0.2, '#d4d0c8', x + 0.2, 0.795, z - 0.27);
        this.silindir(0.065, 0.055, 0.13, '#ffffff', x - 0.85, 0.85, z - 0.2);
        this.kutu(0.42, 0.03, 0.3, '#f6f2ea', x - 0.55, 0.8, z + 0.05, s, { golgesiz: true });
        this.kutu(0.5, 0.07, 0.04, renk, x - 0.6, 0.82, z + 0.45);
        const kit = ['#8a5a3c', '#3d5a80', renk, '#6b6b6b', '#c9c1b3'];
        for (let i = 0; i < 7; i++) this.kutu(0.13, 0.32, 0.22, kit[i % kit.length], cx - 1.3 + i * 0.17, 0.9, zc - 1.72, s, { golgesiz: true });
        this.silindir(0.1, 0.08, 0.2, '#e4ded3', cx + 1.2, 0.84, zc - 1.72);
      }
      this._secimHedef.push(this.hedef(cx, zc - 0.2, 3.0, 2.4, bos ? 'bos' : ak));
    }

    monitor(x, z, renk, don) {
      const T = this.T, g = new T.Group(); g.position.set(x, 0, z); g.rotation.y = don || 0; this.sahne.add(g);
      this.kutu(0.08, 0.3, 0.08, '#3a3d44', 0, 0.95, 0, g);
      this.kutu(0.3, 0.02, 0.2, '#3a3d44', 0, 0.8, 0, g);
      this.kutu(0.95, 0.56, 0.05, '#25282e', 0, 1.3, 0, g);
      const ekran = new T.Mesh(new T.PlaneGeometry(0.86, 0.47), new T.MeshStandardMaterial({ color: '#0f1418', emissive: renk, emissiveIntensity: 0.35 }));
      ekran.position.set(0, 1.3, -0.027); ekran.rotation.y = Math.PI; g.add(ekran);
      return g;
    }
    sandalye(x, z, buyuk) {
      const k = buyuk ? 1.15 : 1;
      this.silindir(0.04, 0.04, 0.4, '#8c8a85', x, 0.22, z);
      this.silindir(0.3, 0.3, 0.03, '#8c8a85', x, 0.03, z);
      this.kutu(0.6 * k, 0.09, 0.56, buyuk ? '#2a2420' : '#3a3d44', x, 0.48, z);
      this.kutu(0.6 * k, buyuk ? 0.85 : 0.6, 0.08, buyuk ? '#2a2420' : '#3a3d44', x, buyuk ? 1.0 : 0.85, z - 0.3);
    }
    sandalyeYon(x, z, yon) {
      const T = this.T, g = new T.Group(); g.position.set(x, 0, z); g.rotation.y = yon; this.sahne.add(g);
      this.silindir(0.04, 0.04, 0.4, '#8c8a85', 0, 0.22, 0, g);
      this.kutu(0.56, 0.09, 0.52, '#d8d3ca', 0, 0.48, 0, g);
      this.kutu(0.56, 0.55, 0.07, '#d8d3ca', 0, 0.8, -0.27, g);
    }

    insan(k) {
      const T = this.T, c = KISI[k];
      const g = new T.Group(), govde = new T.Group(); g.add(govde);
      const koyu = new T.Color(c.ceket).multiplyScalar(0.8).getStyle();
      const bacak = (yon) => {
        const kalca = new T.Group(); kalca.position.set(yon * 0.13, 0.9, 0); govde.add(kalca);
        this.kutu(0.19, 0.47, 0.21, koyu, 0, -0.23, 0, kalca);
        const diz = new T.Group(); diz.position.y = -0.46; kalca.add(diz);
        this.kutu(0.17, 0.42, 0.19, koyu, 0, -0.21, 0, diz);
        this.kutu(0.19, 0.08, 0.3, '#1b1a19', 0, -0.42, 0.05, diz);
        return { kalca, diz };
      };
      const sol = bacak(-1), sag = bacak(1);
      this.kutu(0.56, 0.64, 0.31, c.ceket, 0, 1.22, 0, govde);
      this.kutu(0.6, 0.12, 0.33, c.ceket, 0, 1.48, 0, govde);
      this.kutu(0.2, 0.28, 0.01, '#f5f3ef', 0, 1.39, 0.158, govde);
      this.kutu(0.1, 0.06, 0.02, c.kravat, 0, 1.5, 0.165, govde);
      this.kutu(0.075, 0.34, 0.015, c.kravat, 0, 1.3, 0.166, govde);
      const lp = (yon) => { const m = this.kutu(0.07, 0.3, 0.012, new T.Color(c.ceket).multiplyScalar(0.7).getStyle(), yon * 0.12, 1.37, 0.162, govde); m.rotation.z = yon * 0.32; };
      lp(-1); lp(1);
      this.kutu(0.08, 0.04, 0.012, '#f5f3ef', -0.17, 1.42, 0.16, govde);
      const kol = (yon) => {
        const om = new T.Group(); om.position.set(yon * 0.35, 1.47, 0); govde.add(om);
        this.kutu(0.14, 0.56, 0.17, c.ceket, 0, -0.28, 0, om);
        this.kutu(0.13, 0.05, 0.15, '#f5f3ef', 0, -0.57, 0, om);
        const el = new T.Mesh(new T.SphereGeometry(0.07, 12, 10), this.mat(c.ten)); el.position.y = -0.63; el.castShadow = true; om.add(el);
        return om;
      };
      const kolS = kol(-1), kolR = kol(1);
      this.silindir(0.07, 0.08, 0.1, c.ten, 0, 1.58, 0, govde);
      const bas = new T.Mesh(new T.SphereGeometry(0.19, 20, 16), this.mat(c.ten)); bas.position.y = 1.8; bas.castShadow = true; govde.add(bas);
      const sac = new T.Mesh(new T.SphereGeometry(0.205, 20, 12, 0, Math.PI * 2, 0, Math.PI * 0.55), this.mat(c.sac)); sac.position.set(0, 1.82, -0.02); sac.rotation.x = -0.35; sac.castShadow = true; govde.add(sac);
      [-0.07, 0.07].forEach((x) => { const g2 = new T.Mesh(new T.SphereGeometry(0.022, 8, 6), this.mat('#1a1410')); g2.position.set(x, 1.8, 0.175); govde.add(g2); });
      const evrak = this.kutu(0.24, 0.02, 0.32, '#ffffff', 0, -0.66, 0.12, kolR); evrak.visible = false;
      const halka = new T.Mesh(new T.RingGeometry(0.45, 0.55, 40), new T.MeshBasicMaterial({ color: '#c9962f', transparent: true, opacity: 0.9 }));
      halka.rotation.x = -Math.PI / 2; halka.position.y = 0.02; halka.visible = false; g.add(halka);
      g.traverse((o) => { o.userData.secim = k; });
      return { g, govde, sol, sag, kolS, kolR, evrak, halka };
    }

    ajanEkle(k) {
      const p = this.insan(k);
      const bas = k === 'denetci' ? { x: 0, z: HOL, sz: HOL } : N.seat(k);
      p.g.position.set(bas.x, 0, bas.z);
      this.sahne.add(p.g);
      this.ajan[k] = Object.assign(p, { key: k, loc: bas, yol: [], oturuyor: !!bas.oturur, sitT: bas.oturur ? 1 : 0, yaw: 0, yawHedef: 0, faz: Math.random() * 6, cmd: 0, varis: null, calisiyor: k !== 'denetci', balonBitis: 0, t0: Math.random() * 10 });
    }

    etiketler() {
      const mk = (html) => { const d = document.createElement('div'); d.style.cssText = 'position:absolute;left:0;top:0;will-change:transform;'; d.innerHTML = html; this.katman.appendChild(d); return d; };
      const pill = "display:flex;align-items:center;gap:6px;white-space:nowrap;font-size:11px;font-weight:600;color:#1c1a17;background:#ffffff;border:1px solid #e3dfd6;border-radius:999px;padding:3px 9px 3px 7px;box-shadow:0 1px 3px rgba(28,26,23,.08);transition:border-color .2s, box-shadow .2s;";
      Object.keys(this.ajan).forEach((k) => {
        const a = this.ajan[k];
        a.etiket = mk('<div style="position:relative;transform:translate(-50%,-100%);"><div data-b style="position:absolute;left:50%;bottom:calc(100% + 8px);transform:translateX(-50%) translateY(4px);opacity:0;transition:opacity .25s, transform .25s;white-space:nowrap;font-size:12px;font-weight:500;color:#ffffff;background:#1c1a17;border-radius:8px;padding:6px 10px;box-shadow:0 6px 18px rgba(28,26,23,.18);max-width:260px;overflow:hidden;text-overflow:ellipsis;"></div><div data-p style="' + pill + '"><span style="width:7px;height:7px;border-radius:50%;background:' + KISI[k].kravat + '"></span>' + KISI[k].ad + '</div></div>');
        a.balonEl = a.etiket.querySelector('[data-b]'); a.pillEl = a.etiket.querySelector('[data-p]');
        if (KISI[k].ekip) a.pillEl.style.visibility = 'hidden';
      });
      const yazi = "transform:translate(-50%,-50%);white-space:nowrap;font-size:10px;font-weight:600;letter-spacing:.12em;color:#9a9387;";
      const bosYazi = "transform:translate(-50%,-50%);white-space:nowrap;font-size:11px;font-weight:500;color:#8f6212;border:1px dashed #c9962f;background:#fffaf0;border-radius:999px;padding:3px 9px;";
      const zilYazi = "transform:translate(-50%,-100%);white-space:nowrap;font-size:11px;font-weight:600;letter-spacing:.06em;color:#8f6212;background:#fffaf0;border:1px solid #e9d3a6;border-radius:999px;padding:3px 9px;";
      const liste = [
        { x: 0, y: 0.05, z: -6.95, t: 'CEO ODASI' },
        { x: -10.2, y: 0.05, z: -8.6, t: 'KAHVE' },
        { x: 0, y: 0.05, z: 13.35, t: 'KURUL MASASI' },
        { x: 0, y: 0.05, z: 23.2, t: 'SATIŞ EKİBİ · 20 KİŞİ' },
        { x: ZIL.x + 0.4, y: 2.15, z: ZIL.z, t: 'ZİL', zil: true }
      ];
      Object.keys(YER).forEach((k) => {
        const R = ODA[YER[k]], bos = k.indexOf('bos') === 0;
        if (bos) liste.push({ x: R.cx + R.side * 1.6, y: 0.05, z: R.zc - 1.25, t: '+ Boş oda', bos: true });
      });
      this.sabit = liste.map((o) => Object.assign(o, { el: mk('<div style="' + (o.zil ? zilYazi : o.bos ? bosYazi : yazi) + '">' + o.t + '</div>') }));
      this.zilEl = this.sabit.find((o) => o.zil).el;
    }

    boyut() {
      const T = this.T, w = this.clientWidth || 800, h = this.clientHeight || 500;
      this.renderer.setSize(w, h, false);
      const cam = this.kamera; cam.updateMatrixWorld();
      const inv = cam.matrixWorldInverse, v = new T.Vector3();
      let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
      [-12, 12].forEach((x) => [-0.42, 2.5].forEach((y) => [-10.7, 23.8].forEach((z) => {
        v.set(x, y, z).applyMatrix4(inv); x0 = Math.min(x0, v.x); x1 = Math.max(x1, v.x); y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y);
      })));
      y1 += 1.1; x0 -= 0.2; x1 += 0.2; y0 -= 0.2;
      const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, asp = w / h;
      let hw = (x1 - x0) / 2, hh = (y1 - y0) / 2;
      if (hw / hh > asp) hh = hw / asp; else hw = hh * asp;
      hw /= 1.2; hh /= 1.2;
      Object.assign(cam, { left: cx - hw, right: cx + hw, top: cy + hh, bottom: cy - hh });
      cam.updateProjectionMatrix();
      this.W = w; this.H = h;
    }

    bolge(x, z) {
      if (z > 13.9) { x = cl(x, -10.9, 11.0); const L = S_LANE.reduce((a, b) => (Math.abs(b - z) < Math.abs(a - z) ? b : a)); return { x, z: L, oda: 'satis', ek: [{ x: S_AISLE, z: L }] }; }
      if (z < -6.6 && Math.abs(x) < 3.6) {
        x = cl(x, -3.1, 3.1); z = cl(z, -9.5, -7.0);
        const yan = x >= 0 ? 2.4 : -2.4;
        return { x, z, oda: 'ceo', ek: z < -7.6 ? [{ x: yan, z: -7.0 }, { x: yan, z }] : null };
      }
      if (z < -5.2) { x = cl(x, -11.1, 11.1); z = cl(z, -9.2, -5.4); return { x, z, yol: [{ x, z: HOL }], sz: HOL }; }
      if (Math.abs(x) >= 3.2 && z < 10) {
        const sd = x < 0 ? -1 : 1, i = cl(Math.floor((z + 5.2) / 3.8), 0, 3), key = (sd < 0 ? 'L' : 'R') + i, R = ODA[key];
        x = sd * cl(Math.abs(x), 3.7, 10.5); z = cl(z, R.zc - 1.3, R.zc + 1.5);
        const lane = z > R.zc - 0.3 ? R.zc + 1.35 : R.zc - 1.3;
        return { x, z, oda: key, ek: [{ x: R.hub.x, z: lane }, { x, z: lane }] };
      }
      if (z >= 10) { x = cl(x, -11.0, 11.0); z = cl(z, 10.3, 13.3); return { x, z, yol: [{ x, z: LOBI }], sz: LOBI }; }
      x = cl(x, -2.7, 2.7); return { x, z, sz: z };
    }

    rota(f, t) {
      const p = [];
      if (f.oda && f.oda === t.oda) {
        p.push(...rev(f.ek), ODA[f.oda].hub);
      } else if (!f.oda && !t.oda && !f.yol && !t.yol) {
        // koridor içinde düz yürü
      } else {
        if (f.oda) { const R = ODA[f.oda]; p.push(...rev(f.ek), ...rev(R.yol), { x: 0, z: R.sz }); }
        else { p.push(...rev(f.yol), { x: 0, z: f.sz ?? f.z }); }
        if (t.oda) { const R = ODA[t.oda]; p.push({ x: 0, z: R.sz }, ...R.yol); }
        else { p.push({ x: 0, z: t.sz ?? t.z }, ...(t.yol || [])); }
      }
      if (t.ek) p.push(...t.ek);
      p.push({ x: t.x, z: t.z });
      return p;
    }
    yuru(a, hedef) {
      const id = ++a.cmd;
      const bas = a.yol.length || !a.loc ? this.bolge(a.g.position.x, a.g.position.z) : a.loc;
      a.oturuyor = false; a.hedef = hedef;
      a.yol = this.rota(bas, hedef);
      return new Promise((res) => { a.varis = () => { if (a.cmd === id) res(); }; });
    }

    olaylar() {
      const c = this.renderer.domElement;
      const ndc = (e) => { const r = c.getBoundingClientRect(); return new this.T.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1); };
      const bul = (e) => {
        this.ray.setFromCamera(ndc(e), this.kamera);
        const hedefler = Object.values(this.ajan).map((a) => a.g).concat(this._secimHedef);
        const hit = this.ray.intersectObjects(hedefler, true)[0];
        return hit ? hit.object.userData.secim : null;
      };
      let bas = null;
      c.addEventListener('pointerdown', (e) => { bas = { x: e.clientX, y: e.clientY }; });
      c.addEventListener('pointermove', (e) => { if (this._hv && performance.now() - this._hv < 60) return; this._hv = performance.now(); c.style.cursor = bul(e) ? 'pointer' : (this.secili && this.secili !== 'bos' ? 'crosshair' : 'default'); });
      c.addEventListener('pointerup', (e) => {
        if (!bas || Math.hypot(e.clientX - bas.x, e.clientY - bas.y) > 6) return;
        const k = bul(e);
        if (k) { this.sec(k); window.dispatchEvent(new CustomEvent('nove-sec', { detail: { key: k } })); return; }
        if (!this.secili || this.secili === 'bos' || this._akisAktif) return;
        this.ray.setFromCamera(ndc(e), this.kamera);
        const p = new this.T.Vector3();
        if (!this.ray.ray.intersectPlane(this.zemin, p)) return;
        const a = this.ajan[this.secili];
        if (a.key === 'denetci') this._devId++;
        a.mesgul = false;
        this.yuru(a, this.bolge(p.x, p.z));
      });
    }

    sec(k) {
      this.secili = k;
      Object.values(this.ajan).forEach((a) => {
        const on = a.key === k; a.halka.visible = on;
        a.pillEl.style.borderColor = on ? '#c9962f' : '#e3dfd6';
        a.pillEl.style.boxShadow = on ? '0 0 0 3px rgba(201,150,47,.22)' : '0 1px 3px rgba(28,26,23,.08)';
      });
    }
    balon(k, metin, ms) {
      const a = this.ajan[k]; if (!a) return;
      a.balonEl.textContent = metin;
      a.balonEl.style.opacity = '1'; a.balonEl.style.transform = 'translateX(-50%) translateY(0)';
      a.balonBitis = performance.now() + (ms || 2800);
    }

    async devriye() {
      const a = this.ajan.denetci;
      this._devId = (this._devId || 0) + 1;
      const myId = this._devId;
      let i = a._wpi || 0;
      while (this._devId === myId && this.isConnected) {
        const w = DEVRIYE[i % DEVRIYE.length];
        await this.yuru(a, w);
        if (this._devId !== myId) return;
        if (w.yuz !== undefined) a.yawHedef = w.yuz;
        await bekle(w.dur);
        i++; a._wpi = i;
      }
    }
    gezinti() {
      if (this._akisAktif) return;
      const liste = ['finans', 'kalite', 'okr', 'rapor'].map((k) => this.ajan[k]);
      if (liste.some((a) => a.mesgul)) return;
      const aday = liste.filter((a) => a.oturuyor && this.secili !== a.key);
      if (!aday.length) return;
      const a = aday[Math.floor(Math.random() * aday.length)];
      a.mesgul = true;
      const id = a.cmd + 1;
      this.yuru(a, N.kahve())
        .then(() => { this.balon(a.key, 'Kahve molası', 2000); return bekle(2600); })
        .then(() => (a.cmd === id ? this.yuru(a, N.seat(a.key)) : null))
        .then(() => { a.mesgul = false; });
    }
    komut(d) {
      if (!d) return;
      const a = this.ajan[d.key]; if (!a) return;
      if (d.cmd === 'masa') { a.mesgul = false; if (a.key === 'denetci') this.devriye(); else this.yuru(a, N.seat(a.key)); }
    }

    async akis(d) {
      if (!d) return;
      const A = this.ajan, D = A[d.dept], dk = d.dept;
      const kisa = { finans: 'Finans', kalite: 'Kalite', okr: 'OKR', rapor: 'Raporlama', satisMuduru: 'Satış' }[dk] || '';
      this._akisAktif = true;
      const oturt = (a) => { a.mesgul = false; return a.oturuyor ? Promise.resolve() : this.yuru(a, N.seat(a.key)); };
      try {
        switch (d.tip) {
          case 'qa_al':
            await oturt(A.qa);
            this.balon('qa', 'Kurul sorusu alındı', 2400);
            await bekle(1500);
            break;
          case 'dagit':
            A.qa.evrak.visible = true; this.balon('qa', 'Dağıtıma götürüyor', 2400);
            await this.yuru(A.qa, N.ziyaret('dagitici'));
            A.qa.evrak.visible = false;
            this.balon('dagitici', '→ ' + (dk === 'satisMuduru' ? 'Satış Müdürü' : kisa + ' Danışmanı'), 2600);
            await bekle(1100);
            this.yuru(A.qa, N.seat('qa'));
            break;
          case 'analiz':
            A.dagitici.evrak.visible = true;
            await Promise.all([this.yuru(A.dagitici, N.ziyaret(dk)), oturt(D)]);
            A.dagitici.evrak.visible = false;
            this.balon('dagitici', 'Kurul bunu soruyor', 2000);
            await bekle(900);
            this.balon(dk, 'Analiz ediliyor…', 3200);
            D.hizli = true;
            this.yuru(A.dagitici, N.seat('dagitici'));
            await bekle(1300);
            break;
          case 'denetim':
            this._devId++;
            await this.yuru(A.denetci, N.ziyaretSol(dk));
            this.balon('denetci', 'Kaynaklar kontrol ediliyor', 2400);
            await bekle(1700);
            this.balon('denetci', 'Doğrulandı ✓', 1600);
            await bekle(700);
            this.devriye();
            break;
          case 'ceo_sorgu':
            D.hizli = false; D.evrak.visible = true;
            this.balon(dk, "CEO'ya sunuyor", 2200);
            await this.yuru(D, N.ziyaret('ceo'));
            this.balon('ceo', d.metin || 'Bunu sorgulamam gerek.', 3200);
            await bekle(2400);
            break;
          case 'revize':
            await this.yuru(D, N.seat(dk));
            D.evrak.visible = false; D.hizli = true;
            this.balon(dk, 'Revize ediliyor…', 2400);
            await bekle(1500);
            break;
          case 'ceo_onay':
            D.hizli = false; D.evrak.visible = true;
            await this.yuru(D, N.ziyaret('ceo'));
            D.evrak.visible = false;
            this.balon('ceo', 'Onaylandı ✓', 2400);
            await bekle(1300);
            this.yuru(D, N.seat(dk));
            break;
          case 'qa_ilet':
            A.qa.evrak.visible = true; this.balon('qa', 'Yanıt kurula gidiyor', 2200);
            await this.yuru(A.qa, N.kurul());
            A.qa.evrak.visible = false;
            this.balon('qa', 'Kurula iletildi ✓', 2400);
            await bekle(1200);
            this.yuru(A.qa, N.seat('qa'));
            this._akisAktif = false;
            break;
        }
      } catch (err) { console.warn(err); }
      window.dispatchEvent(new CustomEvent('nove-adim-bitti', { detail: { i: d.i, runId: d.runId } }));
    }

    kare() {
      const T = this.T;
      const dt = Math.min(this.saat.getDelta(), 0.05), now = performance.now(), t = now / 1000;
      const hiz = 3.1 * (this.hiz || 1);
      Object.values(this.ajan).forEach((a) => {
        const g = a.g;
        let yuruyor = false;
        if (a.yol.length) {
          const h = a.yol[0], dx = h.x - g.position.x, dz = h.z - g.position.z, d = Math.hypot(dx, dz);
          const adim = hiz * dt * (a.sitT > 0.05 ? 0.25 : 1);
          if (d <= adim + 0.001) { g.position.x = h.x; g.position.z = h.z; a.yol.shift(); }
          else { g.position.x += (dx / d) * adim; g.position.z += (dz / d) * adim; a.yawHedef = Math.atan2(dx, dz); yuruyor = true; }
          if (!a.yol.length) {
            const hd = a.hedef || {};
            a.loc = hd; a.oturuyor = !!hd.oturur;
            if (hd.oturur) a.yawHedef = 0; else if (hd.yuz !== undefined) a.yawHedef = hd.yuz;
            const f = a.varis; a.varis = null; if (f) f();
          }
        }
        a.sitT += ((a.oturuyor ? 1 : 0) - a.sitT) * Math.min(1, dt * 7);
        a.yaw = lerpA(a.yaw, a.yawHedef, Math.min(1, dt * 9));
        g.rotation.y = a.yaw;
        const s = a.sitT;
        if (yuruyor) a.faz += dt * hiz * 3.1;
        a.yuruW = (a.yuruW || 0) + ((yuruyor ? 1 : 0) - (a.yuruW || 0)) * Math.min(1, dt * 10);
        const sw = Math.sin(a.faz) * 0.55 * a.yuruW * (1 - s);
        a.sol.kalca.rotation.x = sw - Math.PI / 2 * s;
        a.sag.kalca.rotation.x = -sw - Math.PI / 2 * s;
        a.sol.diz.rotation.x = Math.max(0, Math.sin(a.faz + 1.2)) * 0.7 * a.yuruW * (1 - s) + Math.PI / 2 * s;
        a.sag.diz.rotation.x = Math.max(0, Math.sin(a.faz + 1.2 + Math.PI)) * 0.7 * a.yuruW * (1 - s) + Math.PI / 2 * s;
        const yaz = a.calisiyor && a.key !== 'ceo' ? Math.sin(t * (a.hizli ? 22 : 12) + a.t0) * 0.06 : 0;
        const tasi = a.evrak.visible ? -0.9 : 0;
        a.kolS.rotation.x = -sw * 0.8 * (tasi ? 0.3 : 1) + (-1.05 + yaz) * s;
        a.kolR.rotation.x = (tasi || sw * 0.8) * (1 - s) + (-1.05 - yaz) * s;
        a.govde.position.y = -0.4 * s + Math.abs(Math.sin(a.faz)) * 0.035 * a.yuruW * (1 - s) + Math.sin(t * 1.6 + a.t0) * 0.006;
        a.govde.position.z = 0.12 * s;
        if (a.balonBitis && now > a.balonBitis) { a.balonEl.style.opacity = '0'; a.balonEl.style.transform = 'translateX(-50%) translateY(4px)'; a.balonBitis = 0; }
      });
      if (this.zil) {
        const e = (now - (this._zilT || -1e9)) / 1000, d = Math.max(0, 1 - e / 1.4);
        this.zil.rotation.z = Math.sin(e * 26) * 0.6 * d;
        const on = e < 1.1; this.zilHalka.visible = on;
        if (on) { const sc = 1 + e * 3.2; this.zilHalka.scale.set(sc, sc, sc); this.zilHalka.material.opacity = 0.85 * (1 - e / 1.1); }
      }
      this.renderer.render(this.sahne, this.kamera);
      const v = new T.Vector3();
      const yerlestir = (el, x, y, z) => {
        v.set(x, y, z).project(this.kamera);
        el.style.transform = 'translate(' + ((v.x + 1) / 2 * this.W).toFixed(1) + 'px,' + ((1 - v.y) / 2 * this.H).toFixed(1) + 'px)';
      };
      Object.values(this.ajan).forEach((a) => yerlestir(a.etiket, a.g.position.x, 2.35 - 0.4 * a.sitT, a.g.position.z));
      this.sabit.forEach((o) => yerlestir(o.el, o.x, o.y, o.z));
    }
  }
  customElements.define('nove-ofis-4', NoveOfis4);
})();
