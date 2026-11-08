"""
İst-Route · PyTorch risk modelini tarayıcı için dışa aktarır
============================================================

Taha'nın taha/assistant_widget.py modülündeki train_model() fonksiyonunu
(DEĞİŞTİRMEDEN) çağırır: aynı veri (musteri_profili_ortak.csv), aynı PyTorch
RiskMLP (5 -> 16 -> 8 -> 1) eğitimi. Eğitilen ağırlıklar, MinMax ölçekleyici ve
kategori kodlamaları data_real/risk_model.json'a yazılır; harita içindeki
asistan aynı ileri geçişi JS'te yapar (anahtarsız, sunucusuz).

    .venv\\Scripts\\python.exe export_risk_model.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "taha"))
logging.getLogger("streamlit").setLevel(logging.ERROR)

import assistant_widget as aw  # noqa: E402  (Taha'nın modülü, değiştirilmedi)


def main() -> None:
    model, scaler, encoders, metrics, stats = aw.train_model()
    default = aw.get_default_profile(encoders, stats)
    layers = []
    for m in model.net:
        if hasattr(m, "weight"):
            layers.append({"W": m.weight.detach().numpy().round(6).tolist(),
                           "b": m.bias.detach().numpy().round(6).tolist()})
    out = {
        "features": aw.FEATURES,
        "cat_cols": aw.CAT_COLS,
        "log1p": ["h_ort_harcama"],
        "classes": {c: [str(x) for x in encoders[c].classes_] for c in aw.CAT_COLS},
        "scaler": {"scale": scaler.scale_.round(8).tolist(), "min": scaler.min_.round(8).tolist()},
        "layers": layers,                       # Linear, ReLU, Linear, ReLU, Linear -> sigmoid
        "threshold": aw.RISK_THRESHOLD,
        "default_profile": default,
        "stats": stats,
        "metrics": {k: v for k, v in metrics.items() if k != "losses"},
        "kaynak": "PyTorch RiskMLP · musteri_profili_ortak.csv · taha/assistant_widget.train_model",
    }
    dst = ROOT / "data_real" / "risk_model.json"
    dst.parent.mkdir(exist_ok=True)
    dst.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    # doğrulama: PyTorch ile JS'in kullanacağı formülün aynı sonucu verdiğini kontrol et
    p = default
    risk_torch = aw.predict_risk(model, scaler, encoders, p["yas_grubu"], float(p["h_ort_harcama"]),
                                 int(p["h_aktif_gun"]), p["h_en_sik_mcc"], int(p["m_giris_sayisi"]))
    print(f"Yazıldı: {dst} ({dst.stat().st_size / 1024:.1f} KB)")
    print(f"Metrikler: doğruluk {metrics['accuracy']:.3f}, ROC-AUC {metrics['roc_auc']:.3f}, satır {metrics['n_rows']}")
    print(f"Varsayılan profil {p} -> PyTorch risk {risk_torch:.4f}")


if __name__ == "__main__":
    main()
