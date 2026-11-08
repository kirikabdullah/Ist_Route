"""
İst-Route · POI Yükleyici
data_poi/ altındaki temizlenmiş İBB veri setlerini tek bir şemaya indirger.

Ortak şema (dict):
    id, kat ('lokanta' | 'spor' | 'muze'), isim, ilce, lat, lon,
    acilis, kapanis (dakika cinsinden, gün başından), saat_metin,
    gunler, detay, odul_puani, koordinat_kaynagi
"""
from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data_poi"

# tum_ibb_muzeleri.csv koordinat içermiyor. Adres alanlarından elle çıkarılmış
# yaklaşık konumlar (±150 m). Aynı binadaki birimler (Gazhane, Haliç Sanat)
# haritada üst üste binmesin diye aşağıda spiral ofsetle ayrıştırılır.
MUZE_KOORDINAT = {
    "MZ_01": (41.0823, 29.0663), "MZ_02": (41.0436, 28.9404), "MZ_03": (41.0791, 29.0545),
    "MZ_04": (41.0560, 28.9877), "MZ_05": (40.9745, 28.8460), "MZ_06": (41.0770, 29.0430),
    "MZ_07": (41.0084, 28.9412), "MZ_08": (41.0318, 28.9757), "MZ_09": (41.0990, 28.9930),
    "MZ_10": (41.0370, 28.9855), "MZ_11": (40.9985, 29.0435), "MZ_12": (41.1050, 29.0830),
    "MZ_13": (41.1050, 29.0830), "MZ_14": (41.0130, 28.9815), "MZ_15": (41.0655, 28.9890),
    "MZ_16": (41.0260, 28.9590), "MZ_17": (41.0260, 28.9590), "MZ_18": (41.0260, 28.9590),
    "MZ_19": (40.9985, 28.9260), "MZ_20": (41.0090, 28.9220), "MZ_21": (40.9985, 29.0435),
    "MZ_22": (40.9800, 28.8720), "MZ_23": (41.0160, 28.9640), "MZ_24": (41.0280, 28.9720),
    "MZ_25": (41.0480, 29.0080), "MZ_26": (41.0800, 28.9730), "MZ_27": (40.9985, 29.0435),
    "MZ_28": (40.9760, 29.0620), "MZ_29": (40.9350, 29.1310), "MZ_30": (41.0670, 28.9950),
    "MZ_31": (41.0137, 28.9535), "MZ_32": (40.8740, 29.1270), "MZ_33": (41.0335, 28.9400),
    "MZ_34": (41.0084, 28.9779), "MZ_35": (40.9930, 28.9230), "MZ_36": (40.9880, 29.0270),
    "MZ_37": (41.0230, 29.1520), "MZ_38": (41.0300, 28.9740), "MZ_39": (40.9745, 28.8460),
    "MZ_40": (40.9985, 29.0435), "MZ_41": (40.9985, 29.0435), "MZ_42": (40.9985, 29.0435),
    "MZ_43": (41.0380, 28.9895), "MZ_44": (41.0235, 28.9740), "MZ_45": (41.0330, 28.9900),
    "MZ_46": (41.0160, 28.9520), "MZ_47": (41.0040, 28.9770), "MZ_48": (41.0083, 28.9768),
}

_SAAT_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")


def _saat_araligi(metin: str) -> tuple[int, int]:
    m = _SAAT_RE.search(str(metin))
    if not m:
        return 0, 24 * 60
    h1, m1, h2, m2 = map(int, m.groups())
    return h1 * 60 + m1, h2 * 60 + m2


SON_KABUL_DK = 30


def acik_mi(poi: dict, bas_dk: int, sure_dk: int = 0) -> bool:
    """POI, bas_dk anında misafir kabul ediyor mu? (son kabul: kapanıştan 30 dk önce)"""
    return poi["acilis"] <= bas_dk and bas_dk + min(sure_dk, SON_KABUL_DK) <= poi["kapanis"]


def _ayristir(pois: list[dict]) -> None:
    """Aynı koordinattaki POI'leri ~35 m'lik altın-açı spiraliyle ayırır."""
    gruplar: dict[tuple, list[dict]] = {}
    for p in pois:
        gruplar.setdefault((round(p["lat"], 4), round(p["lon"], 4)), []).append(p)
    for grup in gruplar.values():
        if len(grup) < 2:
            continue
        for i, p in enumerate(grup):
            aci = i * 2.39996
            r = 0.00032 * math.sqrt(i + 1)
            p["lat"] += r * math.cos(aci)
            p["lon"] += r * math.sin(aci) * 1.32


def _baslik(s: str) -> str:
    """'ATAŞEHİR KENT LOKANTASI' -> 'Ataşehir Kent Lokantası' (Türkçe i/İ duyarlı)."""
    def kelime(w: str) -> str:
        w = w.replace("I", "ı").replace("İ", "i").lower()
        return (w[0].replace("i", "İ").replace("ı", "I").upper() + w[1:]) if w else w
    return " ".join(kelime(w) for w in str(s).split())


@lru_cache(maxsize=1)
def tum_poiler() -> tuple[dict, ...]:
    pois: list[dict] = []

    kl = pd.read_csv(DATA_DIR / "tum_kent_lokantalari.csv")
    for r in kl.itertuples(index=False):
        a, k = _saat_araligi(r.calisma_saatleri)
        ilce = _baslik(str(r.isim).replace("KENT LOKANTASI", "").strip())
        pois.append(dict(
            id=r.id, kat="lokanta", isim=_baslik(r.isim), ilce=ilce,
            lat=float(r.enlem), lon=float(r.boylam), acilis=a, kapanis=k,
            saat_metin=r.calisma_saatleri, gunler=r.calisma_gunleri,
            detay=f"{r.fiyat}", odul_puani=int(r.odul_puani),
            koordinat_kaynagi="CSV",
        ))

    sp = pd.read_csv(DATA_DIR / "tum_spor_tesisleri.csv")
    for r in sp.itertuples(index=False):
        a, k = _saat_araligi(r.calisma_saatleri)
        pois.append(dict(
            id=r.id, kat="spor", isim=r.isim, ilce=r.ilce,
            lat=float(r.enlem), lon=float(r.boylam), acilis=a, kapanis=k,
            saat_metin=r.calisma_saatleri, gunler=r.calisma_gunleri,
            detay=r.tur, odul_puani=int(r.odul_puani), koordinat_kaynagi="CSV",
        ))

    mz = pd.read_csv(DATA_DIR / "tum_ibb_muzeleri.csv")
    muzeler = []
    for r in mz.itertuples(index=False):
        if r.id not in MUZE_KOORDINAT:
            continue
        lat, lon = MUZE_KOORDINAT[r.id]
        a, k = _saat_araligi(r.calisma_saatleri)
        muzeler.append(dict(
            id=r.id, kat="muze", isim=" ".join(str(r.isim).split()), ilce=r.ilce,
            lat=lat, lon=lon, acilis=a, kapanis=k, saat_metin=r.calisma_saatleri,
            gunler="Salı - Pazar", detay=r.adres, odul_puani=int(r.odul_puani),
            koordinat_kaynagi="Adres bazlı yaklaşık",
        ))
    _ayristir(muzeler)
    pois.extend(muzeler)
    return tuple(pois)


def mesafe_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Haversine, metre."""
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


if __name__ == "__main__":
    p = tum_poiler()
    from collections import Counter
    print(Counter(x["kat"] for x in p))
