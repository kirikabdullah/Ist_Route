/* İst-Route · ortak motor (web: index.html, mobil: mobile.html)
   Veri, durum, GTFS ağ motoru, skorlama, arama. Arayüze özgü işler `hooks` üzerinden. */
const hooks = {onTripChanged(){}, render(){}, setSaat(){}, hemenCik(){}, setAile(){}};
/* ================= constants ================= */
const COL = {kirmizi:"#E30613", mavi:"#00A3E0", sari:"#FBB034"};
const KAT = {
  lokanta:{ad:"Kent Lokantaları", kisa:"Kent Lokantası", renk:"#F07A1A"},
  spor:{ad:"Spor Tesisleri", kisa:"Spor İstanbul", renk:"#7B3FE4"},
  muze:{ad:"Müzeler", kisa:"İBB Müzesi", renk:"#0B2545"},
  kopru:{ad:"Köprü trafiği", kisa:"Köprü", renk:"#E30613"},
  rail:{ad:"Raylı ağ", kisa:"Raylı sistem", renk:"#3E556F"}
};
const SCEN = D.senaryolar;
const SAATLER = Object.keys(SCEN.normal);
const PRESETS = [["08:00","Sabah zirve"],["13:00","Öğle"],["18:00","Akşam zirve"],["23:00","Gece"]];
const ZIRVE = [[480,570],[1020,1170]];
const BINIS = new Set(["metrobus","otobus","marmaray","metro","vapur","tramvay","funikuler","teleferik"]);
const UCRET = D.meta.ucret;
const KAPALI = D.meta.kapali_cevrim;
const SPEEDS = [1,2,4];
// Hava durumu: SİMÜLASYON (gerçek servis bağlı değil); senaryoyla tutarlı temsilî değerler
const WX = {
  normal:{t:16, ic:"cloud", d:"Parçalı bulutlu"},
  lodos:{t:14, ic:"rain", d:"Yağmurlu, kuvvetli lodos"},
  mac:{t:15, ic:"cloud", d:"Parçalı bulutlu"}
};

const ICO = {
  fork:'<path d="M7 2v7a2 2 0 0 0 2 2v11M9 2v5M5 2v5a2 2 0 0 0 2 2M17 2c-2 1.5-3 4-3 7h3v13"/>',
  dumbbell:'<path d="M6.5 6.5v11M17.5 6.5v11M3 9.5v5M21 9.5v5M6.5 12h11"/>',
  museum:'<path d="M3 21h18M4 10h16M12 3 3 8h18zM6 10v8M10 10v8M14 10v8M18 10v8"/>',
  yurume:'<circle cx="13" cy="4" r="2"/><path d="m9 21 3-7 3 3v4M7 12l3-4 4 1 2 4M10 8l-1 5"/>',
  metrobus:'<rect x="4" y="3" width="16" height="15" rx="3"/><path d="M4 11h16M8 21l1-3M16 21l-1-3"/><circle cx="8" cy="14.5" r=".6"/><circle cx="16" cy="14.5" r=".6"/>',
  otobus:'<rect x="5" y="3" width="14" height="15" rx="2.5"/><path d="M5 10h14M9 21v-3M15 21v-3"/>',
  marmaray:'<rect x="5" y="3" width="14" height="14" rx="4"/><path d="M5 11h14M8 21l2-4M16 21l-2-4"/><circle cx="9" cy="14" r=".6"/><circle cx="15" cy="14" r=".6"/>',
  metro:'<rect x="5" y="3" width="14" height="14" rx="4"/><path d="m9 13 3-6 3 6M8 21l2-4M16 21l-2-4"/>',
  vapur:'<path d="M3 17c2 2 4 2 6 0 2 2 4 2 6 0 2 2 4 2 6 0M5 14l1-5h12l1 5M9 9V5h6v4"/>',
  mola:'<path d="M17 8h1a3 3 0 0 1 0 6h-1M3 8h14v7a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4zM7 2v3M11 2v3"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon:'<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  road:'<path d="M4 20 8 4M20 20 16 4M12 6v2M12 11v2M12 16v2"/>',
  car:'<path d="M5 17h14M6 17v2M18 17v2M4 13l2-6h12l2 6v4H4z"/><circle cx="8" cy="14" r=".8"/><circle cx="16" cy="14" r=".8"/>',
  target:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
  star:'<path d="m12 3 2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z"/>',
  play:'<path d="M7 4v16l13-8z"/>',
  pause:'<path d="M7 4h4v16H7zM14 4h4v16h-4z"/>',
  reset:'<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5"/>',
  lock:'<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  family:'<circle cx="8" cy="7" r="3"/><circle cx="17" cy="9" r="2.4"/><path d="M2 21a6 6 0 0 1 12 0M13.5 21a4.5 4.5 0 0 1 9 0"/>',
  wind:'<path d="M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h8"/>',
  alert:'<path d="M12 3 2 21h20zM12 10v5M12 18v.5"/>',
  stadium:'<ellipse cx="12" cy="9" rx="9" ry="4"/><path d="M3 9v6c0 2.2 4 4 9 4s9-1.8 9-4V9"/>',
  cloud:'<path d="M7 18h10a4 4 0 0 0 .4-7.98A6 6 0 0 0 6 11a3.5 3.5 0 0 0 1 7z"/>',
  rain:'<path d="M7 15h10a4 4 0 0 0 .4-7.98A6 6 0 0 0 6 8a3.5 3.5 0 0 0 1 7zM8 18l-1 3M12 18l-1 3M16 18l-1 3"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  chev:'<path d="m6 9 6 6 6-6"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  swap:'<path d="M7 4v16M7 20l-3-3M7 20l3-3M17 20V4M17 4l-3 3M17 4l3 3"/>',
  spark:'<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
  tramvay:'<rect x="6" y="5" width="12" height="13" rx="3"/><path d="M6 12h12M9 2h6M12 2v3M8 21l1.5-3M16 21l-1.5-3"/>',
  funikuler:'<path d="M4 19 20 7M7 21l2-5h8l2 5M9 16V11h8v5"/>',
  pin:'<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
  minus:'<path d="M5 12h14"/>'
};
const svg = (k, s=16, sw=2, col="currentColor", fill="none", cls="") =>
  `<svg ${cls?`class="${cls}"`:""} width="${s}" height="${s}" viewBox="0 0 24 24" fill="${fill}" stroke="${col}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICO[k]}</svg>`;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const $ = id => document.getElementById(id);
const toMin = hhmm => { const [h,m] = hhmm.split(":").map(Number); return h*60+m; };
const fmt = m => { m = ((Math.round(m) % 1440) + 1440) % 1440; return String(Math.floor(m/60)).padStart(2,"0")+":"+String(m%60).padStart(2,"0"); };
const tl = v => v.toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2}) + " ₺";
const inPeak = m => ZIRVE.some(([a,b]) => m>=a && m<b);
// Raylı ve deniz hatları istasyon noktalarından gelir; Catmull-Rom ile yumuşatılır (OSRM yolları dokunulmaz).
function smooth(pts, n = 8){
  if(pts.length < 3) return pts;
  const out = [];
  for(let i = 0; i < pts.length - 1; i++){
    const p0 = pts[i-1] || pts[i], p1 = pts[i], p2 = pts[i+1], p3 = pts[i+2] || p2;
    for(let s = 0; s < n; s++){
      const t = s / n, t2 = t*t, t3 = t2*t;
      const f = k => .5 * ((2*p1[k]) + (-p0[k] + p2[k])*t + (2*p0[k] - 5*p1[k] + 4*p2[k] - p3[k])*t2 + (-p0[k] + 3*p1[k] - 3*p2[k] + p3[k])*t3);
      out.push([f(0), f(1)]);
    }
  }
  out.push(pts[pts.length-1]);
  return out;
}
Object.keys(D.geoms).forEach(k => { if(k.startsWith("s:")) D.geoms[k] = smooth(D.geoms[k]); });
const POI_BY_ID = Object.fromEntries(D.pois.map(p => [p.id, p]));
const KAT_SAY = D.pois.reduce((a,p) => (a[p.kat]=(a[p.kat]||0)+1, a), {});
const MOD_TR = {yurume:"Yürüme", metrobus:"Metrobüs", otobus:"Otobüs", marmaray:"Marmaray", metro:"Metro", vapur:"Vapur", mola:"Mola", tramvay:"Tramvay", funikuler:"Füniküler", teleferik:"Teleferik"};
ICO.teleferik = ICO.funikuler;

/* ================= state ================= */
const store = { get(k,d){ try{ const v = localStorage.getItem(k); return v===null?d:v; }catch(e){ return d; } },
                set(k,v){ try{ localStorage.setItem(k,v); }catch(e){} } };
const state = {
  saat: D.meta.varsayilan_saat || "18:00",
  kriz: "normal",
  aktif: null,                 // null => önerilen rotayı takip et
  kat: {lokanta:true, spor:true, muze:false, kopru:true, rail:true},
  tema: store.get("ist-tema","light"),
  mod: "bireysel",             // 'bireysel' | 'aile'
  puan: 150,
  bakiye: 120,
  pop: null,                   // açık balon: 'time' | 'wx' | 'menu' | 'score:<id>' | null
  // Faz B: dinamik yolculuk. key 'def-o'/'def-d' = kalibre örnek yolculuk (Python skor motoru)
  trip: {
    from: {ad:D.meta.origin.ad, alt:D.meta.origin.alt + " · örnek yolculuk", pt:D.meta.origin.pt, key:"def-o"},
    to:   {ad:D.meta.dest.ad,   alt:D.meta.dest.alt + " · örnek yolculuk",   pt:D.meta.dest.pt,   key:"def-d"}
  },
  zamanMod: "kalkis",          // 'kalkis' | 'varis'
  hedef: 19*60,                // varış modunda hedef varış (dk)
  speed: 1,
  aile: {
    master: {ad:"Ayşe Yılmaz", rol:"Ebeveyn · Ana Kart", bakiye: 750},
    esik: 20, yukleme: 100,
    uyeler: [
      // Çocuk renkleri sabit palet: rota renkleri (kırmızı/mavi/sarı), siyah (deniz kilidi) ve beyaz (aktarma) asla verilmez
      {id:"elif", ad:"Elif", rol:"Öğrenci · 14", tip:"ogrenci", bakiye: 22, oto:true, renk:"#FF6B00", hedefAd:"Taksim"},
      {id:"can",  ad:"Can",  rol:"Öğrenci · 9",  tip:"ogrenci", bakiye: 9,  oto:true, renk:"#8B5CF6", hedefAd:"Levent"}
    ],
    yolcu: "ben",
    log: []
  }
};
// C1: örnek yolculuk dahil her yolculuk gerçek veriyle (GTFS ağı) hesaplanır.
// Eski kalibre Python rotaları yalnızca GTFS verisi yoksa (yedek) kullanılır.
const isDefaultTrip = () => !D.net.gtfs && state.trip.from.key === "def-o" && state.trip.to.key === "def-d";
const stepAt = saat => isDefaultTrip() ? SCEN[state.kriz][saat] : netStep(saat);
const step = () => stepAt(state.saat);
const aktifRota = () => {
  const s = step();
  const r = s.rotalar.find(x => x.id === state.aktif);
  return (r && !r.iptal) ? r : s.rotalar.find(x => x.id === s.oneri);
};
const varis = r => fmt(toMin(state.saat) + r.sure + r.mola);

/* ================= Faz B: ana hat ağı motoru =================
   Örnek yolculuk dışındaki her yolculuk burada hesaplanır. Ağ (network.py) yaklaşık
   konum + tahminî sürelerdir; skor formülü ve kurallar scoring_engine.py ile aynıdır. */
const NET = D.net, N = NET.nodes, LINES = NET.lines;
const ADJ = N.map(() => []);
NET.edges.forEach(([a,b,dk,kind,line,kopru,via]) => ADJ[a].push({a, b, dk, kind, line, kopru, via}));
const O_ID = N.length, T_ID = N.length + 1;
const hav = (a, b) => { const R = 6371000, r = Math.PI/180, dp = (b[0]-a[0])*r, dl = (b[1]-a[1])*r;
  const h = Math.sin(dp/2)**2 + Math.cos(a[0]*r)*Math.cos(b[0]*r)*Math.sin(dl/2)**2; return 2*R*Math.asin(Math.sqrt(h)); };
const W_M_DK = 78, MOLA_DK = D.meta.mola_dk || 45, SON_KABUL = 30;
const UYUM = {lokanta:1, spor:1, muze:.6};
const KALABALIK = {metrobus:.8, marmaray:.7, metro:.6, tramvay:.6, funikuler:.4, teleferik:.3, vapur:.15, otobus:.7};
// Boğaz orta hattı (enlem -> boylam), Avrupa/Asya ayrımı ve araç kıyası için
const BOGAZ = [[40.90,28.99],[41.00,29.000],[41.02,29.005],[41.04,29.020],[41.05,29.035],[41.07,29.050],[41.09,29.060],[41.12,29.070],[41.25,29.080]];
function asyada(pt){
  let lon = BOGAZ[BOGAZ.length-1][1];
  for(let i = 1; i < BOGAZ.length; i++){ const [a, b] = [BOGAZ[i-1], BOGAZ[i]];
    if(pt[0] <= b[0]){ const t = Math.max(0, Math.min(1, (pt[0]-a[0])/(b[0]-a[0]))); lon = a[1] + (b[1]-a[1])*t; break; } }
  return pt[1] > lon;
}
const zirvede = m => inPeak(m);
const ortusme = (bas, son) => son <= bas ? 0 : ZIRVE.reduce((s,[a,b]) => s + Math.max(0, Math.min(son,b) - Math.max(bas,a)), 0) / (son - bas);
function saatAraligi(p){ const m = /(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})/.exec(p.saat_metin || ""); return m ? [+m[1]*60 + +m[2], +m[3]*60 + +m[4]] : [0, 1440]; }
const acikMi = (p, bas, sure) => { const [a, b] = saatAraligi(p); return a <= bas && bas + Math.min(sure, SON_KABUL) <= b; };
function baglanti(pt, p){ const d = hav(pt, [p.lat, p.lon]) * 1.3;
  return d <= 910 ? ["yurume", Math.max(2, Math.round(d / W_M_DK))] : ["otobus", Math.round(3 + d / 350)]; }

// Kalkış/varış -> ağ bağlantıları (yolculuk ve çocuk rotaları ortak kullanır; noktalara göre önbellekli)
const connMap = new Map();
function connectors(f = state.trip.from, t = state.trip.to){
  const key = f.pt + "|" + t.pt;
  if(connMap.has(key)) return connMap.get(key);
  const near = (pt, maxM) => N.map((n, i) => [i, hav(pt, n.pt)]).filter(([, d]) => d <= maxM).sort((a, b) => a[1] - b[1]);
  const mk = (pt, list, toNode) => {
    let res = list.slice(0, 12), bus = false;
    if(!res.length){ res = N.map((n, i) => [i, hav(pt, n.pt)]).sort((a, b) => a[1] - b[1]).slice(0, 3); bus = true; }
    return res.map(([i, d]) => {
      const dk = bus ? Math.round(5 + d * 1.4 / 250) : Math.max(1, Math.round(d * 1.3 / W_M_DK));
      return toNode
        ? {a:O_ID, b:i, dk: dk + N[i].bekleme, kind:"baglanti", mod: bus ? "otobus" : "yurume", pa:pt, pb:N[i].pt, label:`${N[i].ad} durağına ${bus ? "otobüs" : "yürü"} (bekleme dahil)`}
        : {a:i, b:T_ID, dk, kind:"baglanti", mod: bus ? "otobus" : "yurume", pa:N[i].pt, pb:pt, label:`${t.ad} · ${bus ? "otobüs" : "yürü"}`};
    });
  };
  const fromO = mk(f.pt, near(f.pt, 1600), true);
  const toT = new Map(); mk(t.pt, near(t.pt, 1600), false).forEach(e => toT.set(e.a, e));
  const dd = hav(f.pt, t.pt);
  if(dd <= 2200) fromO.push({a:O_ID, b:T_ID, dk:Math.max(2, Math.round(dd * 1.3 / W_M_DK)), kind:"baglanti", mod:"yurume", pa:f.pt, pb:t.pt, label:`${t.ad} · yürüyerek`});
  const res = {key, fromO, toT, dd};
  connMap.set(key, res);
  return res;
}
// Aile Modu: çocuğun evden (seçili kalkış) hedef durağına en hızlı rotası
const kidCache = new Map();
function kidRoute(u){
  if(!u.hedef) return null;
  const from = state.trip.from, key = from.pt + "|" + u.hedef.pt + "|" + state.kriz + "|" + state.saat;
  if(kidCache.has(key)) return kidCache.get(key);
  const c = SCEN.normal[state.saat].trafik.cong, lodos = state.kriz === "lodos";
  const conn = connectors(from, {ad:u.hedef.ad, pt:u.hedef.pt});
  const path = dijkstra(conn,
    e => e.kind === "hat" ? e.dk * (LINES[e.line].mod === "metrobus" ? 1 + .25 * c : 1) : e.dk + (e.kind === "aktarma" ? 2 : 0),
    e => !(lodos && e.kind === "hat" && LINES[e.line].mod === "vapur"));
  const res = path ? (() => { const {legs} = toLegs(path, c, false); return {legs, sure:legs.reduce((s, l) => s + l.dk, 0), ozet:routeMeta(legs).ozet}; })() : null;
  kidCache.set(key, res);
  return res;
}
// İkili yığınlı Dijkstra (GTFS ağı ~1500 düğüm; varış modu 36 saat × 4 arama yapar)
function dijkstra(conn, cost, allow){
  const V = N.length + 2, dist = new Float64Array(V).fill(Infinity), prev = new Array(V).fill(null), done = new Uint8Array(V);
  const hk = [], hv = [];
  const push = (k, v) => { hk.push(k); hv.push(v); let i = hk.length - 1;
    while(i > 0){ const p = (i - 1) >> 1; if(hk[p] <= hk[i]) break; [hk[p], hk[i]] = [hk[i], hk[p]]; [hv[p], hv[i]] = [hv[i], hv[p]]; i = p; } };
  const pop = () => { const v = hv[0], lk = hk.pop(), lv = hv.pop();
    if(hk.length){ hk[0] = lk; hv[0] = lv; let i = 0;
      for(;;){ const l = 2*i + 1, r = l + 1; let m = i;
        if(l < hk.length && hk[l] < hk[m]) m = l; if(r < hk.length && hk[r] < hk[m]) m = r;
        if(m === i) break; [hk[m], hk[i]] = [hk[i], hk[m]]; [hv[m], hv[i]] = [hv[i], hv[m]]; i = m; } }
    return v; };
  dist[O_ID] = 0; push(0, O_ID);
  while(hk.length){
    const u = pop();
    if(done[u]) continue;
    done[u] = 1;
    if(u === T_ID) break;
    const outs = u === O_ID ? conn.fromO : ADJ[u].filter(allow).concat(conn.toT.has(u) ? [conn.toT.get(u)] : []);
    for(const e of outs){ const nd = dist[u] + cost(e); if(nd < dist[e.b]){ dist[e.b] = nd; prev[e.b] = e; push(nd, e.b); } }
  }
  if(!prev[T_ID]) return null;
  const path = []; let v = T_ID;
  while(v !== O_ID){ const e = prev[v]; path.unshift(e); v = e.a; }
  return path;
}
let geoSeq = 0;
// Yalnızca seyrek (birkaç noktalı) hatlar yumuşatılır; GTFS shapes zaten gerçek güzergâhtır
function geoKey(pts, smoothIt){ const k = "n:" + (geoSeq++); D.geoms[k] = smoothIt && pts.length < 12 ? smooth(pts) : pts; return k; }
const LINE_KISA = id => LINES[id].kisa || MOD_TR[LINES[id].mod] || id;
// Kenar listesi -> Python ile aynı biçimde bacaklar ({mod, ad, dk, g})
function toLegs(path, c, macOn){
  const raw = []; let cur = null, sogut = false;
  for(const e of path){
    if(e.kind === "hat"){
      const ln = LINES[e.line], dk = e.dk * (ln.mod === "metrobus" ? 1 + .25 * c : 1);
      if(cur && cur.line === e.line){ cur.dk += dk; cur.to = N[e.b].ad; cur.pts.push(...(e.via || []), N[e.b].pt); cur.kopru ||= e.kopru; }
      else { cur = {ride:true, line:e.line, mod:ln.mod, from:N[e.a].ad, to:N[e.b].ad, dk, pts:[N[e.a].pt, ...(e.via || []), N[e.b].pt], kopru:!!e.kopru}; raw.push(cur); }
    } else {
      cur = null;
      let dk = e.dk;
      const into = e.b < N.length ? N[e.b].ad : "";
      if(macOn && into === "Söğütlüçeşme"){ dk += 6; sogut = true; }
      const pa = e.pa || N[e.a].pt, pb = e.pb || N[e.b].pt;
      const label = e.kind === "aktarma" ? `Aktarma · ${into} (${LINE_KISA(N[e.b].line)}, bekleme dahil)` : e.label;
      const last = raw[raw.length - 1];
      if(last && !last.ride && last.mod === (e.mod || "yurume")){ last.dk += dk; last.pts.push(pb); last.label = label; }
      else raw.push({ride:false, mod:e.mod || "yurume", dk, pts:[pa, pb], label});
    }
  }
  const legs = raw.map(r => r.ride
    ? {mod:r.mod, ad:`${LINES[r.line].ad} · ${r.from} → ${r.to}`, dk:Math.max(1, Math.round(r.dk)), g:geoKey(r.pts, true), _kopru:r.kopru, _line:r.line, _to:r.to}
    : {mod:r.mod, ad:r.label, dk:Math.max(1, Math.round(r.dk)), g:geoKey(r.pts, false)});
  return {legs, sogut};
}
function routeMeta(legs){
  const rides = legs.filter(l => l._line);
  const names = [...new Set(rides.map(l => LINE_KISA(l._line)))];
  const rideMin = rides.reduce((s, l) => s + l.dk, 0) || 1;
  return {
    ozet: names.length ? names.join(" + ") : "Yürüyüş",
    aktarma: Math.max(0, rides.length - 1),
    yurume_dk: legs.filter(l => l.mod === "yurume").reduce((s, l) => s + l.dk, 0),
    kalabalik: rides.reduce((s, l) => s + (KALABALIK[l.mod] ?? .5) * l.dk, 0) / rideMin,
    kopru_kullanim: rides.some(l => l._kopru) ? .6 : 0,
    vapur: rides.some(l => l.mod === "vapur")
  };
}
function skorlaJS(rs, c, dk){
  rs.forEach(r => { r.sure = r.legs.filter(l => l.mod !== "mola").reduce((s, l) => s + l.dk, 0); r.t_eff = r.sure + .25 * r.mola; });
  const tmin = Math.min(...rs.filter(r => !r.iptal).map(r => r.t_eff));
  rs.forEach(r => {
    const zaman = tmin / r.t_eff, aktarma = 1 / (1 + .5 * r.aktarma);
    const yur = Math.max(0, 1 - r.yurume_dk / 45) * (r.sahil ? 1.15 : 1);
    const konfor = .6 * Math.min(1, yur) + .4 * (1 - r.kalabalik * c);
    const s_ind = 100 * (.55 * zaman + .2 * aktarma + .25 * konfor);
    const kacinma = 1 - r.kopru_kullanim * c;
    const dagitma = r.mola ? ortusme(r.mola_bas, r.mola_bas + r.mola) * UYUM[r.mola_kat] : (r.id === "konforlu" && r.sahil && zirvede(dk) ? .4 : 0);
    const tesvik = Math.min(1, r.puan / 25);
    const s_soc = 100 * (.4 * kacinma + .35 * dagitma + .25 * tesvik);
    Object.assign(r, {s_ind:+s_ind.toFixed(1), s_soc:+s_soc.toFixed(1), skor:+(.55 * s_ind + .45 * s_soc).toFixed(1),
      bilesen:{zaman, aktarma, konfor, kacinma, dagitma, tesvik}});
  });
}
const netCache = new Map();
function netStep(saat){
  const key = state.trip.from.pt + "|" + state.trip.to.pt + "|" + state.kriz + "|" + saat;
  if(netCache.has(key)) return netCache.get(key);
  const base = SCEN[state.kriz][saat], tr = SCEN.normal[saat].trafik, c = tr.cong, dk = toMin(saat);
  const conn = connectors();
  const lodos = state.kriz === "lodos", macOn = state.kriz === "mac" && base.kriz_aktif;
  const modOf = e => e.kind === "hat" ? LINES[e.line].mod : null;
  const allow = e => !(lodos && modOf(e) === "vapur");
  const extra = e => (macOn && e.b < N.length && N[e.b].ad === "Söğütlüçeşme" && e.kind !== "hat") ? 6 : 0;
  const tHiz = e => e.kind === "hat" ? e.dk * (modOf(e) === "metrobus" ? 1 + .25 * c : 1) : e.dk + (e.kind === "aktarma" ? 2 : 0) + extra(e);
  // Konforlu: kalabalık hatları ve aktarmayı belirgin cezalandırır, deniz yolunu tercih eder
  const CROWD = {metrobus:1 + 1.2 * c, marmaray:1 + .4 * c, metro:1 + .3 * c, tramvay:1.2, funikuler:1, teleferik:1, vapur:.4};
  const tKonfor = e => e.kind === "hat" ? e.dk * (CROWD[modOf(e)] || 1) : e.dk * 1.2 + (e.kind === "aktarma" ? 10 : 0) + extra(e);
  const tSosyal = e => tHiz(e) + (e.kopru ? 20 * c : 0);

  const pH = dijkstra(conn, tHiz, allow), pK = dijkstra(conn, tKonfor, allow), pS = dijkstra(conn, tSosyal, allow);
  if(!pH){ const empty = {trafik:tr, zirve:zirvede(dk), rotalar:[], oneri:null, kriz_aktif:base.kriz_aktif, bos:true}; netCache.set(key, empty); return empty; }

  const mk = (id, path, extraProps) => {
    const {legs, sogut} = toLegs(path, c, macOn), m = routeMeta(legs);
    const r = {id, legs, ...m, mola:0, mola_poi:null, puan:0, iptal:false, uyari:null, sahil:false, ...extraProps(m)};
    if(sogut) r.uyari = "Söğütlüçeşme'de derbi kalabalığı · ek bekleme";
    return r;
  };
  // "Hızlı" her zaman gerçek süresi en kısa yoldur (aktarma cezası daha kısa bir yolu gizlemesin)
  const sureOf = p => toLegs(p, c, macOn).legs.reduce((s, l) => s + l.dk, 0);
  const pFast = pK && sureOf(pK) < sureOf(pH) ? pK : pH;
  const hizli = mk("hizli", pFast, () => ({renk:"kirmizi", ikon:"⚡", tip:"Hızlı · Ekspres", alt:"En kısa toplam süre"}));
  const konforlu = mk("konforlu", pK || pH, m => ({renk:"mavi", ikon:"🛋️", tip:"Konforlu & Dengeli", sahil:m.vapur,
    kalabalik:m.kalabalik * .8, puan: m.vapur ? (zirvede(dk) ? 10 : 5) : 0,
    alt: m.vapur ? "0 trafik stresi, deniz yolu" : (lodos ? "Lodos: vapur yerine sakin raylı hatlar" : "Daha sakin hatlar, az aktarma")}));
  const ayni = (a, b) => JSON.stringify(a.legs.map(l => l.ad)) === JSON.stringify(b.legs.map(l => l.ad));
  let kRoute = konforlu;
  if(ayni(konforlu, hizli)){
    // Hızlı'nın hatlarını cezalandırarak gerçek bir alternatif ara; makul süredeyse kullan
    const used = new Set(hizli.legs.filter(l => l._line).map(l => l._line));
    const pAlt = dijkstra(conn, e => tKonfor(e) * (e.kind === "hat" && used.has(e.line) ? 1.8 : 1), allow);
    if(pAlt){
      const alt = mk("konforlu", pAlt, m => ({renk:"mavi", ikon:"🛋️", tip:"Konforlu & Dengeli", sahil:m.vapur,
        kalabalik:m.kalabalik * .8, puan: m.vapur ? (zirvede(dk) ? 10 : 5) : 0,
        alt: m.vapur ? "0 trafik stresi, deniz yolu" : "Alternatif hat: daha sakin, farklı aktarma"}));
      const sure = r => r.legs.reduce((s, l) => s + l.dk, 0);
      const kCost = p => p.reduce((s, e) => s + tKonfor(e), 0);
      // Yalnızca gerçekten sakin bir alternatifse kabul: konfor maliyeti en fazla %25 kötü, süre makul
      if(!ayni(alt, hizli) && sure(alt) <= sure(hizli) * 1.5 + 10 && kCost(pAlt) <= kCost(pK || pH) * 1.25) kRoute = alt;
    }
    if(kRoute === konforlu) konforlu.alt = "Hızlı rotayla aynı güzergâh";
  }
  // Alternatif aslında daha kısaysa roller değişir: kısa olan Hızlı, öbürü Konforlu
  const legSure = r => r.legs.reduce((s, l) => s + l.dk, 0);
  if(kRoute !== konforlu && legSure(kRoute) < legSure(hizli)){
    const eskiH = {...hizli};   // kopyayı değiştirmeden önce al
    Object.assign(hizli, {...kRoute, id:"hizli", renk:"kirmizi", ikon:"⚡", tip:"Hızlı · Ekspres", alt:"En kısa toplam süre", puan:0, sahil:false});
    kRoute = {...eskiH, id:"konforlu", renk:"mavi", ikon:"🛋️", tip:"Konforlu & Dengeli", alt:"Daha az aktarma, daha sakin hatlar"};
  }
  const sBase = mk("sosyal", pS || pH, () => ({renk:"sari", ikon:"🎁", tip:"Sosyal Mola"}));

  // Mola: sosyal yolun her hat bacağının bitiş istasyonunda, açık İBB noktası aranır (Python kuralı)
  const adaylar = [];
  let t = 0;
  sBase.legs.forEach((l, i) => {
    t += l.dk;
    if(!l._line) return;
    const nodePt = D.geoms[l.g][D.geoms[l.g].length - 1];
    D.pois.forEach(p => {
      if(hav(nodePt, [p.lat, p.lon]) > 1600) return;
      const [bm, w] = baglanti(nodePt, p);
      if(acikMi(p, dk + t + w, MOLA_DK)) adaylar.push({p, i, w, bm, nodePt, t, durak:l._to});
    });
  });
  let best = null, bestSet = null;
  const candList = adaylar.length ? adaylar : [null];
  for(const a of candList){
    let sos;
    if(!a){ sos = {...sBase, legs:sBase.legs.slice(), alt:"Bu saatte güzergâhta açık İBB noktası yok", ozet:sBase.ozet}; }
    else {
      const pp = [a.p.lat, a.p.lon], fiil = a.bm === "yurume" ? "yürü" : "kısa otobüs";
      const legs = [...sBase.legs.slice(0, a.i + 1),
        {mod:a.bm, ad:`${a.p.isim} · ${fiil}`, dk:a.w, g:geoKey([a.nodePt, pp], false)},
        {mod:"mola", ad:`Mola · ${a.p.isim}`, dk:MOLA_DK, g:null},
        {mod:a.bm, ad:`${a.durak} istasyonuna dön`, dk:a.w, g:geoKey([pp, a.nodePt], false)},
        ...sBase.legs.slice(a.i + 1)];
      sos = {...sBase, legs, mola:MOLA_DK, mola_poi:a.p.id, mola_kat:a.p.kat, mola_bas:dk + a.t + a.w, puan:a.p.odul_puani,
        dugum:a.durak, aktarma:sBase.aktarma + (a.bm === "yurume" ? 1 : 3),
        yurume_dk:sBase.yurume_dk + (a.bm === "yurume" ? 2 * a.w : 4), kalabalik:sBase.kalabalik * .6};
    }
    const set = [{...hizli}, {...kRoute}, sos];
    skorlaJS(set, c, dk);
    if(!best || set[2].skor > best.skor){ best = set[2]; bestSet = set; }
  }
  const rotalar = bestSet;
  const oneri = rotalar.filter(r => !r.iptal).reduce((a, b) => b.skor > a.skor ? b : a).id;
  // Araç kıyası: kuş uçuşu ×1.35, trafik yoğunluğuna göre hız; kıtalar arası ise köprü gecikmesi
  const cross = asyada(state.trip.from.pt) !== asyada(state.trip.to.pt);
  const arac = Math.round(5 + conn.dd / 1000 * 1.35 / (42 - 24 * c) * 60 + (cross ? 8 + 37 * c : 0));
  rotalar.forEach(r => { r.oneri = r.id === oneri; r.varis_dk = r.sure + r.mola; r.arac_fark = arac - r.varis_dk; });
  const res = {trafik:{...tr, arac_dk:arac}, zirve:zirvede(dk), rotalar, oneri, kriz_aktif:base.kriz_aktif, ag:true};
  netCache.set(key, res);
  return res;
}
function tripChanged(){ netCache.clear(); kidCache.clear(); state.aktif = null; hooks.onTripChanged(); }

/* ---------- arama dizini: istasyonlar, iskeleler, POI'ler + örnek yolculuk ---------- */
const norm = s => String(s).toLocaleLowerCase("tr").replace(/ı/g,"i").normalize("NFD").replace(/[̀-ͯ]/g,"");
const SEARCH = (() => {
  const byAd = new Map();
  N.forEach(n => {
    const lid = LINES[n.line].mod === "vapur" ? "Vapur" : LINE_KISA(n.line);
    if(!byAd.has(n.ad)) byAd.set(n.ad, {ad:n.ad, lines:new Set(), pt:n.pt, kind:n.mod === "vapur" ? "iskele" : "durak"});
    byAd.get(n.ad).lines.add(lid);
  });
  const items = [...byAd.values()].map(s => ({ad:s.ad, alt:[...s.lines].join(" · "), pt:s.pt, kind:s.kind, key:"st:" + s.ad}));
  D.pois.forEach(p => items.push({ad:p.isim, alt:`${KAT[p.kat].kisa} · ${p.ilce}`, pt:[p.lat, p.lon], kind:p.kat, key:"poi:" + p.id}));
  items.unshift({ad:D.meta.origin.ad, alt:D.meta.origin.alt + " · örnek yolculuk noktası", pt:D.meta.origin.pt, kind:"ornek", key:"def-o"},
                {ad:D.meta.dest.ad, alt:D.meta.dest.alt + " · örnek yolculuk noktası", pt:D.meta.dest.pt, kind:"ornek", key:"def-d"});
  items.forEach(it => it.n = norm(it.ad + " " + it.alt));
  return items;
})();
// Çocuk hedef seçicisi için durak/iskele listesi (alfabetik)
const DURAKLAR = SEARCH.filter(i => i.kind === "durak" || i.kind === "iskele").sort((a, b) => a.ad.localeCompare(b.ad, "tr"));
state.aile.uyeler.forEach(u => {
  u.hedef = DURAKLAR.find(d => d.ad === u.hedefAd) || DURAKLAR.find(d => d.ad.startsWith(u.hedefAd)) || DURAKLAR[0];
});
function searchItems(q){
  const nq = norm(q.trim());
  if(!nq) return SEARCH.filter(i => i.kind === "ornek" || i.kind === "iskele").slice(0, 8);
  const toks = nq.split(/\s+/);
  return SEARCH.map(i => {
    if(!toks.every(t => i.n.includes(t))) return null;
    const nad = norm(i.ad);
    return [i, nad.startsWith(nq) ? 0 : nad.split(/[\s\-·]+/).some(w => w.startsWith(toks[0])) ? 1 : 2];
  }).filter(Boolean).sort((a, b) => a[1] - b[1] || a[0].ad.length - b[0].ad.length).slice(0, 8).map(x => x[0]);
}

function traveler(){
  if(state.mod !== "aile" || state.aile.yolcu === "ben") return null;
  return state.aile.uyeler.find(u => u.id === state.aile.yolcu);
}
// Varış modunda: hedefe yetişen en geç kalkışı bul (önerilen rotaya göre)
function cikisBul(hedef){
  for(let i = SAATLER.length - 1; i >= 0; i--){
    const st = stepAt(SAATLER[i]), r = st.rotalar.find(x => x.id === st.oneri);
    if(r && toMin(SAATLER[i]) + r.sure + r.mola <= hedef) return SAATLER[i];
  }
  return null;
}
