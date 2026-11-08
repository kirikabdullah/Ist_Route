# İst-Route 🚇

**Akıllı ulaşım ve teşvik prototipi** · İBB Future İstanbul Datathon

İst-Route her yolculuk için üç rota önerir: **Hızlı**, **Konforlu** ve **Sosyal Mola**. Her rota iki eksende puanlanır: yolcunun kendi faydası ve şehrin trafik yükü. Amaç, yolcuyu zirve saatte tıkalı köprü arterlerinden uzaklaştırmak. Teşvik olarak, o saatte açık bir İBB noktasında (Kent Lokantası, spor tesisi, müze) verilen molaya İstanbulkart puanı kazandırılır.

```
Toplam Skor = 0.55 · S_ind  +  0.45 · S_soc
              (bireysel)       (şehir / sosyal)
```

> Bu proje datathon'a katılan bağımsız bir takımın prototipidir. İBB ile resmi bir iş birliği ya da onay yoktur.

---

## Özellikler

- **3 rota kartı ve skor dökümü.** Her önerinin gerekçesi bileşenleriyle gösterilir.
- **Kalkış/varış saati seçimi.** 06:00–23:30 arası, yarım saatlik adımlarla.
- **Kriz senaryoları:** Normal, Lodos (vapur iptali), Derbi (stadyum kalabalığı).
- **Dinamik yolculuk.** İstasyon, iskele ya da POI araması, GPS veya ters çevirme ile kalkış/varış seçimi. Rota tarayıcıda Dijkstra ile hesaplanır.
- **Canlı yolculuk simülasyonu.** Ulaşım kurallarına uyar: vapurdayken rota değişmez, yalnızca iskelede değişir.
- **Aile Modu.** Ana karttan çocukların bakiyesini izleme ve otomatik yükleme.
- **POI katmanları:** 19 Kent Lokantası, 23 spor tesisi, 48 İBB müzesi.
- **İst-Route Asistanı.** Yanıtlarını uygulamanın kendi verisinden kurar ve API anahtarı olmadan çalışır. Bakiye riskini tarayıcıda çalışan bir PyTorch modeliyle (RiskMLP) tahmin eder. `GOOGLE_API_KEY` tanımlıysa yanıtlar Gemini ile doğallaştırılır.
- **Web ve mobil arayüz.** İkisi de aynı motoru (`ui/engine.js`) ve aynı asistanı (`ui/assistant.js`) kullanır.

---

## Hızlı Başlangıç

### 1. Sunucusuz demo (kurulum gerektirmez)

Aşağıdaki dosyaları tarayıcıda doğrudan açmanız yeterli:

- `ist_route_demo.html`: masaüstü arayüz
- `ist_route_mobile.html`: mobil arayüz

GPS yalnızca bu tek dosyalık demolarda çalışır.

### 2. Streamlit ile çalıştırma

```bash
python -m venv .venv
```

```bash
.venv\Scripts\pip install streamlit pandas numpy
```

```bash
.venv\Scripts\python -m streamlit run app.py
```

- Masaüstü: http://localhost:8501
- Mobil: http://localhost:8501/?view=mobile

Mobil arayüzü tek tıkla açmak için `IST-ROUTE_MOBIL_BASLAT.bat` dosyasını çalıştırabilirsiniz. Telefondan erişmek için telefonla bilgisayarın aynı Wi-Fi ağında olması gerekir. Adres: `http://BILGISAYAR-IP:8501/?view=mobile`.

### 3. (İsteğe bağlı) AI asistanı ve Gemini

```bash
.venv\Scripts\pip install -r taha/requirements.txt
```

Gemini ile doğallaştırma için `GOOGLE_API_KEY` ortam değişkenini ya da `.streamlit/secrets.toml` dosyasını ayarlayın:

```toml
GOOGLE_API_KEY = "..."
```

Anahtar yalnızca sunucuda kalır, tarayıcıya gönderilmez. Varsayılan model `GEMINI_MODEL`, yedek modeller `GEMINI_FALLBACK_MODELS` ortam değişkeniyle değiştirilebilir.

---

## Proje Yapısı

```
ist_route/
├── app.py                    Streamlit kabuğu (yalnızca başlatıcı; arayüz tam ekran iframe)
├── scoring_engine.py         Skor motoru: senaryoları önceden hesaplar, HTML'i derler
├── network.py                Ana hat istasyon ağı (yaklaşık konum, tahminî süre)
├── poi_loader.py             Kent Lokantası / spor tesisi / müze verisini tek şemaya indirger
├── prepare_real_data.py      Ham GTFS, raylı hat ve trafik verisini küçük JSON'lara çevirir
├── export_risk_model.py      PyTorch RiskMLP modelini eğitip tarayıcı için JSON'a yazar
├── ui/
│   ├── index.html            Masaüstü arayüz şablonu (Leaflet)
│   ├── mobile.html           Mobil arayüz şablonu
│   ├── engine.js             Ortak rota motoru (Dijkstra vb.)
│   └── assistant.js          Ortak asistan mantığı
├── data_real/                Ön işlenmiş gerçek veri (GTFS ağı, raylı hatlar, trafik, risk modeli)
├── cache/osrm_cache.json     Önbelleğe alınmış OSRM rota geometrileri
├── taha/                     AI asistan modülü (assistant_widget.py, bkz. taha/INTEGRATION.md)
├── video/                    Mobil tanıtım videosu otomasyonu (Playwright + FFmpeg)
├── ist_route_demo.html       Dışa aktarılmış tek dosyalık masaüstü demo
└── ist_route_mobile.html     Dışa aktarılmış tek dosyalık mobil demo
```

---

## Geliştirici Komutları

**Skor motorunu test et** (senaryo özetlerini konsola yazar):

```bash
python scoring_engine.py
```

**Tek dosyalık demoları yeniden üret** (`ist_route_demo.html` ve `ist_route_mobile.html`):

```bash
python scoring_engine.py --export
```

OSRM'e bağlanmadan, yalnızca önbellekle çalıştırmak için komutun sonuna `--offline` ekleyin.

**Gerçek veriyi yeniden hazırla** (tek seferlik; ham veri klasörü varsayılan olarak `~/Downloads`):

```bash
python prepare_real_data.py "C:\yol\ham_veri"
```

**Risk modelini yeniden dışa aktar:**

```bash
.venv\Scripts\python.exe export_risk_model.py
```

**Tanıtım videosunu üret:**

```bash
cd video && npm install && node make_video.mjs
```

> **Not:** `poi_loader.py`, POI CSV'lerini proje klasörünün bir üstündeki `../data_poi/` klasöründen okur (`tum_kent_lokantalari.csv`, `tum_spor_tesisleri.csv`, `tum_ibb_muzeleri.csv`).

---

## Veri Kaynakları ve Dürüstlük Notu

İst-Route gerçek veri ile simülasyonu birbirinden ayırır ve arayüzde de ayrı etiketler.

**Gerçek veri**

| Bileşen | Kaynak |
|---|---|
| Raylı sistem ve vapur süreleri | İBB GTFS `stop_times` |
| Rota geometrisi | GTFS `shapes`, OSRM |
| Raylı ağ katmanı | İBB Raylı Sistem Hatları Vektör Verisi |
| Köprü hızları | `traffic_density_202501` (Ocak 2025, hafta içi saatlik ortalama) |
| POI'ler | İBB Kent Lokantaları, Spor Tesisleri, Müzeler |

**Tahminî / temsilî**

- Metrobüs süreleri (İETT verisi GTFS'te yok)
- Müze koordinatları (adresten elle çıkarılmış yaklaşık konumlar)
- Biniş ücretleri (tam 30 ₺, öğrenci 15 ₺, aktarmada %60)
- Aile üyeleri ve bakiyeler
- Kriz senaryoları ve duyuru metinleri
- Skor ağırlıklarının alt bileşenleri

Ürün tanımı, ilkeler ve açık kararlar için bkz. [PRODUCT.md](PRODUCT.md).

---

## Varsayılan Demo Senaryosu

Saat **18:00**, **Mecidiyeköy → Kalamış Sahili**. Bu saatte 1. ve 2. Köprü yoğundur. Sosyal Mola rotası, yolcuyu açık bir İBB tesisinde mola verdirerek zirve saatten sonra yola çıkarır ve İstanbulkart puanı kazandırır.
