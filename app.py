"""
İst-Route · Streamlit kabuğu
Streamlit yalnızca sunucu/başlatıcı olarak kullanılır: tüm varsayılan Streamlit
arayüzü gizlenir ve ekranın tamamına ui/index.html'deki harita uygulaması basılır.

Harita çift yönlü bir Streamlit bileşenidir: seçili rota / yolculuk / saat değişince
rotanın özetini Python'a gönderir. Bu özet, taha/assistant_widget.py'deki AI
asistanına (PyTorch risk modeli + Gemini) `route_context` olarak verilir.

    streamlit run app.py
    (AI yanıtları için: GOOGLE_API_KEY ortam değişkeni ya da .streamlit/secrets.toml)
"""
from pathlib import Path
import sys

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scoring_engine import build_payload, render_html  # noqa: E402

st.set_page_config(page_title="İst-Route · Akıllı Ulaşım & Teşvik Prototipi", page_icon="🚇",
                   layout="wide", initial_sidebar_state="collapsed")

# Streamlit görünümünü tamamen kaldır; harita iframe'ini ekranın tamamına yay.
st.markdown("""
<style>
  header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
  [data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stStatusWidget"],
  footer, #MainMenu { display:none !important; }
  html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background:#F8FAFC !important; overflow:hidden !important; }
  .block-container, [data-testid="stMainBlockContainer"] { padding:0 !important; max-width:100% !important; }
  [data-testid="stVerticalBlock"] { gap:0 !important; }
  iframe[title="st.iframe"], iframe[title="streamlit_components_v1.html"], iframe[title="ist_route_map"],
  [data-testid="stIFrame"], [data-testid="stCustomComponentV1"], .stElementContainer iframe {
    position:fixed !important; inset:0 !important; width:100vw !important; height:100vh !important;
    border:0 !important; z-index:999 !important; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- AI asistanı
ASSISTANT_DIR = ROOT / "taha"
assistant_error = None
render_assistant = None
if (ASSISTANT_DIR / "assistant_widget.py").exists():
    sys.path.insert(0, str(ASSISTANT_DIR))
    try:
        from assistant_widget import render_assistant  # noqa: E402
    except Exception as e:  # torch / langchain kurulu değilse harita yine çalışır
        assistant_error = f"{type(e).__name__}: {e}"


@st.cache_data(show_spinner="İst-Route skor motoru hazırlanıyor…")
def _payload() -> dict:
    return build_payload(online=True)


@st.cache_data(show_spinner=False)
def _build_component(template: str = "index.html") -> str:
    """Şablonu (web: index.html, mobil: mobile.html) veriyle derleyip bileşen klasörüne yazar."""
    out_dir = ROOT / ".build" / ("map_component_mobile" if template == "mobile.html" else "map_component")
    out_dir.mkdir(parents=True, exist_ok=True)
    html = render_html(_payload(), template)
    f = out_dir / "index.html"
    if not f.exists() or f.read_text(encoding="utf-8") != html:
        f.write_text(html, encoding="utf-8")
    return str(out_dir)


# ---------------------------------------------------------------- Gemini (isteğe bağlı)
# Harita içindeki İst-Route Asistanı yanıtlarını her zaman veriden, anahtarsız kurar.
# GOOGLE_API_KEY varsa bu taslak, yeni bilgi eklenmeden Gemini ile doğallaştırılır.
# Anahtar yalnızca sunucuda kalır; tarayıcıya gönderilmez.
def _api_key() -> str:
    import os
    k = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not k:
        try:
            k = str(st.secrets.get("GOOGLE_API_KEY", "") or "").strip()
        except Exception:
            k = ""
    return "" if k.upper().startswith("BURAYA") else k


REPHRASE_PROMPT = (
    "Sen İst-Route uygulamasının ulaşım asistanısın. Aşağıdaki TASLAK yanıt uygulamanın gerçek verisinden "
    "üretildi. Onu samimi ve akıcı Türkçeyle yeniden yaz. KURALLAR: tüm sayıları, saatleri, hat ve durak "
    "adlarını aynen koru; yeni bilgi, hat, durak, indirim, kampanya ya da marka ekleme; sıralı adımlar varsa "
    "numaralı satırlar olarak bırak; en fazla 6 cümle/satır. Yalnızca yeniden yazılmış yanıtı döndür.\n\n"
    "Kullanıcının sorusu: {q}\n\nTASLAK:\n{draft}"
)


def _gemini_rephrase(key: str, q: str, draft: str) -> str:
    import os
    from langchain_google_genai import ChatGoogleGenerativeAI
    models = [os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")] + [
        m.strip() for m in os.environ.get("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash").split(",") if m.strip()]
    for name in dict.fromkeys(models):
        try:
            llm = ChatGoogleGenerativeAI(model=name, google_api_key=key, temperature=0.3,
                                         max_output_tokens=700, timeout=30, max_retries=1)
            out = llm.invoke(REPHRASE_PROMPT.format(q=q, draft=draft)).content
            if isinstance(out, list):
                out = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in out)
            if str(out).strip():
                return str(out).strip()
        except Exception as e:  # kota / model adı / ağ: sıradaki modeli dene
            print(f"[İst-Route] Gemini ({name}) başarısız: {type(e).__name__}: {str(e)[:160]}",
                  file=sys.stderr, flush=True)
    return ""


API_KEY = _api_key()
try:
    import langchain_google_genai  # noqa: F401
    GEMINI_OK = bool(API_KEY)
except Exception:
    GEMINI_OK = False

replies = st.session_state.setdefault("ai_replies", {})
# Mobil arayüz: http://localhost:8501/?view=mobile  (IST-ROUTE_MOBIL_BASLAT.bat)
MOBILE = str(st.query_params.get("view", "")).lower() in ("mobile", "mobil", "m")
if MOBILE:
    ist_route_map = components.declare_component("ist_route_mobile", path=_build_component("mobile.html"))
    value = ist_route_map(key="harita_mobil", default=None, gemini=GEMINI_OK, replies=replies) or {}
else:
    ist_route_map = components.declare_component("ist_route_map", path=_build_component("index.html"))
    value = ist_route_map(key="harita", default=None, gemini=GEMINI_OK,
                          taha_var=render_assistant is not None, replies=replies) or {}

ask = value.get("ask") if isinstance(value, dict) else None
if GEMINI_OK and ask and ask.get("id") and ask["id"] not in replies:
    replies[ask["id"]] = _gemini_rephrase(API_KEY, str(ask.get("q", "")), str(ask.get("draft", "")))
    st.rerun()   # yanıtı bileşene argüman olarak ilet

if render_assistant is not None and value.get("taha") and not MOBILE:
    try:
        render_assistant(route_context=value.get("route_context"), key_prefix="harita_asistan",
                         show_profile_controls=True)
    except Exception as e:
        print(f"[İst-Route] Taha'nın asistanı yüklenemedi: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
elif assistant_error:
    print(f"[İst-Route] Taha'nın asistanı devre dışı ({assistant_error}). "
          "Kurulum: .venv içinde pip install -r taha/requirements.txt", file=sys.stderr, flush=True)
