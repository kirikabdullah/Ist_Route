"""
İst-Route · Ana Hat İstasyon Ağı (Faz B, seçenek b)
===================================================

GTFS DEĞİLDİR. Raylı sistem, Metrobüs, tramvay, füniküler ve başlıca vapur
hatlarının elle derlenmiş, YAKLAŞIK istasyon koordinatları ve TAHMİNÎ
istasyonlar arası süreleriyle kurulmuş bir grafiktir. Amaç, herhangi iki nokta
arasında demo düzeyinde çok-modlu rota üretmektir. Süreler sefer tarifesinden
değil, tipik seyahat sürelerinden türetilmiştir.

Çıktı (net_payload): düğümler (hat × istasyon), hat içi kenarlar ve aktarma
kenarları. Rota araması tarayıcıda (JS Dijkstra) yapılır; böylece tek dosyalık
demo sunucusuz çalışır.
"""
from __future__ import annotations

import math

# mod: metro | marmaray | metrobus | tramvay | funikuler | vapur
# bekleme: ortalama bekleme (dk, sefer aralığının ~yarısı) — biniş/aktarmada eklenir
# istasyonlar: (ad, enlem, boylam, önceki istasyondan dk)
LINES = [
    {"id": "M2", "ad": "M2 Metro", "mod": "metro", "renk": "#00A651", "bekleme": 2, "ist": [
        ("Yenikapı", 41.0050, 28.9510, 0), ("Vezneciler", 41.0130, 28.9580, 2), ("Haliç", 41.0215, 28.9685, 2),
        ("Şişhane", 41.0290, 28.9740, 2), ("Taksim", 41.0370, 28.9860, 2), ("Osmanbey", 41.0525, 28.9870, 2),
        ("Şişli-Mecidiyeköy", 41.0640, 28.9925, 2), ("Gayrettepe", 41.0685, 29.0080, 2), ("Levent", 41.0780, 29.0110, 2),
        ("4. Levent", 41.0860, 29.0070, 2), ("Sanayi Mahallesi", 41.0930, 29.0060, 2), ("İTÜ-Ayazağa", 41.1040, 29.0215, 2),
        ("Atatürk Oto Sanayi", 41.1120, 29.0230, 2), ("Darüşşafaka", 41.1240, 29.0270, 2), ("Hacıosman", 41.1370, 29.0290, 3)]},
    {"id": "MR", "ad": "Marmaray", "mod": "marmaray", "renk": "#0072BC", "bekleme": 4, "ist": [
        ("Halkalı", 41.0170, 28.7740, 0), ("Küçükçekmece", 40.9990, 28.7800, 4), ("Florya", 40.9750, 28.7900, 3),
        ("Yeşilköy", 40.9630, 28.8240, 4), ("Bakırköy", 40.9780, 28.8730, 4), ("Zeytinburnu", 40.9880, 28.9040, 4),
        ("Kazlıçeşme", 40.9930, 28.9200, 2), ("Yenikapı", 41.0050, 28.9510, 4), ("Sirkeci", 41.0145, 28.9780, 2),
        ("Üsküdar", 41.0256, 29.0158, 4), ("Ayrılık Çeşmesi", 41.0010, 29.0300, 4), ("Söğütlüçeşme", 40.9935, 29.0375, 2),
        ("Feneryolu", 40.9822, 29.0515, 2), ("Göztepe", 40.9770, 29.0610, 2), ("Erenköy", 40.9720, 29.0720, 2),
        ("Suadiye", 40.9640, 29.0830, 2), ("Bostancı", 40.9560, 29.0950, 2), ("Maltepe", 40.9330, 29.1300, 5),
        ("Kartal", 40.8900, 29.1900, 6), ("Pendik", 40.8770, 29.2350, 4), ("Tuzla", 40.8180, 29.3000, 7),
        ("Gebze", 40.8000, 29.4300, 8)]},
    {"id": "MB", "ad": "Metrobüs", "mod": "metrobus", "renk": "#E30613", "bekleme": 1, "ist": [
        ("Beylikdüzü", 41.0010, 28.6420, 0), ("Avcılar", 40.9790, 28.7230, 10), ("Cennet Mahallesi", 40.9890, 28.7790, 6),
        ("Sefaköy", 40.9960, 28.8000, 3), ("Yenibosna", 41.0000, 28.8300, 3), ("Şirinevler", 40.9930, 28.8440, 3),
        ("Bahçelievler", 40.9980, 28.8580, 2), ("İncirli", 40.9930, 28.8720, 2), ("Zeytinburnu", 40.9895, 28.9050, 4),
        ("Cevizlibağ", 41.0150, 28.9170, 4), ("Topkapı", 41.0230, 28.9250, 2), ("Edirnekapı", 41.0350, 28.9380, 3),
        ("Ayvansaray", 41.0440, 28.9440, 2), ("Halıcıoğlu", 41.0500, 28.9530, 2), ("Okmeydanı", 41.0580, 28.9700, 3),
        ("Çağlayan", 41.0650, 28.9800, 2), ("Mecidiyeköy", 41.0661, 28.9962, 3), ("Zincirlikuyu", 41.0676, 29.0123, 3),
        ("Burhaniye", 41.0330, 29.0455, 8), ("Altunizade", 41.0225, 29.0450, 2), ("Acıbadem", 41.0040, 29.0450, 3),
        ("Uzunçayır", 40.9990, 29.0420, 2), ("Söğütlüçeşme", 40.9935, 29.0375, 2)],
     # 15 Temmuz Şehitler Köprüsü'nden geçen bacak (köprü arteri kullanımı skorlanır)
     "kopru": [("Zincirlikuyu", "Burhaniye")]},
    {"id": "M4", "ad": "M4 Metro", "mod": "metro", "renk": "#E4007C", "bekleme": 2, "ist": [
        ("Kadıköy", 40.9910, 29.0270, 0), ("Ayrılık Çeşmesi", 41.0010, 29.0300, 2), ("Acıbadem", 41.0010, 29.0480, 2),
        ("Ünalan", 40.9970, 29.0600, 2), ("Göztepe", 40.9930, 29.0690, 2), ("Yenisahra", 40.9870, 29.0890, 2),
        ("Kozyatağı", 40.9750, 29.0980, 2), ("Bostancı", 40.9690, 29.1030, 2), ("Küçükyalı", 40.9500, 29.1130, 2),
        ("Maltepe", 40.9390, 29.1390, 2), ("Huzurevi", 40.9280, 29.1510, 2), ("Gülsuyu", 40.9200, 29.1620, 2),
        ("Esenkent", 40.9140, 29.1700, 2), ("Hastane-Adliye", 40.9080, 29.1800, 2), ("Soğanlık", 40.9000, 29.1900, 2),
        ("Kartal", 40.8930, 29.2000, 2), ("Yakacık", 40.8970, 29.2110, 2), ("Pendik", 40.8920, 29.2300, 2),
        ("Tavşantepe", 40.8900, 29.2450, 2), ("Sabiha Gökçen Havalimanı", 40.9050, 29.3090, 8)]},
    {"id": "M5", "ad": "M5 Metro", "mod": "metro", "renk": "#682C91", "bekleme": 3, "ist": [
        ("Üsküdar", 41.0256, 29.0158, 0), ("Fıstıkağacı", 41.0270, 29.0310, 2), ("Bağlarbaşı", 41.0230, 29.0400, 2),
        ("Altunizade", 41.0225, 29.0450, 2), ("Kısıklı", 41.0230, 29.0610, 2), ("Bulgurlu", 41.0170, 29.0750, 2),
        ("Ümraniye", 41.0260, 29.0950, 2), ("Çarşı", 41.0240, 29.1030, 2), ("Yamanevler", 41.0230, 29.1170, 2),
        ("Çakmak", 41.0170, 29.1280, 2), ("Ihlamurkuyu", 41.0170, 29.1400, 2), ("Altınşehir", 41.0170, 29.1510, 2),
        ("İmam Hatip Lisesi", 41.0210, 29.1610, 2), ("Dudullu", 41.0240, 29.1700, 2), ("Necip Fazıl", 41.0210, 29.1830, 2),
        ("Çekmeköy", 41.0340, 29.1920, 3)]},
    {"id": "M7", "ad": "M7 Metro", "mod": "metro", "renk": "#F7A8C4", "bekleme": 3, "ist": [
        ("Kabataş", 41.0360, 28.9930, 0), ("Yıldız", 41.0470, 29.0080, 3), ("Fulya", 41.0590, 29.0000, 2),
        ("Mecidiyeköy", 41.0662, 28.9930, 2), ("Çağlayan", 41.0680, 28.9800, 2), ("Kağıthane", 41.0800, 28.9750, 2),
        ("Nurtepe", 41.0850, 28.9640, 2), ("Alibeyköy", 41.0780, 28.9400, 3)]},
    {"id": "T1", "ad": "T1 Tramvay", "mod": "tramvay", "renk": "#004B87", "bekleme": 3, "ist": [
        ("Kabataş", 41.0360, 28.9930, 0), ("Fındıklı", 41.0320, 28.9880, 2), ("Tophane", 41.0270, 28.9810, 2),
        ("Karaköy", 41.0222, 28.9760, 2), ("Eminönü", 41.0170, 28.9720, 2), ("Sirkeci", 41.0150, 28.9770, 2),
        ("Gülhane", 41.0130, 28.9800, 2), ("Sultanahmet", 41.0080, 28.9760, 2), ("Çemberlitaş", 41.0090, 28.9710, 2),
        ("Beyazıt", 41.0100, 28.9640, 2), ("Laleli", 41.0090, 28.9560, 2), ("Aksaray", 41.0070, 28.9480, 2),
        ("Yusufpaşa", 41.0080, 28.9420, 2), ("Fındıkzade", 41.0115, 28.9340, 2), ("Çapa", 41.0140, 28.9300, 2),
        ("Pazartekke", 41.0170, 28.9250, 2), ("Topkapı", 41.0200, 28.9200, 2), ("Cevizlibağ", 41.0140, 28.9140, 2),
        ("Zeytinburnu", 40.9970, 28.9050, 4)]},
    {"id": "F1", "ad": "F1 Füniküler", "mod": "funikuler", "renk": "#7F7F7F", "bekleme": 2, "ist": [
        ("Taksim", 41.0370, 28.9860, 0), ("Kabataş", 41.0360, 28.9930, 2)]},
]

# Vapur hatları: iskeleler + suyun içinden geçen ara noktalar (kara üstünden çizilmesin)
PIERS = {
    "Kadıköy İskelesi": (40.9928, 29.0224), "Karaköy İskelesi": (41.0210, 28.9770),
    "Eminönü İskelesi": (41.0180, 28.9740), "Beşiktaş İskelesi": (41.0418, 29.0058),
    "Üsküdar İskelesi": (41.0270, 29.0130), "Kabataş İskelesi": (41.0340, 28.9950),
}
FERRIES = [
    # (a, b, dk, ara noktalar a->b)
    ("Kadıköy İskelesi", "Karaköy İskelesi", 20, [(41.0010, 29.0095), (41.0110, 28.9930)]),
    ("Kadıköy İskelesi", "Eminönü İskelesi", 22, [(41.0010, 29.0095), (41.0100, 28.9880)]),
    ("Kadıköy İskelesi", "Beşiktaş İskelesi", 20, [(41.0010, 29.0095), (41.0140, 29.0035), (41.0310, 29.0050)]),
    ("Kadıköy İskelesi", "Kabataş İskelesi", 20, [(41.0010, 29.0095), (41.0180, 29.0000)]),
    ("Üsküdar İskelesi", "Eminönü İskelesi", 15, [(41.0230, 29.0000)]),
    ("Üsküdar İskelesi", "Karaköy İskelesi", 15, [(41.0250, 29.0000)]),
    ("Üsküdar İskelesi", "Beşiktaş İskelesi", 12, [(41.0340, 29.0100)]),
]
VAPUR_BEKLEME = 8

AKTARMA_YARICAP_M = 400   # bu mesafedeki farklı hat istasyonları arasında yürüyerek aktarma
YURUME_M_DK = 78          # m/dk (≈4.7 km/s), yol dolambacı için mesafe ×1.3


def _m(a, b) -> float:
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def net_payload() -> dict:
    """GTFS ağı (data_real/gtfs_network.json) varsa onu kullanır; GTFS'te olmayan Metrobüs
    tahminî tanımla eklenir. Dosya yoksa elle derlenmiş ana hat ağına düşer."""
    from pathlib import Path
    import json
    gtfs = Path(__file__).resolve().parent / "data_real" / "gtfs_network.json"
    if gtfs.exists():
        return _gtfs_payload(json.loads(gtfs.read_text(encoding="utf-8")))
    return _manual_payload()


def _add_transfers(nodes, edges):
    """Farklı hatlardaki yakın düğümler arası yürüyerek aktarma (+ hedef hattın beklemesi)."""
    order = sorted(range(len(nodes)), key=lambda i: nodes[i]["pt"][0])
    dlat = AKTARMA_YARICAP_M / 111000
    for x, i in enumerate(order):
        a = nodes[i]
        for j in order[x + 1:]:
            b = nodes[j]
            if b["pt"][0] - a["pt"][0] > dlat * 2.3:
                break
            if a["line"] == b["line"]:
                continue
            d = _m(a["pt"], b["pt"])
            if d <= AKTARMA_YARICAP_M or (a["ad"] == b["ad"] and d <= 900):
                w = max(2, round(d * 1.3 / YURUME_M_DK))
                edges.append([i, j, w + b["bekleme"], "aktarma", None, False, None])
                edges.append([j, i, w + a["bekleme"], "aktarma", None, False, None])


def _gtfs_payload(g: dict) -> dict:
    nodes = [dict(n, id=i) for i, n in enumerate(g["nodes"])]
    edges = [list(e) for e in g["edges"]]
    lines = {k: {"ad": v["ad"], "kisa": v["kisa"], "mod": v["mod"], "renk": v.get("renk") or "#00A3E0", "tahmini": False}
             for k, v in g["lines"].items()}
    # Metrobüs: İETT verisi GTFS'te yok -> elle tanımlı (tahminî) hat
    mb = next(L for L in LINES if L["id"] == "MB")
    lines["MB"] = {"ad": "Metrobüs", "kisa": "Metrobüs", "mod": "metrobus", "renk": mb["renk"], "tahmini": True}
    kopru = {tuple(k) for k in mb.get("kopru", [])}
    prev = None
    for ad, lat, lon, dk in mb["ist"]:
        nid = len(nodes)
        nodes.append({"id": nid, "line": "MB", "ad": ad, "pt": [lat, lon], "mod": "metrobus", "bekleme": mb["bekleme"]})
        if prev is not None:
            kp = (nodes[prev]["ad"], ad) in kopru or (ad, nodes[prev]["ad"]) in kopru
            edges.append([prev, nid, dk, "hat", "MB", kp, None])
            edges.append([nid, prev, dk, "hat", "MB", kp, None])
        prev = nid
    _add_transfers(nodes, edges)
    return {"nodes": nodes, "edges": edges, "lines": lines, "gtfs": True,
            "not": g.get("kaynak", "İBB GTFS") + " · Metrobüs tahminî (İETT GTFS'te yok)."}


def _manual_payload() -> dict:
    nodes, edges = [], []
    idx = {}

    def add_node(line, ad, lat, lon, mod, bekleme):
        nid = len(nodes)
        nodes.append({"id": nid, "line": line, "ad": ad, "pt": [lat, lon], "mod": mod, "bekleme": bekleme})
        idx[(line, ad)] = nid
        return nid

    lines_meta = {}
    for L in LINES:
        kisa = L["id"] if L["mod"] in ("metro", "tramvay", "funikuler") else {"marmaray": "Marmaray", "metrobus": "Metrobüs"}.get(L["mod"], L["ad"])
        lines_meta[L["id"]] = {"ad": L["ad"], "kisa": kisa, "mod": L["mod"], "renk": L["renk"], "tahmini": True}
        kopru = {tuple(k) for k in L.get("kopru", [])}
        prev = None
        for ad, lat, lon, dk in L["ist"]:
            nid = add_node(L["id"], ad, lat, lon, L["mod"], L["bekleme"])
            if prev is not None:
                pa = nodes[prev]["ad"]
                kp = (pa, ad) in kopru or (ad, pa) in kopru
                edges.append([prev, nid, dk, "hat", L["id"], kp, None])
                edges.append([nid, prev, dk, "hat", L["id"], kp, None])
            prev = nid

    for i, (a, b, dk, via) in enumerate(FERRIES):
        lid = f"V{i}"
        lines_meta[lid] = {"ad": f"Vapur · {a.replace(' İskelesi', '')}–{b.replace(' İskelesi', '')}", "kisa": "Vapur", "mod": "vapur", "renk": "#00A3E0", "tahmini": True}
        na = add_node(lid, a, *PIERS[a], "vapur", VAPUR_BEKLEME)
        nb = add_node(lid, b, *PIERS[b], "vapur", VAPUR_BEKLEME)
        edges.append([na, nb, dk, "hat", lid, False, [list(p) for p in via]])
        edges.append([nb, na, dk, "hat", lid, False, [list(p) for p in reversed(via)]])

    _add_transfers(nodes, edges)
    return {"nodes": nodes, "edges": edges, "lines": lines_meta, "gtfs": False,
            "not": "Ana hat ağı: yaklaşık konumlar ve tahminî süreler (GTFS değildir)."}


if __name__ == "__main__":
    n = net_payload()
    print("GTFS" if n["gtfs"] else "elle tanımlı", "·", len(n["nodes"]), "düğüm,", len(n["edges"]), "kenar,", len(n["lines"]), "hat")
    ak = sum(1 for e in n["edges"] if e[3] == "aktarma")
    print(ak, "aktarma kenarı")
