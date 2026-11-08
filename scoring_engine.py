"""
İst-Route · Akıllı Öneri ve Skorlama Motoru
===========================================

    Toplam Rota Skoru = 0.55 · S_ind + 0.45 · S_soc

S_ind  (Bireysel, 0-100)
    0.55 · (T_min / T_eff)            -> süre verimliliği (mola süresinin %25'i ceza olarak eklenir)
    0.20 · 1 / (1 + 0.5 · aktarma)    -> aktarma yükü
    0.25 · konfor                     -> 0.6 · yürüme konforu + 0.4 · (1 - kalabalık · yoğunluk)

S_soc  (Sosyal / Şehir, 0-100)
    0.40 · köprü arter kaçınma         -> 1 - (köprü koridoru kullanımı · 1./2. Köprü yoğunluğu)
    0.35 · zirve dağıtma oranı         -> molanın zirve penceresiyle (08:00-09:30, 17:00-19:30) örtüşme payı
    0.25 · İstanbulkart Plus potansiyeli -> kazanılan puan / 25

Motor, 06:00-23:30 arası her yarım saat için üç rotayı (Kırmızı / Mavi / Sarı)
hesaplar; sarı rotanın mola noktası o saatte AÇIK olan POI'ler arasından skoru
maksimize edecek şekilde dinamik seçilir. Çıktı tek bir JSON payload'dır;
arayüz bu payload'la sunucuya dönmeden anlık tepki verir.

Kullanım:
    python scoring_engine.py            # 18:00 özetini yazdırır
    python scoring_engine.py --export   # ist_route_demo.html (tek dosya, çevrimdışı demo)
"""
from __future__ import annotations

import json
import math
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from network import net_payload
from poi_loader import acik_mi, mesafe_m, tum_poiler

ROOT = Path(__file__).resolve().parent
CACHE_FILE = ROOT / "cache" / "osrm_cache.json"

W_IND, W_SOC = 0.55, 0.45
MOLA_DK = 45
ZIRVE = [(8 * 60, 9 * 60 + 30), (17 * 60, 19 * 60 + 30)]

ORIGIN = {"ad": "Mecidiyeköy", "alt": "Şişli", "pt": (41.0668, 28.9958)}  # Büyükdere Cd. tarafı: OSRM ara sokağa sapmasın
DEST = {"ad": "Kalamış Sahili", "alt": "Kadıköy", "pt": (40.9788, 29.0418)}

# Köprü hız profili (km/s). 08/09/13/18/19/23 değerleri önceki sürümdeki
# sensör ölçümleridir; ara saatler doğrusal profil ile tamamlanmıştır.
B1 = {6: 70, 7: 40, 8: 14, 9: 22, 10: 45, 11: 58, 12: 62, 13: 68, 14: 62, 15: 50, 16: 32,
      17: 18, 18: 12, 19: 18, 20: 40, 21: 60, 22: 75, 23: 82, 24: 85}
B2 = {6: 78, 7: 50, 8: 32, 9: 45, 10: 60, 11: 66, 12: 70, 13: 74, 14: 68, 15: 58, 16: 44,
      17: 34, 18: 28, 19: 36, 20: 55, 21: 70, 22: 80, 23: 85, 24: 86}

# Proaktif kriz senaryoları (İBB AKOM / Şehir Hatları duyuru simülasyonu)
KRIZLER = {
    # Senaryo metinleri simülasyondur; resmi kurum duyurusu gibi sunulmaz (PRODUCT.md marka taahhüdü)
    "normal": {"seviye": "bilgi", "baslik": "Senaryo yok",
               "metin": "Vapur, metro ve Marmaray seferleri planlandığı gibi varsayılıyor.", "pencere": None},
    "lodos": {"seviye": "kritik", "baslik": "Senaryo: kuvvetli lodos",
              "metin": "Beşiktaş–Kadıköy vapur seferleri iptal varsayılıyor; öneriler raylı sistemlere kayar.",
              "pencere": None},
    "mac": {"seviye": "uyari", "baslik": "Senaryo: Şükrü Saracoğlu'nda derbi (20:00)",
            "metin": "16:30–23:00 arası Söğütlüçeşme aktarmasında kalabalık ve ek bekleme varsayılıyor.",
            "pencere": (16 * 60 + 30, 23 * 60)},
}
STADYUM = {"ad": "Şükrü Saracoğlu Stadyumu", "pt": (40.9875, 29.0369)}

# Biniş ücretleri (simülasyon tarifesi, ₺) – aktarmada indirimli
UCRET = {"tam": 30.0, "ogrenci": 15.0, "aktarma_orani": 0.6}

# C3: gerçek veri varsa köprü hızları İBB traffic_density_202501'den (hafta içi saatlik ortalama)
TRAFIK_KAYNAK = "Simülasyon profili (08/09/13/18/19/23 ölçümleri + interpolasyon)"
_TP = ROOT / "data_real" / "traffic_profile.json"
if _TP.exists():
    _prof = json.loads(_TP.read_text(encoding="utf-8"))["saatlik_ort_hiz_kmh"]
    if _prof.get("b1") and _prof.get("b2") and len(_prof["b1"]) == 24 and len(_prof["b2"]) == 24:
        B1 = {h: _prof["b1"][str(h)] for h in range(24)}; B1[24] = B1[0]
        B2 = {h: _prof["b2"][str(h)] for h in range(24)}; B2[24] = B2[0]
        TRAFIK_KAYNAK = "İBB trafik yoğunluğu verisi · Ocak 2025 hafta içi saatlik ortalama"

BRIDGES = [
    {"id": "b1", "ad": "15 Temmuz Şehitler Köprüsü", "pt": (41.0453, 29.0343)},
    {"id": "b2", "ad": "Fatih Sultan Mehmet Köprüsü", "pt": (41.0910, 29.0610)},
]


# ----------------------------------------------------------------------------
# Trafik
# ----------------------------------------------------------------------------
def _interp(tablo: dict, dk: int) -> float:
    h, frac = divmod(dk, 60)
    a, b = tablo[h], tablo[min(h + 1, 24)]
    return a + (b - a) * frac / 60


def trafik(dk: int) -> dict:
    b1, b2 = _interp(B1, dk), _interp(B2, dk)
    # Gerçek veri saatlik ortalamadır (anlık kilitlenmeleri yumuşatır): 70 km/s serbest akış = 0, 28 km/s = 1
    cong = max(0.0, min(1.0, (70 - b1) / 42))
    if b1 < 35:
        durum, seviye = "Köprüler kilitli", "kritik"
    elif b1 < 45:
        durum, seviye = "Köprü arterleri yoğun", "yogun"
    else:
        durum, seviye = "Trafik akıcı", "akici"
    return {"b1": round(b1), "b2": round(b2), "cong": round(cong, 3), "durum": durum,
            "seviye": seviye, "arac_dk": round(24 + 41 * cong)}


def zirvede(dk: int) -> bool:
    return any(a <= dk < b for a, b in ZIRVE)


def zirve_ortusme(bas: int, son: int) -> float:
    if son <= bas:
        return 0.0
    ort = sum(max(0, min(son, b) - max(bas, a)) for a, b in ZIRVE)
    return ort / (son - bas)


# ----------------------------------------------------------------------------
# OSRM (önbellekli, çevrimdışı güvenli)
# ----------------------------------------------------------------------------
def _cache_load() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _cache_key(pts) -> str:
    return ";".join(f"{lon:.5f},{lat:.5f}" for lat, lon in pts)


def _osrm_fetch(pts) -> list | None:
    url = ("https://router.project-osrm.org/route/v1/driving/" + _cache_key(pts)
           + "?overview=full&geometries=geojson")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IstRoute-Datathon/2.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read().decode("utf-8"))
        if data.get("routes"):
            return [[round(y, 5), round(x, 5)] for x, y in data["routes"][0]["geometry"]["coordinates"]]
    except Exception:
        return None
    return None


class GeoStore:
    """Geometrileri tekilleştirir; OSRM isteklerini toplu ve paralel çözer."""

    def __init__(self, online: bool = True):
        self.online = online
        self.cache = _cache_load()
        self.geoms: dict[str, list] = {}
        self._pending: dict[str, tuple] = {}

    def add(self, pts, osrm: bool) -> str:
        key = ("o:" if osrm else "s:") + _cache_key(pts)
        if key not in self.geoms:
            self.geoms[key] = [[round(a, 5), round(b, 5)] for a, b in pts]
            if osrm:
                self._pending[key] = tuple(pts)
        return key

    def resolve(self) -> None:
        todo = {k: p for k, p in self._pending.items() if _cache_key(p) not in self.cache}
        if todo and self.online:
            with ThreadPoolExecutor(max_workers=6) as ex:
                for k, res in zip(todo, ex.map(_osrm_fetch, todo.values())):
                    if res:
                        self.cache[_cache_key(todo[k])] = res
            try:
                CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                CACHE_FILE.write_text(json.dumps(self.cache), encoding="utf-8")
            except Exception:
                pass
        for k, p in self._pending.items():
            hit = self.cache.get(_cache_key(p))
            if hit:
                self.geoms[k] = hit
        self._pending.clear()


# ----------------------------------------------------------------------------
# Rota tanımları
# ----------------------------------------------------------------------------
P = {
    "mcd_mb": (41.0661, 28.9962), "zincir": (41.0676, 29.0123), "kopru1": (41.0453, 29.0343),
    "altuni": (41.0225, 29.0450), "acibadem": (41.0040, 29.0450), "sogut": (40.9935, 29.0375),
    "feneryolu": (40.9822, 29.0515), "besiktas": (41.0425, 29.0058),
    "kadikoy": (40.9928, 29.0224), "moda": (40.9838, 29.0238),
}

# Sarı rota: M2 + Marmaray hattı; (ad, nokta, başlangıçtan dakika, hat)
RAY = [
    ("Şişli-Mecidiyeköy", (41.0640, 28.9925), 3, "M2"),
    ("Osmanbey", (41.0525, 28.9870), 5, "M2"),
    ("Taksim", (41.0370, 28.9860), 7, "M2"),
    ("Şişhane", (41.0290, 28.9740), 9, "M2"),
    ("Haliç", (41.0215, 28.9685), 10, "M2"),
    ("Vezneciler", (41.0130, 28.9580), 12, "M2"),
    ("Yenikapı", (41.0050, 28.9510), 16, "MR"),   # M2 -> Marmaray aktarması dahil
    ("Sirkeci", (41.0145, 28.9780), 18, "MR"),
    ("Üsküdar", (41.0256, 29.0158), 22, "MR"),
    ("Ayrılık Çeşmesi", (41.0010, 29.0300), 26, "MR"),
    ("Söğütlüçeşme", (40.9935, 29.0375), 28, "MR"),
    ("Feneryolu", (40.9822, 29.0515), 30, "MR"),
]
RAY_SON_YURUME = 6
MOLA_YARICAP_M = 1600
YURUME_ESIK_M = 700          # üstü kısa otobüs bağlantısı sayılır
# Brief: zirve dağıtma etkisi Kent Lokantası / Spor molası için tanımlı; müze ziyareti kısmi.
# Müze ziyareti süre olarak esnek ve çoğu müze zirve saatine yakın kapanır -> kısmi etki.
DAGITMA_UYUM = {"lokanta": 1.0, "spor": 1.0, "muze": 0.6}


def baglanti(npt, poi) -> tuple[str, int]:
    """İstasyon -> POI bağlantısı: (mod, dakika)."""
    d = mesafe_m(npt, (poi["lat"], poi["lon"])) * 1.3
    if d <= YURUME_ESIK_M * 1.3:
        return "yurume", max(2, round(d / 78))
    return "otobus", round(3 + d / 350)


def _leg(gs: GeoStore, mod: str, ad: str, dk: float, pts, osrm: bool) -> dict:
    return {"mod": mod, "ad": ad, "dk": round(dk), "g": gs.add(pts, osrm)}


def rota_hizli(gs: GeoStore, c: float) -> dict:
    mb = 17 + 4 * c
    legs = [
        _leg(gs, "yurume", "Mecidiyeköy durağına yürü", 3, [ORIGIN["pt"], P["mcd_mb"]], False),
        # Metrobüs kendi şeridinde: OSRM araç profili kavşak döngüleri üretir, D-100 hattı ara noktalardan çizilir
        _leg(gs, "metrobus", "Metrobüs · Mecidiyeköy → Söğütlüçeşme (15 Temmuz)", mb,
             [P["mcd_mb"], P["zincir"], (41.0560, 29.0225), P["kopru1"], (41.0405, 29.0420), (41.0330, 29.0455),
              P["altuni"], (41.0120, 29.0450), P["acibadem"], (40.9990, 29.0420), P["sogut"]], False),
        _leg(gs, "marmaray", "Marmaray · Söğütlüçeşme → Feneryolu", 3 + 4,
             [P["sogut"], (40.9880, 29.0440), P["feneryolu"]], False),
        _leg(gs, "yurume", "Kalamış Sahili'ne yürü", 7, [P["feneryolu"], DEST["pt"]], True),
    ]
    return dict(id="hizli", renk="kirmizi", ikon="⚡", tip="Hızlı · Ekspres",
                ozet="Metrobüs + Marmaray", alt="Metrobüs özel şeridi, köprü trafiğini atlar",
                legs=legs, aktarma=1, yurume_dk=13, sahil=False, kalabalik=0.75,
                kopru_kullanim=0.6, mola=0, mola_poi=None, puan=0)


def rota_konforlu(gs: GeoStore, c: float, dk: int) -> dict:
    otobus = 3 + 3 * c
    legs = [
        _leg(gs, "otobus", "Otobüs · Mecidiyeköy → Beşiktaş İskele", otobus,
             [ORIGIN["pt"], (41.0674, 29.0070), (41.0630, 29.0095), (41.0560, 29.0082), (41.0490, 29.0068),
              P["besiktas"]], False),   # Büyükdere → Zincirlikuyu → Barbaros Bulvarı
        # Vapur hattı Boğaz'ın ortasından (Asya kıyısının karasına taşmadan) çizilir
        _leg(gs, "vapur", "Vapur · Beşiktaş → Kadıköy (bekleme dahil)", 20,
             [P["besiktas"], (41.0310, 29.0050), (41.0140, 29.0035), (41.0010, 29.0095), P["kadikoy"]],
             False),
        # Sahil yürüyüşü araç yolundan değil kıyı hattından çizilir (OSRM sürüş profili zikzak üretir)
        _leg(gs, "yurume", "Moda sahil yürüyüşü → Kalamış", 20,
             [P["kadikoy"], (40.9893, 29.0231), P["moda"], (40.9806, 29.0247), (40.9791, 29.0288),
              (40.9783, 29.0340), (40.9786, 29.0385), DEST["pt"]], False),
    ]
    puan = 10 if zirvede(dk) else 5
    return dict(id="konforlu", renk="mavi", ikon="🛋️", tip="Konforlu & Dengeli",
                ozet="Vapur + Sahil Yürüyüşü", alt="0 Trafik Stresi · Boğaz havası",
                legs=legs, aktarma=1, yurume_dk=20, sahil=True, kalabalik=0.2,
                kopru_kullanim=0.0, mola=0, mola_poi=None, puan=puan)


def _ray_pts(i: int, j: int) -> list:
    return [n[1] for n in RAY[i:j + 1]]


def rota_sosyal(gs: GeoStore, dk: int, poi: dict | None, dugum: int | None) -> dict:
    son = len(RAY) - 1
    if poi is None:
        legs = [
            _leg(gs, "yurume", "Şişli-Mecidiyeköy M2'ye yürü", 3, [ORIGIN["pt"], RAY[0][1]], False),
            _leg(gs, "metro", "M2 Metro · Şişli → Yenikapı", RAY[6][2] - 3, _ray_pts(0, 6), False),
            _leg(gs, "marmaray", "Marmaray · Yenikapı → Feneryolu", RAY[son][2] - RAY[6][2],
                 _ray_pts(6, son), False),
            _leg(gs, "yurume", "Kalamış Sahili'ne yürü", RAY_SON_YURUME, [RAY[son][1], DEST["pt"]], True),
        ]
        return dict(id="sosyal", renk="sari", ikon="🎁", tip="Sosyal Mola",
                    ozet="M2 + Marmaray (mola noktası kapalı)",
                    alt="Bu saatte güzergâhta açık İBB noktası yok",
                    legs=legs, aktarma=1, yurume_dk=9, sahil=False, kalabalik=0.45,
                    kopru_kullanim=0.0, mola=0, mola_poi=None, puan=0)

    ad, npt, ndk, hat = RAY[dugum]
    bmod, w = baglanti(npt, poi)
    legs = [_leg(gs, "yurume", "Şişli-Mecidiyeköy M2'ye yürü", 3, [ORIGIN["pt"], RAY[0][1]], False)]
    if dugum <= 6:
        legs.append(_leg(gs, "metro", f"M2 Metro · Şişli → {ad}", ndk - 3, _ray_pts(0, dugum), False))
    else:
        legs.append(_leg(gs, "metro", "M2 Metro · Şişli → Yenikapı", RAY[6][2] - 3, _ray_pts(0, 6), False))
        legs.append(_leg(gs, "marmaray", f"Marmaray · Yenikapı → {ad}", ndk - RAY[6][2],
                         _ray_pts(6, dugum), False))
    fiil = "yürü" if bmod == "yurume" else "kısa otobüs"
    legs.append(_leg(gs, bmod, f"{poi['isim']} · {fiil}", w, [npt, (poi["lat"], poi["lon"])], True))
    legs.append({"mod": "mola", "ad": f"Mola · {poi['isim']}", "dk": MOLA_DK, "g": None})
    legs.append(_leg(gs, bmod, f"{ad} istasyonuna dön", w, [(poi["lat"], poi["lon"]), npt], True))
    if dugum < 6:
        legs.append(_leg(gs, "metro", f"M2 Metro · {ad} → Yenikapı", RAY[6][2] - ndk, _ray_pts(dugum, 6), False))
        legs.append(_leg(gs, "marmaray", "Marmaray · Yenikapı → Feneryolu", RAY[son][2] - RAY[6][2],
                         _ray_pts(6, son), False))
    else:
        legs.append(_leg(gs, "marmaray", f"Marmaray · {ad} → Feneryolu", RAY[son][2] - ndk,
                         _ray_pts(dugum, son), False))
    legs.append(_leg(gs, "yurume", "Kalamış Sahili'ne yürü", RAY_SON_YURUME, [RAY[son][1], DEST["pt"]], True))

    kisa = poi["isim"].replace(" Kent Lokantası", " Kent Lok.").replace(" Spor Kompleksi", " Spor")
    tur = {"lokanta": "Kent Lokantası", "spor": "Spor Tesisi", "muze": "Müze"}[poi["kat"]]
    return dict(id="sosyal", renk="sari", ikon="🎁", tip="Sosyal Mola",
                ozet=f"{tur} Duraklı", alt=kisa,
                legs=legs, aktarma=2 if bmod == "yurume" else 4,
                yurume_dk=3 + (2 * w if bmod == "yurume" else 4) + RAY_SON_YURUME, sahil=False,
                kalabalik=0.35, kopru_kullanim=0.0, mola=MOLA_DK, mola_poi=poi["id"],
                mola_kat=poi["kat"], mola_bas=dk + ndk + w, puan=int(poi["odul_puani"]), dugum=ad)


# ----------------------------------------------------------------------------
# Skorlama
# ----------------------------------------------------------------------------
def _seyahat(r: dict) -> int:
    return sum(l["dk"] for l in r["legs"] if l["mod"] != "mola")


def skorla(rotalar: list[dict], tr: dict, dk: int) -> None:
    c = tr["cong"]
    for r in rotalar:
        r["sure"] = _seyahat(r)
        r["t_eff"] = r["sure"] + 0.25 * r["mola"]
    t_min = min(r["t_eff"] for r in rotalar if not r.get("iptal"))

    for r in rotalar:
        if r.get("iptal"):
            r["s_ind"] = r["s_soc"] = r["skor"] = 0.0
            r["bilesen"] = {k: 0 for k in ("zaman", "aktarma", "konfor", "kacinma", "dagitma", "tesvik")}
            continue
        zaman = t_min / r["t_eff"]
        aktarma = 1 / (1 + 0.5 * r["aktarma"])
        yurume = max(0.0, 1 - r["yurume_dk"] / 45) * (1.15 if r["sahil"] else 1.0)
        konfor = 0.6 * min(1.0, yurume) + 0.4 * (1 - r["kalabalik"] * c)
        s_ind = 100 * (0.55 * zaman + 0.20 * aktarma + 0.25 * konfor)

        kacinma = 1 - r["kopru_kullanim"] * c
        if r["mola"]:
            dagitma = (zirve_ortusme(r["mola_bas"], r["mola_bas"] + r["mola"])
                       * DAGITMA_UYUM[r["mola_kat"]])
        elif r["id"] == "konforlu" and zirvede(dk):
            dagitma = 0.4   # yükü kara köprülerinden deniz hattına kaydırır
        else:
            dagitma = 0.0
        tesvik = min(1.0, r["puan"] / 25)
        s_soc = 100 * (0.40 * kacinma + 0.35 * dagitma + 0.25 * tesvik)

        r["s_ind"], r["s_soc"] = round(s_ind, 1), round(s_soc, 1)
        r["skor"] = round(W_IND * s_ind + W_SOC * s_soc, 1)
        r["bilesen"] = {
            "zaman": round(zaman, 3), "aktarma": round(aktarma, 3), "konfor": round(konfor, 3),
            "kacinma": round(kacinma, 3), "dagitma": round(dagitma, 3), "tesvik": round(tesvik, 3),
        }


def _mola_adaylari() -> list[tuple[dict, int]]:
    """Sarı rotanın raylı düğümlerine MOLA_YARICAP_M içindeki POI'ler (en yakın düğümle)."""
    out = []
    for p in tum_poiler():
        best = min(range(len(RAY) - 1), key=lambda i: mesafe_m(RAY[i][1], (p["lat"], p["lon"])))
        if mesafe_m(RAY[best][1], (p["lat"], p["lon"])) <= MOLA_YARICAP_M:
            out.append((p, best))
    return out


def _kriz_uygula(r: dict, senaryo: str, dk: int) -> None:
    """Senaryoyu rotaya işler: iptal, ek bekleme, kalabalık. Rota geometrisi değişmez."""
    if senaryo == "lodos" and r["id"] == "konforlu":
        r["iptal"] = True
        r["uyari"] = "Lodos nedeniyle vapur seferleri iptal"
        r["puan"] = 0
    a, b = KRIZLER["mac"]["pencere"]
    if senaryo == "mac" and a <= dk < b:
        ek = {"hizli": 8, "sosyal": 3}.get(r["id"])
        if ek:
            r["legs"] = [dict(l) for l in r["legs"]]
            idx = next(i for i, l in enumerate(r["legs"]) if l["mod"] == "marmaray" and "Söğütlüçeşme" in l["ad"]
                       or (l["mod"] == "marmaray" and r["id"] == "sosyal" and "Feneryolu" in l["ad"]))
            r["legs"][idx]["dk"] += ek
            r["legs"][idx]["ad"] += f" (+{ek} dk stadyum yoğunluğu)"
            r["kalabalik"] = 1.0 if r["id"] == "hizli" else 0.6
            r["uyari"] = f"Söğütlüçeşme'de derbi kalabalığı · +{ek} dk"


def adim_hesapla(gs: GeoStore, dk: int, adaylar, senaryo: str = "normal") -> dict:
    tr = trafik(dk)
    c = tr["cong"]
    sabit = [rota_hizli(gs, c), rota_konforlu(gs, c, dk)]
    for r in sabit:
        _kriz_uygula(r, senaryo, dk)

    secenekler = []
    for p, dugum in adaylar:
        _, w = baglanti(RAY[dugum][1], p)
        if acik_mi(p, dk + RAY[dugum][2] + w, MOLA_DK):
            secenekler.append((p, dugum))
    if not secenekler:
        secenekler = [(None, None)]

    en_iyi, en_iyi_set = None, None
    for p, dugum in secenekler:
        sos = rota_sosyal(gs, dk, p, dugum)
        _kriz_uygula(sos, senaryo, dk)
        aday = [dict(r) for r in sabit] + [sos]
        skorla(aday, tr, dk)
        if en_iyi is None or aday[2]["skor"] > en_iyi["skor"]:
            en_iyi, en_iyi_set = aday[2], aday
    rotalar = en_iyi_set
    onerilen = max((r for r in rotalar if not r.get("iptal")), key=lambda r: r["skor"])["id"]
    for r in rotalar:
        r["oneri"] = r["id"] == onerilen
        # Kapıdan kapıya: mola süresi dahil (eskiden yalnızca hareket süresiydi; yanıltıcıydı)
        r["varis_dk"] = r["sure"] + r["mola"]
        r["arac_fark"] = tr["arac_dk"] - r["varis_dk"]
        r.setdefault("iptal", False)
        r.setdefault("uyari", None)
        r.pop("t_eff", None)
    pencere = KRIZLER[senaryo]["pencere"]
    kriz_aktif = senaryo != "normal" and (pencere is None or pencere[0] <= dk < pencere[1])
    return {"trafik": tr, "zirve": zirvede(dk), "rotalar": rotalar, "oneri": onerilen,
            "kriz_aktif": kriz_aktif, "alternatif_mola": len([s for s in secenekler if s[0]])}


def build_payload(online: bool = True) -> dict:
    gs = GeoStore(online=online)
    adaylar = _mola_adaylari()
    senaryolar = {}
    for sen in KRIZLER:
        senaryolar[sen] = {f"{dk // 60:02d}:{dk % 60:02d}": adim_hesapla(gs, dk, adaylar, sen)
                           for dk in range(6 * 60, 24 * 60, 30)}
    adimlar = senaryolar["normal"]
    gs.resolve()

    pois = [{k: p[k] for k in ("id", "kat", "isim", "ilce", "lat", "lon", "saat_metin", "gunler",
                               "detay", "odul_puani", "koordinat_kaynagi")} for p in tum_poiler()]
    return {
        "meta": {
            "origin": {**ORIGIN, "pt": list(ORIGIN["pt"])},
            "dest": {**DEST, "pt": list(DEST["pt"])},
            "agirlik": {"ind": W_IND, "soc": W_SOC},
            "mola_dk": MOLA_DK,
            "varsayilan_saat": "18:00",
            "ucret": UCRET,
            "krizler": {k: {**v, "pencere": list(v["pencere"]) if v["pencere"] else None}
                        for k, v in KRIZLER.items()},
            "stadyum": {**STADYUM, "pt": list(STADYUM["pt"])},
            "kapali_cevrim": ["Kent Lokantası", "İBB Sosyal Tesisleri", "Halk Ekmek"],
        },
        "pois": pois,
        "bridges": [{**b, "pt": list(b["pt"])} for b in BRIDGES],
        "geoms": gs.geoms,
        "senaryolar": senaryolar,
        # Faz B/C1: herhangi iki nokta için tarayıcıda rota araması yapılan ağ (GTFS varsa GTFS)
        "net": net_payload(),
        # C2: İBB raylı sistem hatları vektör verisi (harita katmanı)
        "rail": json.loads((ROOT / "data_real" / "rail_lines.json").read_text(encoding="utf-8"))
                if (ROOT / "data_real" / "rail_lines.json").exists() else None,
        "trafik_kaynak": TRAFIK_KAYNAK,
        # Asistan: PyTorch RiskMLP ağırlıkları (export_risk_model.py) — tarayıcıda ileri geçiş
        "risk_model": json.loads((ROOT / "data_real" / "risk_model.json").read_text(encoding="utf-8"))
                      if (ROOT / "data_real" / "risk_model.json").exists() else None,
    }


def render_html(payload: dict, template: str = "index.html") -> str:
    """Şablona veri paketini ve ortak JS'i (ui/engine.js, ui/assistant.js) gömer -> tek dosya."""
    tpl = (ROOT / "ui" / template).read_text(encoding="utf-8")
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    for mark, fn in (("/*__ENGINE__*/", "engine.js"), ("/*__ASSISTANT__*/", "assistant.js")):
        if mark in tpl:
            tpl = tpl.replace(mark, (ROOT / "ui" / fn).read_text(encoding="utf-8").replace("</script", "<\\/script"))
    return tpl.replace("/*__IST_PAYLOAD__*/null", blob)


if __name__ == "__main__":
    pl = build_payload(online="--offline" not in sys.argv)
    if "--export" in sys.argv:
        for tpl, name in (("index.html", "ist_route_demo.html"), ("mobile.html", "ist_route_mobile.html")):
            if not (ROOT / "ui" / tpl).exists():
                continue
            out = ROOT / name
            out.write_text(render_html(pl, tpl), encoding="utf-8")
            print(f"Yazıldı: {out}  ({out.stat().st_size / 1024:.0f} KB)")
    for sen, saat in (("normal", "08:00"), ("normal", "13:00"), ("normal", "18:00"), ("normal", "23:00"),
                      ("lodos", "18:00"), ("mac", "18:00")):
        a = pl["senaryolar"][sen][saat]
        print(f"\n[{sen}] {saat}  {a['trafik']['durum']}  (1.Köprü {a['trafik']['b1']} km/s, araç {a['trafik']['arac_dk']} dk)")
        for r in a["rotalar"]:
            m = f" + {r['mola']} dk mola @ {r['alt']}" if r["mola"] else ""
            ipt = "  [İPTAL]" if r["iptal"] else ""
            print(f"  {'★' if r['oneri'] else ' '} {r['id']:<9} {r['sure']:>3} dk{m:<45} "
                  f"S_ind={r['s_ind']:5.1f}  S_soc={r['s_soc']:5.1f}  TOPLAM={r['skor']:5.1f}  +{r['puan']} puan{ipt}")
    real = sum(1 for k, v in pl["geoms"].items() if k.startswith("o:") and len(v) > 4)
    print(f"\nOSRM geometri: {real}/{sum(1 for k in pl['geoms'] if k.startswith('o:'))} gerçek yol")
