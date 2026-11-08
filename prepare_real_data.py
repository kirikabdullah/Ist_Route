"""
İst-Route · Gerçek veri ön işleme (tek seferlik)
================================================

Ham dosyaları okuyup projeye küçük JSON'lar yazar (uygulama her açılışta 140 MB
okumasın diye):

  data_real/gtfs_network.json    İBB GTFS: raylı + vapur hatları, gerçek sefer süreleri,
                                 sefer aralığından bekleme, GTFS shapes geometrisi
  data_real/rail_lines.json      Raylı Sistem Hatları Vektör Verisi (sadeleştirilmiş)
  data_real/traffic_profile.json traffic_density_202501: köprü çevresi saatlik ortalama hız

Kullanım:
    python prepare_real_data.py [ham_veri_klasörü]     (varsayılan: ~/Downloads)

Veri notları:
  * Excel'e aktarımda koordinatların ondalık ayırıcısı kaybolmuş (41083287780558 ->
    41.083287780558). fix_coord() ilk iki haneyi tam kısım kabul ederek düzeltir.
  * shape_dist_traveled alanı da bozuk ("8.49" vb.); kullanılmaz.
  * Metrobüs (İETT) GTFS'te yok; network.py'de tahminî tanımla kalır.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data_real"
RAW = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads"

RAIL_TYPES = {0: "tramvay", 1: "metro", 6: "teleferik", 7: "funikuler"}
FERRY_TYPE = 4
MARMARAY_AGENCY = 4


def fix_coord(v) -> float | None:
    """Bozulmuş koordinatı düzelt: 41083287780558 -> 41.083287780558."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        f = None
    if f is not None and abs(f) <= 180:
        return f
    digits = "".join(ch for ch in str(v).split(".")[0] if ch.isdigit())
    if len(digits) < 3:
        return None
    return float(digits[:2] + "." + digits[2:])


def hms(s) -> int | None:
    try:
        h, m, sec = (int(x) for x in str(s).strip().split(":"))
        return h * 3600 + m * 60 + sec
    except Exception:
        return None


def meters(a, b) -> float:
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def simplify(pts, tol_m=12.0):
    """Douglas–Peucker (metre toleranslı, küçük alanda düzlem yaklaşımı)."""
    if len(pts) < 3:
        return pts
    lat0 = math.radians(pts[0][0])
    xy = [(p[1] * 111320 * math.cos(lat0), p[0] * 110540) for p in pts]
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        (x1, y1), (x2, y2) = xy[i], xy[j]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1e-9
        best, bi = 0.0, -1
        for k in range(i + 1, j):
            x, y = xy[k]
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / L
            if d > best:
                best, bi = d, k
        if best > tol_m and bi > 0:
            keep[bi] = True
            stack += [(i, bi), (bi, j)]
    return [p for p, k in zip(pts, keep) if k]


def clean_stop_name(name: str, mode: str) -> str:
    n = str(name).strip()
    if mode == "vapur":
        n = n.replace(" ŞH.", "").replace(" ŞH", "").strip()
        if not n.lower().endswith("iskelesi"):
            n = f"{n} İskelesi"
    return n


def title_tr(s: str) -> str:
    def w(x):
        x = x.replace("I", "ı").replace("İ", "i").lower()
        return (x[0].replace("i", "İ").replace("ı", "I").upper() + x[1:]) if x else x
    return " ".join(w(x) for x in str(s).split())


def build_gtfs():
    print("GTFS okunuyor…")
    routes = pd.read_excel(RAW / "routes.xlsx")
    stops = pd.read_excel(RAW / "stops.xlsx")
    trips = pd.read_excel(RAW / "trips.xlsx")
    st = pd.read_excel(RAW / "stop_times.xlsx")
    shapes = pd.read_excel(RAW / "shapes.xlsx")
    print(f"  routes={len(routes)} stops={len(stops)} trips={len(trips)} stop_times={len(st)} shapes={len(shapes)}")

    routes = routes[routes.route_type.isin(list(RAIL_TYPES) + [FERRY_TYPE])].copy()
    stops["lat"] = stops.stop_lat.map(fix_coord)
    stops["lon"] = stops.stop_lon.map(fix_coord)
    # Bazı satırlar bozuk (tüm satır tek hücrede); sayısal olmayan stop_id'ler atlanır
    stops["sid"] = pd.to_numeric(stops.stop_id, errors="coerce")
    bozuk = int(stops.sid.isna().sum())
    stop_xy = {int(r.sid): (r.lat, r.lon, r.stop_name) for r in stops.itertuples()
               if pd.notna(r.sid) and r.lat and r.lon}
    print(f"  {bozuk} bozuk durak satırı atlandı")
    shapes["lat"] = shapes.shape_pt_lat.map(fix_coord)
    shapes["lon"] = shapes.shape_pt_lon.map(fix_coord)
    shape_pts = {int(sid): [[round(a, 5), round(b, 5)] for a, b in zip(g.sort_values("shape_pt_sequence").lat, g.sort_values("shape_pt_sequence").lon)]
                 for sid, g in shapes.groupby("shape_id")}

    st = st[st.trip_id.isin(trips[trips.route_id.isin(routes.route_id)].trip_id)].copy()
    st["arr"] = st.arrival_time.map(hms)
    st["dep"] = st.departure_time.map(hms)
    st = st.dropna(subset=["stop_id"])
    st["stop_id"] = st.stop_id.astype(int)
    trip_info = trips.set_index("trip_id")

    lines, seqs = {}, []
    for r in routes.itertuples():
        rtype = int(r.route_type)
        mode = "vapur" if rtype == FERRY_TYPE else ("marmaray" if int(r.agency_id or 0) == MARMARAY_AGENCY else RAIL_TYPES[rtype])
        rid = str(int(r.route_id))
        short = str(r.route_short_name).strip()
        kisa = "Marmaray" if mode == "marmaray" else ("Vapur" if mode == "vapur" else short)
        ad = (f"{kisa} · {title_tr(r.route_long_name)}" if mode != "vapur" else f"Vapur · {title_tr(r.route_long_name)}")
        rtrips = trip_info[trip_info.route_id == r.route_id]
        if rtrips.empty:
            continue
        rst = st[st.trip_id.isin(rtrips.index)]
        if rst.empty:
            continue
        # Sefer aralığı: 07:00–20:00 arası ilk duraktan kalkan sefer sayısı (yön başına)
        firsts = rst.sort_values("stop_sequence").groupby("trip_id").first()
        day = firsts[(firsts.dep >= 7 * 3600) & (firsts.dep <= 20 * 3600)]
        per_dir = max(1, len(day) / max(1, rtrips.direction_id.nunique()))
        headway = 13 * 60 / per_dir
        bekleme = int(max(1, min(25 if mode == "vapur" else 12, round(headway / 2))))
        lines[rid] = {"ad": ad, "kisa": kisa, "mod": mode, "bekleme": bekleme,
                      "renk": ("#" + str(r.route_color)) if isinstance(r.route_color, str) and len(r.route_color) == 6 else None}
        # Her yön için en çok duraklı temsilî sefer
        for dir_id, dtrips in rtrips.groupby("direction_id", dropna=False):
            cnt = rst[rst.trip_id.isin(dtrips.index)].groupby("trip_id").size()
            if cnt.empty:
                continue
            tid = cnt.idxmax()
            seq = rst[rst.trip_id == tid].sort_values("stop_sequence")
            shp = shape_pts.get(int(trip_info.loc[tid].shape_id)) if pd.notna(trip_info.loc[tid].shape_id) else None
            seqs.append((rid, mode, seq, shp))

    nodes, nidx, edges = [], {}, []

    def node(rid, mode, sid):
        lat, lon, name = stop_xy[sid]
        key = (rid, clean_stop_name(name, mode))
        if key not in nidx:
            nidx[key] = len(nodes)
            nodes.append({"line": rid, "ad": key[1], "pt": [round(lat, 5), round(lon, 5)], "mod": mode, "bekleme": lines[rid]["bekleme"]})
        return nidx[key]

    for rid, mode, seq, shp in seqs:
        rows = [r for r in seq.itertuples() if r.stop_id in stop_xy]
        if len(rows) < 2:
            continue
        # durakları şekil üzerinde sırayla eşle (monoton arama)
        idxs, k = [], 0
        if shp:
            for r in rows:
                p = stop_xy[r.stop_id][:2]
                best, bk = 1e18, k
                for j in range(k, len(shp)):
                    d = (shp[j][0] - p[0]) ** 2 + (shp[j][1] - p[1]) ** 2
                    if d < best:
                        best, bk = d, j
                idxs.append(bk); k = bk
        for i in range(1, len(rows)):
            a, b = rows[i - 1], rows[i]
            t = (b.arr if b.arr is not None else b.dep) - (a.dep if a.dep is not None else a.arr)
            if t is None or t <= 0:
                t = 60
            dk = round(max(1.0, t / 60), 1)
            na, nb = node(rid, mode, a.stop_id), node(rid, mode, b.stop_id)
            if na == nb:
                continue
            via = None
            if shp and idxs[i] > idxs[i - 1] + 1:
                via = simplify(shp[idxs[i - 1]:idxs[i] + 1], 12)[1:-1]
            edges.append([na, nb, dk, "hat", rid, False, via])

    # yinelenen kenarları tekilleştir (aynı a,b,line: en kısa süre)
    best = {}
    for e in edges:
        k = (e[0], e[1], e[4])
        if k not in best or e[2] < best[k][2]:
            best[k] = e
    edges = list(best.values())
    used = {e[4] for e in edges}
    lines = {k: v for k, v in lines.items() if k in used}
    print(f"  {len(lines)} hat, {len(nodes)} düğüm, {len(edges)} hat kenarı")
    return {"lines": lines, "nodes": nodes, "edges": edges,
            "kaynak": "İBB GTFS (Metro İstanbul, Marmaray, Şehir Hatları, Turyol, Dentur, İDO) · sefer süreleri stop_times'tan"}


def build_rail_lines():
    print("Raylı sistem vektör verisi okunuyor…")
    g = json.loads((RAW / "Raylı Sistem Hatları Vektör Verisi").read_text(encoding="utf-8"))
    out = []
    for f in g["features"]:
        pr = f["properties"]
        geom = f["geometry"]
        parts = geom["coordinates"] if geom["type"] == "MultiLineString" else [geom["coordinates"]]
        lines = [simplify([[round(c[1], 5), round(c[0], 5)] for c in part], 20) for part in parts if len(part) > 1]
        out.append({"ad": pr.get("PROJE_AD_KISA"), "tur": pr.get("PROJE_TURU"),
                    "asama": pr.get("PROJE_ASAMA"), "parcalar": lines})
    print(f"  {len(out)} hat")
    return {"hatlar": out, "kaynak": "İBB Raylı Sistem Hatları Vektör Verisi"}


BRIDGES = {
    "b1": [(41.0475, 29.0270), (41.0453, 29.0330), (41.0430, 29.0390)],   # 15 Temmuz Şehitler
    "b2": [(41.0925, 29.0540), (41.0910, 29.0610), (41.0895, 29.0680)],   # Fatih Sultan Mehmet
}


def build_traffic():
    print("Trafik yoğunluğu okunuyor (parça parça)…")
    acc = {b: defaultdict(lambda: [0.0, 0.0, 0]) for b in BRIDGES}   # saat -> [hız*araç, araç, kayıt]
    city = defaultdict(lambda: [0.0, 0])
    n = 0
    for ch in pd.read_csv(RAW / "traffic_density_202501.csv", chunksize=500_000,
                          usecols=["DATE_TIME", "LATITUDE", "LONGITUDE", "AVERAGE_SPEED", "NUMBER_OF_VEHICLES"]):
        n += len(ch)
        ts = pd.to_datetime(ch.DATE_TIME)
        ch = ch[ts.dt.dayofweek < 5]          # yalnızca hafta içi (uygulama "hafta içi" simüle eder)
        hours = pd.to_datetime(ch.DATE_TIME).dt.hour
        for h, v in ch.groupby(hours).AVERAGE_SPEED.mean().items():
            city[h][0] += v; city[h][1] += 1
        box = ch[(ch.LATITUDE.between(41.03, 41.10)) & (ch.LONGITUDE.between(29.02, 29.07))]
        for b, pts in BRIDGES.items():
            dmin = None
            for p in pts:
                d = ((box.LATITUDE - p[0]) * 111000) ** 2 + ((box.LONGITUDE - p[1]) * 84000) ** 2
                dmin = d if dmin is None else dmin.where(dmin < d, d)
            sel = box[dmin <= 700 ** 2]
            if sel.empty:
                continue
            sh = pd.to_datetime(sel.DATE_TIME).dt.hour
            w = sel.NUMBER_OF_VEHICLES.clip(lower=1)
            for h, grp in sel.assign(h=sh, w=w).groupby("h"):
                acc[b][h][0] += (grp.AVERAGE_SPEED * grp.w).sum()
                acc[b][h][1] += grp.w.sum()
                acc[b][h][2] += len(grp)
    prof = {}
    for b in BRIDGES:
        prof[b] = {str(h): round(acc[b][h][0] / acc[b][h][1], 1) for h in range(24) if acc[b][h][1] > 0}
    prof["sehir"] = {str(h): round(city[h][0] / city[h][1], 1) for h in range(24) if city[h][1]}
    kayit = {b: sum(acc[b][h][2] for h in acc[b]) for b in BRIDGES}
    print(f"  {n} satır okundu; köprü kayıtları {kayit}")
    return {"saatlik_ort_hiz_kmh": prof, "kayit_sayisi": kayit,
            "kaynak": "İBB traffic_density_202501 · Ocak 2025 hafta içi, köprü çevresi ~700 m hücreler, araç sayısı ağırlıklı ortalama"}


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for fn, builder in [("gtfs_network.json", build_gtfs), ("rail_lines.json", build_rail_lines), ("traffic_profile.json", build_traffic)]:
        data = builder()
        (OUT / fn).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  -> {OUT / fn} ({(OUT / fn).stat().st_size / 1024:.0f} KB)")
