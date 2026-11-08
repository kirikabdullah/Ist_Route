/* İst-Route Asistanı · kural tabanlı beyin (web + mobil ortak)
   Yanıtlar yalnızca uygulamanın verisinden kurulur; arayüz işleri `hooks` üzerinden. */
const RM = D.risk_model;
const ai = {open:false, msgs:[], seq:0, profile: RM ? {...RM.default_profile} : null, profOpen:false};
function riskOf(p){
  if(!RM || !p) return null;
  const x = RM.features.map((f, i) => {
    let v = p[f];
    if(RM.cat_cols.includes(f)){ const k = RM.classes[f].indexOf(String(v)); v = k < 0 ? 0 : k; }
    else if(RM.log1p.includes(f)) v = Math.log1p(Math.max(0, +v || 0));
    else v = +v || 0;
    return Math.min(1, Math.max(0, v * RM.scaler.scale[i] + RM.scaler.min[i]));
  });
  let h = x;
  RM.layers.forEach((L, li) => {
    h = L.W.map((row, j) => row.reduce((s, w, k) => s + w * h[k], L.b[j]));
    if(li < RM.layers.length - 1) h = h.map(v => Math.max(0, v));
  });
  return 1 / (1 + Math.exp(-h[0]));
}
const md = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\n/g, "<br>");
// Bacak adından okunur adım: "M2 · Yenikapı - Hacıosman · Şişli → Taksim" -> {hat, yol}
// Saatin bulunma eki: 19:30 -> "'da", 18:00 -> "'de", 13:00 -> "'te" (okunuşun son kelimesine göre)
const SON = ["sıfır","bir","iki","üç","dört","beş","altı","yedi","sekiz","dokuz"], ONLAR = ["","on","yirmi","otuz","kırk","elli"];
function saatEki(hhmm){
  const [h, m] = hhmm.split(":").map(Number), n = m ? m : h;
  const w = n % 10 ? SON[n % 10] : n ? ONLAR[Math.floor(n / 10)] : "sıfır";
  const v = [...w].reverse().find(c => "aeıioöuü".includes(c));
  const sert = /[çfhkpsşt]$/.test(w);
  return "'" + (sert ? "t" : "d") + ("aıou".includes(v) ? "a" : "e");
}
const sa = hhmm => hhmm + saatEki(hhmm);
function legStep(l){
  const parts = String(l.ad).split(" · ");
  const yol = parts[parts.length - 1], hat = l._line ? LINE_KISA(l._line) : (MOD_TR[l.mod] || parts[0]);
  if(l.mod === "yurume"){
    const ak = /^Aktarma · (.+?) \((.+?), bekleme dahil\)$/.exec(l.ad);
    if(ak) return `Aktarma: ${ak[1]} → ${ak[2]} hattı (${l.dk} dk, bekleme dahil)`;
    const bk = / \(bekleme dahil\)$/.test(l.ad);
    if(bk) return `Yürü → ${l.ad.replace(/ durağına yürü \(bekleme dahil\)$/, " durağı")} (${l.dk} dk, bekleme dahil)`;
    const hedef = l.ad.replace(/ durağına yürü$/, " durağı").replace(/ · yürü(yerek)?$/, "").replace(/^Moda sahil yürüyüşü → /, "sahil boyunca ");
    return `Yürü → ${hedef} (${l.dk} dk)`;
  }
  if(l.mod === "mola") return `Mola: ${parts.slice(1).join(" · ")} (${l.dk} dk)`;
  if(l.mod === "otobus" && !l._line) return `Kısa otobüs → ${l.ad.split(" · ")[0].replace(/ istasyonuna dön$/, " istasyonu")} (${l.dk} dk)`;
  return `${hat}: ${yol} (${l.dk} dk)`;
}
function tripFare(r, tip = "tam"){
  const n = r.legs.filter(l => BINIS.has(l.mod)).length;
  const base = tip === "ogrenci" ? UCRET.ogrenci : UCRET.tam;
  return n ? base + (n - 1) * base * UCRET.aktarma_orani : 0;
}
function aRoute(r, intro){
  const s = step(), steps = r.legs.filter(l => l.dk > 0).map(legStep);
  const fark = r.arac_fark;
  const lines = [intro || `**${r.tip}** rota · ${state.trip.from.ad} → ${state.trip.to.ad} · kalkış ${state.saat}:`,
    ...steps.map((t, i) => `${i + 1}. ${t}`),
    `Varış **${varis(r)}** · toplam ${r.sure} dk${r.mola ? ` + ${r.mola} dk mola` : ""}. Aynı saatte araçla ${s.trafik.arac_dk} dk${fark > 0 ? `; ${fark} dk daha hızlısın` : ""}.`];
  if(r.uyari) lines.push(`Uyarı: ${r.uyari}.`);
  if(r.puan) lines.push(`Bu rota **+${r.puan} İBB Puanı** kazandırır (Kapalı Çevrim).`);
  return lines.join("\n");
}
function aBestNoBridge(){
  const s = step(), ok = s.rotalar.filter(r => !r.iptal);
  const r = ok.filter(x => !x.kopru_kullanim).sort((a, b) => b.skor - a.skor)[0] || ok.sort((a, b) => a.kopru_kullanim - b.kopru_kullanim)[0];
  const tr = s.trafik;
  return { route:r, text: aRoute(r, `Şu an ${tr.durum.toLowerCase()} (1. Köprü ${tr.b1} km/s, 2. Köprü ${tr.b2} km/s). Köprü trafiğine girmeyen en iyi seçenek **${r.tip}**:`) };
}
function aTraffic(){
  const s = step(), tr = s.trafik;
  return `${state.saat} itibarıyla **${tr.durum}**: 15 Temmuz Köprüsü ${tr.b1} km/s, FSM Köprüsü ${tr.b2} km/s (${D.trafik_kaynak || "simülasyon"}).\n`
    + `Bu yolculuk araçla yaklaşık ${tr.arac_dk} dk sürer; önerilen rota (${s.rotalar.find(r => r.id === s.oneri).tip}) ${sa(varis(s.rotalar.find(r => r.id === s.oneri)))} vardırır.`;
}
function aMola(){
  const s = step(), sos = s.rotalar.find(r => r.id === "sosyal"), p = sos && sos.mola_poi && POI_BY_ID[sos.mola_poi];
  const lines = [];
  if(p) lines.push(`Güzergâhında açık bir İBB noktası var: **${p.isim}** (${KAT[p.kat].kisa}, ${p.saat_metin}). ${sos.mola} dk mola verirsen **+${sos.puan} İBB Puanı** kazanırsın${s.zirve ? " ve zirve saati trafikte değil orada geçirirsin" : ""}.`);
  else lines.push(`${state.saat} kalkışında güzergâhında açık bir Kent Lokantası, spor tesisi ya da müze yok.`);
  lines.push(`İBB Puanı Kapalı Çevrim'dir: nakde çevrilmez, yalnızca ${KAPALI.join(", ")}'te harcanır.`);
  return {text:lines.join("\n"), route:p ? sos : null};
}
function aRisk(){
  const r = aktifRota(), risk = riskOf(ai.profile);
  const u = traveler(), tip = u ? u.tip : "tam";
  const fare = tripFare(r, tip), bak = u ? u.bakiye : state.mod === "aile" ? state.aile.master.bakiye : state.bakiye;
  const lines = [];
  if(risk != null){
    const hi = risk >= RM.threshold;
    lines.push(`Bakiye yetersizliği riskin **%${Math.round(risk * 100)}** (${hi ? "yüksek" : "düşük"}). Bu tahmin, ${RM.metrics.n_rows.toLocaleString("tr-TR")} yolcu verisiyle PyTorch'ta eğitilen modelden ve "Profilim" ayarlarından geliyor.`);
  }
  lines.push(`${r.tip} rotası ${tl(fare)} tutar (temsilî tarife, aktarma indirimli). ${u ? u.ad + "'in kartında" : "Kartında"} ${tl(bak)} var${bak < fare ? " — **yetmez, yola çıkmadan yükleme yap**." : bak < fare * 2 ? "; dönüş için yükleme yapmanı öneririm." : "; yeterli."}`);
  return lines.join("\n");
}
function aScenario(){
  const s = step(), k = D.meta.krizler[state.kriz], w = WX[state.kriz];
  if(state.kriz === "normal") return `Şu an aktif bir demo senaryosu yok (${w.t}°C, ${w.d.toLowerCase()}). Vapur, metro ve Marmaray planlandığı gibi varsayılıyor. Hava/senaryo simgesinden Lodos ya da Derbi senaryosunu deneyebilirsin.`;
  const iptal = s.rotalar.filter(r => r.iptal).map(r => r.tip);
  return `**${k.baslik}** (simülasyon): ${k.metin}${!s.kriz_aktif ? ` ${state.saat} kalkışında rotan etkilenmiyor.` : ""}`
    + (iptal.length ? `\nKullanılamayan rota: ${iptal.join(", ")}.` : "")
    + `\nÖnerim: **${s.rotalar.find(r => r.id === s.oneri).tip}**, varış ${varis(s.rotalar.find(r => r.id === s.oneri))}.`;
}
function aKids(){
  if(state.mod !== "aile") return {text:`Aile Modu kapalı. "…" menüsünden Aile Modu'nu açarsan çocuklarının kart bakiyelerini ve rotalarını burada görebilirim.`, act:{lbl:"Aile Modu'nu aç", fn:() => hooks.setAile()}};
  const a = state.aile;
  return {text: a.uyeler.map(u => {
    const k = kidRoute(u);
    return `**${u.ad}** (${u.rol}): ${state.trip.from.ad} → ${u.hedef.ad}${k ? ` ${k.sure} dk, ${k.ozet}` : ", rota bulunamadı"}. Bakiye ${tl(u.bakiye)}${u.bakiye < a.esik ? " — düşük" : ""}; otomatik yükleme ${u.oto ? "açık" : "kapalı"}.`;
  }).join("\n") + `\nRotaları haritada kendi renkleriyle çizili.`};
}
const HELP = `Şunları sorabilirsin:\n1. "Taksim'den Kadıköy'e nasıl giderim?"\n2. "Trafiğe girmeden nasıl giderim?"\n3. "19:00'da orada olmalıyım"\n4. "Yolda mola verip puan kazanabilir miyim?"\n5. "Bakiyem yeter mi?"\n6. "Bugün bir uyarı var mı?" · "Çocuklarım nerede?"`;
// Metindeki yer adlarını bul (en uzun eşleşme, çakışmasız, metindeki sırasıyla)
function findPlaces(q){
  const nq = " " + norm(q).replace(/[’`]/g, "'") + " ";
  const hits = [];
  SEARCH.forEach(it => {
    const n = norm(it.ad); if(n.length < 4) return;
    let i = nq.indexOf(n);
    while(i >= 0){
      const before = nq[i - 1], after = nq[i + n.length];
      if(!/[a-z0-9]/.test(before) && !/[a-z0-9]/.test(after || " ") || after === "'") hits.push({it, i, j:i + n.length});
      i = nq.indexOf(n, i + 1);
    }
  });
  hits.sort((a, b) => (b.j - b.i) - (a.j - a.i));
  const out = [];
  hits.forEach(h => { if(!out.some(o => h.i < o.j && o.i < h.j)) out.push(h); });
  out.sort((a, b) => a.i - b.i);
  return out.map(h => ({...h, sonek: nq.slice(h.j, h.j + 5)}));
}
const ABLATIF = /^'?(d|t)(a|e)n/;    // 'den / 'tan ... -> kalkış
function aiAnswer(q){
  const nq = norm(q);
  // 1) Yerden yere
  const pl = findPlaces(q);
  if(pl.length >= 2 || (pl.length === 1 && /(nasil|git|gid|var|ulas|yol)/.test(nq))){
    let from, to;
    if(pl.length >= 2){
      const f = pl.find(p => ABLATIF.test(p.sonek)) || pl[0];
      from = f; to = pl.find(p => p !== f) || pl[1];
    } else if(ABLATIF.test(pl[0].sonek)) from = pl[0];
    else to = pl[0];
    if(from && to && hav(from.it.pt, to.it.pt) < 150) return {text:"Kalkış ve varış aynı nokta görünüyor; farklı iki yer yazar mısın?"};
    if(from){ state.trip.from = {ad:from.it.ad, alt:from.it.alt, pt:from.it.pt, key:from.it.key}; }
    if(to){ state.trip.to = {ad:to.it.ad, alt:to.it.alt, pt:to.it.pt, key:to.it.key}; }
    tripChanged(); hooks.render({forceFocus:true});
    const s = step();
    if(!s.rotalar.length) return {text:`${state.trip.from.ad} → ${state.trip.to.ad} için ağda rota bulamadım.`};
    const r = aktifRota();
    return {text: aRoute(r, `Haritayı **${state.trip.from.ad} → ${state.trip.to.ad}** olarak güncelledim. Önerim **${r.tip}**:`)
      + `\nDiğer seçenekler: ${s.rotalar.filter(x => x.id !== r.id && !x.iptal).map(x => `${x.tip} ${x.sure} dk${x.mola ? " + mola" : ""} (varış ${varis(x)})`).join(", ")}.`};
  }
  // 2) Saat
  const tm = /(\d{1,2})[:.](\d{2})/.exec(q);
  if(tm && /(orada|var|yetis|olmali|kadar)/.test(nq)){
    const hedef = (+tm[1]) * 60 + (+tm[2]);
    const h = cikisBul(Math.min(24 * 60, hedef));
    if(!h) return {text:`Hedef varış ${fmt(hedef)}: buna yetişen bir kalkış simülasyon aralığında (06:00–23:30) yok.`};
    state.zamanMod = "varis"; state.hedef = Math.ceil(hedef / 30) * 30; hooks.setSaat(h);
    const r = aktifRota();
    return {text: aRoute(r, `Hedef: **${state.trip.to.ad}**, varış en geç ${fmt(hedef)}. En geç **${sa(h)}** çıkman yeterli. Önerilen rota **${r.tip}**:`)};
  }
  if(/(simdi|hemen) (cik|gid)/.test(nq)){ hooks.hemenCik(); return {text: aRoute(aktifRota(), `Kalkışı şimdiki saate (${state.saat}) ayarladım:`)}; }
  // 3) Konu bazlı
  if(/(girmeden|kopru(den|ye)? (gecme|kac)|trafiksiz)/.test(nq)){ const b = aBestNoBridge(); return {text:b.text, route:b.route}; }
  if(/(lodos|vapur|iptal|derbi|mac|hava|uyari|kriz|senaryo)/.test(nq)) return {text:aScenario()};
  if(/(cocu|elif|\bcan\b|aile|oglum|kizim)/.test(nq)) return aKids();
  if(/(bakiye|risk|para|yeter|yukle|ucret|kac (tl|lira)|istanbulkart)/.test(nq)) return {text:aRisk()};
  if(/(mola|puan|indirim|lokanta|yemek|spor|muze|kapali|tesvik|kampanya)/.test(nq)) return aMola();
  if(/(trafik|kopru|yogun|sikis)/.test(nq)) return {text:aTraffic()};
  if(/(nasil|rota|yol|aktarma|hangi|git|nereden|binecek|in(ecek|eyim))/.test(nq)) return {text:aRoute(aktifRota())};
  if(/(merhaba|selam|yardim|neler|ne yapabil)/.test(nq)) return {text:`Merhaba! Seçili yolculuğun ${state.trip.from.ad} → ${state.trip.to.ad}, ${state.saat} kalkış. ${HELP}`};
  return {text:`Bunu tam anlayamadım. ${HELP}`};
}

