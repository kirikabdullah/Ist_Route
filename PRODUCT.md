# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

Masaüstü tarayıcı (jüri sunumu) ve mobil tarayıcı (yolcu kullanımı) aynı tek sayfa uygulamada. Native uygulama yok.

## Users

**Birincil kullanıcı: İstanbullu yolcu.** Zirve saatlerde (08:00–09:30, 17:00–19:30) işe/eve giden, İstanbulkart kullanan kişi. Durum: kalkıştan önce ya da yolculuk sırasında, telefonda hızlıca karar veriyor. İş: "Şu an hangi rotayla gideyim?" sorusuna süre, konfor ve kazanç (puan) dengesiyle cevap almak.

İkincil kullanıcı: aile bütçesini yöneten ebeveyn (Aile Modu). Çocukların İstanbulkart bakiyesini ana karttan izler ve otomatik yükleme kurar.

İzleyici, kullanıcı değil: İBB Future İstanbul Datathon jürisi. Ürünü yolcunun deneyimi üzerinden değerlendirir. Tasarım kararları yolcuya göre verilir, jüri bu deneyimi izler.

## Product Purpose

İst-Route, her yolculuk için üç rota önerir: Hızlı, Konforlu ve Sosyal Mola. Her rota iki eksende puanlanır: yolcunun bireysel faydası ve şehrin trafik yükü. Amaç, yolcuyu tıkalı köprü arterlerinden ve zirve saat yığılmasından uzaklaştırmak. Teşvik aracı, İBB noktalarında (Kent Lokantası, Spor Tesisi, müze) verilen molaya bağlı İstanbulkart Plus puanı.

Başarı: Yolcu, zirve saatte şehre yük olmayan rotayı kendi çıkarına da uygun bulup seçer. Jüri, bu seçimin veriyle gerekçelendirildiğini görür.

## Positioning

Sıradan bir rota planlayıcısı süreyi optimize eder. İst-Route ise süreyi şehir etkisiyle birlikte puanlar:

**Toplam = 0.55 · S_ind + 0.45 · S_soc**

Mola noktası, o saatte gerçekten açık olan İBB tesisleri arasından dinamik seçilir. Kazanılan puan, İBB'nin kapalı çevrim ekosisteminde harcanır. Trafik dağıtma, kamu tesisi kullanımı ve teşvik tek bir mekanizmada birleşiyor.

## Operating Context

- Kullanım anı: kalkış öncesi rota seçimi ve yolculuk sırasında canlı takip (simülasyon).
- Şehir koşulları ürünün parçasıdır: zirve saat, 1./2. Köprü yoğunluğu, lodos nedeniyle vapur iptali, stadyum (derbi) kalabalığı.
- Ulaşım fiziği kuralları: açık denizde (vapurda) rota değişmez, yalnızca iskelede değişir. Aktarmada indirimli ücret uygulanır.
- Sunum ritüeli: datathon jüri demosu. Varsayılan senaryo saat 18:00, Mecidiyeköy → Kalamış Sahili.

## Capabilities and Constraints

**Mevcut yetenekler:**
- 3 rota kartı ve skor dökümü
- 06:00–23:30 arası yarım saatlik kalkış seçimi
- Kriz senaryoları (Normal / Lodos / Derbi)
- Canlı yolculuk simülasyonu
- Aile Modu (ana kart + alt kartlar, otomatik yükleme)
- Kapalı Çevrim puan kuralı
- POI katmanları (19 Kent Lokantası, 23 Spor Tesisi, 48 İBB müzesi)

**Teknik yapı:**
- `scoring_engine.py`: Python skor motoru; senaryolar önceden hesaplanır, OSRM rotaları önbellekli.
- `ui/index.html`: tek sayfa, Leaflet tabanlı arayüz.
- `app.py`: Streamlit yalnızca başlatıcı kabuk.
- `ist_route_demo.html`: sunucusuz tek dosya demo.

**Terminoloji:** Bireysel Skor (S_ind), Sosyal/Şehir Skoru (S_soc), İBB Puanı, Kapalı Çevrim, Ana Kart / alt kart, mola noktası, zirve saat.

**Dinamik yolculuk (Faz B):** Kalkış ve varış; istasyon, iskele ve POI aramasıyla, GPS ile ya da ters çevirerek seçilir. "Kalkış saati" ve "Varış saati" modları vardır.
- Örnek yolculuk dışındaki her yolculuk `network.py` ana hat ağında (tarayıcıda Dijkstra) hesaplanır.
- Ağ yaklaşık konum ve tahminî sürelerden oluşur; GTFS değildir ve arayüzde öyle etiketlenir.
- GPS yalnızca tek dosyalık demoda çalışır; Streamlit iframe'i konum iznini vermez.

**Gerçek veri (C1–C3):** Kullanıcı kararıyla, örnek yolculuk dahil tüm rotalar gerçek veriyle hesaplanır. Brief'teki 38 / 46 / 42 + 45 dk değerleri artık bağlayıcı değildir.
- **Süreler:** İBB GTFS (raylı ve vapur) `stop_times`'tan gelir.
- **Geometri:** GTFS `shapes`'ten gelir.
- **Raylı ağ katmanı:** İBB Raylı Sistem Hatları Vektör Verisi'nden çizilir.
- **Köprü hızları:** `traffic_density_202501`'den (Ocak 2025, hafta içi saatlik ortalama) gelir.
- **Hazırlık:** Ön işleme `prepare_real_data.py` ile yapılır, çıktısı `data_real/` klasörüne yazılır.
- **Metrobüs:** İETT verisi GTFS'te olmadığından süreleri tahminî kalır.

**Karar verildi, kısmen uygulandı:** GTFS, raylı ağ ve trafik verisi bağlandı (yukarıda). Datathon müşteri veri setleri ürüne henüz bağlanmadı. Bu dosyalar:
- `../data_csv/` altındakiler: harcama, ulaşım, mobil, müşteri profili, `koridor_trafik_ozeti.csv`, `ulasim_trafik_entegreli.csv`
- Kök dizindeki Kapalı Çevrim kart kullanımı ve Açık Çevrim Plus harcama dosyaları

Hangi skor bileşenini hangi verinin besleyeceği açık bir karardır.

**İst-Route Asistanı (hibrit):** Harita içinde, anahtarsız çalışır.
- **Kaynak:** Yanıtlar yalnızca uygulamanın verisinden kural tabanlı kurulur: GTFS rota motoru, POI, trafik, senaryo, cüzdan.
- **Bakiye riski:** `export_risk_model.py`, Taha'nın PyTorch RiskMLP modelini eğitir. Model `data_real/risk_model.json` olarak tarayıcıda çalışır.
- **Gemini:** Streamlit'te `GOOGLE_API_KEY` varsa taslak, yeni bilgi eklenmeden doğallaştırılır. Anahtar tarayıcıya gitmez.
- **Taha'nın modülü:** `taha/assistant_widget.py` değiştirilmeden "…" menüsünden isteğe bağlı açılır.

**Mobil arayüz:** `ui/mobile.html` dosyası ayrı bir şablondur ve `ist_route_mobile.html` olarak dışa aktarılır.
- **Tasarım sistemi:** Kullanıcının verdiği Tailwind yapılandırması kullanılır:
  - Inter yazı tipi, marka rengi `#C1125A`
  - İstanbulkart mavisi ve camgöbeği `#0A7EB9` / `#00CCFF`
  - `ui` gri tonları ve heading/title/body/description/caption yazı boyutları
- **Ortak kod:** Web ve mobil aynı motoru (`ui/engine.js`) ve asistan beynini (`ui/assistant.js`) derleme sırasında içine alır.
- **Renk kuralı:** Rota renkleri (kırmızı, mavi, sarı) ve çocuk renkleri iki arayüzde de aynıdır.

## Brand Commitments

- **Ürün adı:** İst-Route.
- **Kurumsal ilişki:** Takım, İBB Future İstanbul Datathon'una katılan bağımsız bir takımdır; İBB ile resmi iş birliği yoktur. Resmi İBB / "İstanbul Senin" logosu kullanılmaz, onay ya da resmi veri kaynağı iddiasında bulunulmaz. Kaynak etiketleri (ör. AKOM, Şehir Hatları duyurusu) simülasyon olduğu açıkça belirtilmeden gösterilmez.
- **Kurumsal renkler (kullanıcı brief'inde sabitlendi):** İBB renkleri ilham olarak kullanılır:
  - `#0B2545` lacivert
  - `#00A3E0` camgöbeği
  - `#E30613` kırmızı
  - `#FBB034` sarı
  - `#F8FAFC` zemin
- **Dil:** Türkçe arayüz.

## Evidence on Hand

**Gerçek veri:**
- `../data_poi/tum_kent_lokantalari.csv`: 19 lokanta, koordinat ve saatlerle.
- `../data_poi/tum_spor_tesisleri.csv`: 23 tesis, koordinat ve branşlarla.
- `../data_poi/tum_ibb_muzeleri.csv`: 48 müze. Koordinat yok; `poi_loader.MUZE_KOORDINAT` içindeki konumlar adresten elle çıkarılmış yaklaşık değerlerdir.
- `../data_csv/` ve kök dizindeki datathon Excel/CSV dosyaları (henüz ürüne bağlı değil).
- OSRM rota geometrileri: `cache/osrm_cache.json`.

**Simülasyon ya da temsilî olanlar (gerçek gibi sunulmamalı):**
- Ara saatlerin köprü hız profili. Yalnızca 08/09/13/18/19/23 değerleri önceki ölçümden gelir, gerisi interpolasyondur.
- Biniş ücretleri: tam 30 ₺, öğrenci 15 ₺, aktarmada %60.
- Aile üyeleri ve bakiyeler.
- Kriz senaryoları ve duyuru metinleri.
- Rota bacak süreleri.
- Skor ağırlıklarının alt bileşenleri.

**Yok, uydurulmamalı:** Halk Ekmek ve İBB Sosyal Tesisleri konum verisi; kullanıcı yorumu ya da referans; benimsenme oranı veya trafik azaltma etkisi ölçümü; İBB onayı.

## Product Principles

1. **Yolcunun çıkarı ile şehrin çıkarını aynı kararda buluştur.** Şehre iyi gelen rota, yolcuya da somut bir kazanç (puan, konfor, öngörülebilirlik) sunmalı. Fedakârlık istenmez.
2. **Her öneri gerekçesini gösterir.** Skor, bileşenleriyle birlikte açıklanır; kara kutu öneri yoktur.
3. **Gerçek ile simülasyonu ayır.** Veri kaynaklı değer ile temsilî değer kullanıcıya ve jüriye karıştırılmadan sunulur.
4. **Şehir koşullarına dürüst tepki.** Kapalı tesis, iptal sefer ya da kalabalık olduğunda öneri değişir. Var olmayan seçenek sunulmaz.
5. **Fiziksel gerçekliğe uy.** Ulaşım kuralları (denizde rota kilidi, aktarma, açılış saatleri) arayüzün davranışını belirler.

## Accessibility & Inclusion

Ürüne özel bir standart henüz belirlenmedi (açık karar). Mevcut uygulama klavyeyle rota seçimini, `prefers-reduced-motion` desteğini ve mobil dokunmatik kullanımı içeriyor.
