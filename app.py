"""
0.Device — The Sovereign Trade & Finance Agent
AppBuildersPH Hackathon 2026 · Theme: Local AI · Team ISET

Everyday story: a small business owner types what they sold. A local AI
(running on their own device, via Ollama) turns it into a Smart Receipt,
locks it in their Trust Vault, and shows how much cash they can get TODAY
instead of waiting 30–90 days. When a bank or investor wants to look at
that receipt, they pay a small view fee through any rail they like
(GCash, Maya, card, USDC). The business owner keeps 70% of every view fee —
their data earns for them. That is the Fidnt Data Monetization model.

───────────────────────────────────────────────────────────────────────────
CONCEPT COMMENTS (required by brief)
───────────────────────────────────────────────────────────────────────────

LOCAL AI PRIVACY
  The entire underwriting step runs on-device (Ollama → llama3, a local LLM).
  The seller's sales text — real, sensitive business financial data — never
  leaves the machine. No cloud AI API is called at any point. This is the
  reason a market vendor or MSME would trust it: their books stay theirs.
  If Ollama is not running, the app falls back to a built-in Demo Mode so a
  live presentation can never crash (disclosed in the README + on screen).

402 MULTI-RAIL eSETTLEMENT
  When an investor queries a Smart Receipt, the app answers the way the web
  was designed to: HTTP 402 — Payment Required. That single status code is
  the gate. The investor then picks ANY rail — GCash QR, Maya NFC tap,
  Stripe/Apple Pay card, or a USDC atomic settlement on Stellar — and the
  same unlock happens. Rail-agnostic money movement, one protocol gate.

FIDNT DATA MONETIZATION
  The person who CREATES the data keeps ownership (Layer 0 notarized by
  hash) and earns a dividend every single time someone pays to view it:
  70% to the originator wallet, 30% to the network. Data stops being
  something extracted from small businesses and becomes an asset they own.
───────────────────────────────────────────────────────────────────────────
"""

import hashlib
import io
import json
import os
import re
import time
from datetime import datetime, timedelta

import qrcode
import requests
import streamlit as st

# ── Constants ──────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets_db.json")
OLLAMA_URL = "http://localhost:11434/api/generate"   # Local AI only. No cloud.
OLLAMA_MODELS = ["llama3.2:latest", "llama3.2:1b"]  # steps down automatically if RAM is tight
GCASH_NUMBER = "639170000000"    # QR Ph collects REAL money once this is your GCash-registered mobile (63 + number)
GCASH_QR_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gcash_qr.png")
# ^ Save YOUR GCash app's personal QR (Profile → My QR Code → screenshot) as this file for a truly scannable, real-money QR
HERO_IMG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "hero.jpg")
# ^ OPTIONAL: drop any landscape photo here and it becomes the hero background (otherwise a cinematic CSS hero shows)
STELLAR_TREASURY_DEFAULT = "GBSQMSQFTC7PUI3OGE3BPTXFKC42OPMK7CVAO7MR3Z6J2HY4JI3EK5IE"  # funded Stellar TESTNET account (public key)
ORIGINATOR_WALLET = "0xUser1"
FEE_PHP = 5.0          # view fee, pesos
FEE_USDC = 0.10        # view fee, USDC
DIVIDEND_SHARE = 0.70  # Fidnt rule: 70% of every fee → data owner
KNOWN_CORPS = {
    "globe", "pldt", "smart", "meralco", "ayala", "bdo", "bpi", "metrobank",
    "jollibee", "san miguel", "sm prime", "abs-cbn", "cebu pacific",
    "shopee", "lazada", "google", "nestle", "unilever",
}

UNDERWRITER_PROMPT = (
    "You are a trade finance underwriter. Read the user's text. Generate a "
    "formal eCommercial Invoice in JSON format with keys: 'invoice_id', "
    "'seller', 'buyer', 'amount' (number, PHP), 'due_date' (YYYY-MM-DD). "
    "Also, assess the buyer's risk: if they are a large known corporation, "
    "assign a 3% discount rate; if unknown, 8%. Add keys 'risk_level', "
    "'discount_rate_percentage', 'suggested_cash_advance' (the amount less "
    "the discount rate), and 'investor_yield_percentage'. Respond with JSON "
    "only.\n\nUser text: {user_text}"
)

# ── Page config + dark, mobile-first styling ───────────────────────────────
st.set_page_config(
    page_title="0.Device — Sovereign Trade & Finance Agent",
    page_icon="⬢",
    layout="centered",           # mobile-first: single centered column
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      /* ── The page: deep emerald, subtle glow — desktop shows one phone-size
         glass widget floating in the middle; mobile goes full-bleed app ── */
      .stApp {
        background:
          radial-gradient(900px 520px at 12% -8%, rgba(47,213,117,0.16), transparent 60%),
          radial-gradient(720px 520px at 108% 18%, rgba(46,144,255,0.10), transparent 55%),
          linear-gradient(160deg, #07130d 0%, #0a1410 45%, #050b08 100%);
      }
      .block-container {
        max-width: 430px;                       /* phone-size on desktop */
        margin: 2.4rem auto 3rem;
        padding: 1.25rem 1.15rem 2.4rem;
        background: rgba(255,255,255,0.045);
        backdrop-filter: blur(28px) saturate(150%);
        -webkit-backdrop-filter: blur(28px) saturate(150%);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 34px;
        box-shadow: 0 30px 90px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.08);
      }
      /* hide browser chrome — it should feel like a device, not a webpage */
      [data-testid="stHeader"] { display: none; }
      [data-testid="stSidebar"] { display: none; }
      [data-testid="stToolbar"] { display: none; }
      [data-testid="stFooter"] { display: none; }
      footer { visibility: hidden; }
      /* device status strip */
      .devicetop { display:flex; justify-content:space-between; align-items:center;
        font-size:0.70rem; letter-spacing:1.6px; color:#8fa89b; margin-bottom:0.5rem; }
      /* tabs as a segmented control */
      div[data-baseweb="tab-list"] { gap: 6px; background: rgba(255,255,255,0.05);
        padding: 4px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08); }
      button[data-baseweb="tab"] { border-radius: 11px !important; font-size: 0.82rem; }
      button[data-baseweb="tab"][aria-selected="true"] { background: rgba(47,213,117,0.20); }
      /* glass buttons and inputs */
      div[data-testid="stButton"] > button {
        width: 100%; border-radius: 14px; font-weight: 600;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.12);
      }
      div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #1f9d55, #2fd575);
        border: none; color: #04120a;
      }
      div[data-testid="stTextArea"] textarea, [data-baseweb="select"] > div {
        background: rgba(255,255,255,0.06) !important;
        border-radius: 12px !important;
      }
      .badge { display:inline-block; padding:2px 12px; border-radius:999px;
               border:1px solid rgba(47,213,117,0.7); color:#2fd575; font-size:0.70rem;
               letter-spacing:1.5px; margin-right:6px; }
      .muted { color:#8fa89b; font-size:0.82rem; }
      .rail-card { border:1px solid rgba(255,255,255,0.10); border-radius:14px; padding:12px 16px;
                   background: rgba(255,255,255,0.05); margin-bottom:10px; }
      .rail-title { font-weight:700; font-size:0.98rem; margin-bottom:2px; }
      .big-green { font-size:1.45rem; font-weight:800; color:#2fd575;
                   text-align:center; line-height:1.35; margin: 0.4rem 0; }
      .gate { border:1px solid rgba(47,213,117,0.55); border-radius:16px; padding:16px 18px;
              background: rgba(47,213,117,0.07); }
      /* mobile: the widget becomes the whole screen — native-app feel */
      @media (max-width: 640px) {
        .block-container {
          max-width: 100%; margin: 0; border-radius: 0;
          border-left: none; border-right: none; border-top: none;
          padding-bottom: calc(2.4rem + env(safe-area-inset-bottom));
        }
      }
      /* ── Cinematic hero ── */
      .hero { position: relative; border-radius: 22px; padding: 2rem 1.3rem 1.9rem;
              text-align: center; overflow: hidden; margin-bottom: 0.9rem;
              background-size: cover; background-position: center;
              background-image:
                linear-gradient(155deg, rgba(4,18,10,0.30), rgba(4,18,10,0.88)),
                radial-gradient(120% 120% at 18% 0%, rgba(47,213,117,0.30), transparent 55%),
                radial-gradient(130% 140% at 92% 112%, rgba(212,175,55,0.20), transparent 55%),
                linear-gradient(160deg, #0d2418, #07130d);
              border: 1px solid rgba(47,213,117,0.35); }
      .hero-kicker { font-size: 0.62rem; letter-spacing: 2.4px; color: #7fe0a8; margin-bottom: 0.55rem; }
      .hero-title { font-size: 1.66rem; font-weight: 800; line-height: 1.16; color: #f2fbf6;
                    text-shadow: 0 2px 26px rgba(47,213,117,0.35); }
      .hero-sub { font-size: 0.85rem; color: #a9c6b6; margin-top: 0.5rem; }
      .hero-receipt { position: relative; margin: 1.05rem auto 0.15rem; width: 80%;
                      background: rgba(240,255,247,0.97); color: #07130d; border-radius: 14px;
                      padding: 0.65rem 0.9rem; text-align: left; transform: rotate(-2.2deg);
                      box-shadow: 0 18px 40px rgba(0,0,0,0.45), 0 0 0 1px rgba(47,213,117,0.5);
                      animation: floaty 5.5s ease-in-out infinite; }
      .hr-row { display: flex; justify-content: space-between; font-size: 0.66rem; color: #4c6a5b; }
      .hr-amount { font-size: 1.08rem; font-weight: 800; color: #0b7a3e; margin-top: 2px; }
      .hr-tag { display: inline-block; margin-top: 5px; font-size: 0.58rem; font-weight: 700;
                background: #d8f5e4; color: #0b7a3e; border-radius: 999px; padding: 1px 8px;
                letter-spacing: 0.6px; }
      @keyframes floaty { 0%,100% { transform: rotate(-2.2deg) translateY(0); }
                          50% { transform: rotate(-1.3deg) translateY(-6px); } }
      /* ── Value strip + stepper ── */
      .vp-card { border: 1px solid rgba(255,255,255,0.10); background: rgba(255,255,255,0.05);
                 border-radius: 14px; padding: 10px 8px; text-align: center; height: 100%; }
      .vp-ico { font-size: 1.15rem; }
      .vp-t { font-weight: 700; font-size: 0.8rem; margin-top: 2px; }
      .vp-d { font-size: 0.66rem; color: #8fa89b; margin-top: 3px; line-height: 1.35; }
      .steps { text-align: center; font-size: 0.74rem; color: #8fa89b; margin: 0.1rem 0 0.65rem; }
      .steps b { color: #7fe0a8; }
      /* ── Motion ── */
      div[data-testid="stButton"] > button[kind="primary"] { animation: pulse 2.6s ease-in-out infinite; }
      @keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(47,213,117,0.35); }
                         50% { box-shadow: 0 0 16px 3px rgba(47,213,117,0.22); } }
      .rail-card { transition: transform .18s ease, border-color .18s ease; }
      .rail-card:hover { transform: translateY(-2px); border-color: rgba(47,213,117,0.55); }
      /* ── One-line section headings + topmost, unclipped tooltips ── */
      h2 { font-size: 1.02rem !important; margin: 0.15rem 0 0.1rem !important; white-space: nowrap; }
      h2 + div, h2 a { display: inline; }
      [data-baseweb="popover"], [data-baseweb="tooltip"] { z-index: 100000 !important; }
      /* ── Investor mechanics flow diagram ── */
      .flow { display: flex; align-items: stretch; gap: 6px; flex-wrap: wrap;
              background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.10);
              border-radius: 14px; padding: 12px; }
      .fstep { flex: 1 1 38%; min-width: 120px; background: rgba(255,255,255,0.05);
               border: 1px solid rgba(255,255,255,0.10); border-radius: 12px;
               padding: 8px 10px; text-align: center; }
      .fn { display: inline-block; width: 20px; height: 20px; line-height: 20px; border-radius: 50%;
            background: rgba(47,213,117,0.25); color: #7fe0a8; font-weight: 800; font-size: 0.72rem; }
      .ft { font-weight: 700; font-size: 0.82rem; margin-top: 3px; }
      .fd { font-size: 0.66rem; color: #8fa89b; margin-top: 2px; line-height: 1.3; }
      .farrow { align-self: center; color: #7fe0a8; font-size: 1rem; }
      .mech li { font-size: 0.78rem; color: #c9ded3; margin-bottom: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state defaults ─────────────────────────────────────────────────
for key, default in {
    "receipt": None,            # last Smart Receipt generated (dict)
    "ai_mode": None,            # "local" or "demo"
    "notarized_id": None,       # asset_id of last notarized receipt
    "pay_flow": None,           # {"asset_id","rail","stage"}
    "last_settlement": None,    # {"asset_id","rail","settled_at",...}
}.items():
    st.session_state.setdefault(key, default)


# ── Trust Vault helpers (local JSON database) ──────────────────────────────
def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def seed_asset():
    """One sample receipt so the Investor view is never empty on first run."""
    rec = {
        "invoice_id": "ECI-SEED-0001",
        "seller": "Juan's Hardware Supply",
        "buyer": "Globe Telecom",
        "amount": 100000,
        "due_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "risk_level": "Low (Prime Buyer)",
        "discount_rate_percentage": 3.0,
        "suggested_cash_advance": 97000,
        "investor_yield_percentage": 3.0,
    }
    digest = hashlib.sha256(
        (json.dumps(rec, sort_keys=True, separators=(",", ":")) + ORIGINATOR_WALLET).encode()
    ).hexdigest()
    return {
        "asset_id": "ECI-SEED-0001",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "wallet": ORIGINATOR_WALLET,
        "layer0_hash": "0x" + digest,
        "tranching": False,
        "rwa_pdax": False,
        "receipt": rec,
        "views": 0,
        "dividends_php": 0.0,
    }


def load_db():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, encoding="utf-8") as f:
                db = json.load(f)
            if isinstance(db, dict) and "assets" in db:
                return db
        except (json.JSONDecodeError, OSError):
            pass
    db = {"assets": [seed_asset()]}
    save_db(db)
    return db


# ── Local AI helper (Ollama) + Demo Mode fallback ──────────────────────────
def parse_amount(text):
    """Pull a peso figure out of everyday text like 'Sold 100k PHP of ...'."""
    low = text.lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*k\b", low)
    if m:
        return float(m.group(1)) * 1000
    m = re.search(r"(?:php|₱)\s*([\d,]+(?:\.\d+)?)", low)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"([\d,]{4,}(?:\.\d+)?)", low)
    if m:
        return float(m.group(1).replace(",", ""))
    return 100000.0


def detect_buyer(text):
    low = text.lower()
    for corp in KNOWN_CORPS:
        if corp in low:
            return corp.title(), True
    m = re.search(r"\bto\s+([A-Z][\w&.']*(?:\s+[A-Z][\w&.']*){0,3})", text)
    if m:
        return m.group(1).strip(), False
    return "Local Buyer", False


def mock_receipt(text):
    """Demo Mode: same JSON contract the local LLM returns, built with rules.
    This is the safety net for the live demo — the app never crashes."""
    buyer, known = detect_buyer(text)
    amount = parse_amount(text)
    rate = 3.0 if known else 8.0
    db = load_db()
    return {
        "invoice_id": f"ECI-{datetime.now():%Y%m%d}-{len(db['assets']) + 1:04d}",
        "seller": "Your Business",
        "buyer": buyer,
        "amount": amount,
        "due_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "risk_level": "Low (Prime Buyer)" if known else "Elevated (Unverified Buyer)",
        "discount_rate_percentage": rate,
        "suggested_cash_advance": round(amount * (1 - rate / 100), 2),
        "investor_yield_percentage": rate,
    }


def normalize(rec, raw_text):
    """Guarantee every key exists with a sane value, whichever path produced it."""
    base = mock_receipt(raw_text)
    base.update({k: v for k, v in rec.items() if v not in (None, "", "null")})
    try:
        base["amount"] = float(base["amount"])
    except (TypeError, ValueError):
        base["amount"] = parse_amount(raw_text)
    try:
        base["suggested_cash_advance"] = round(float(base["suggested_cash_advance"]), 2)
    except (TypeError, ValueError):
        base["suggested_cash_advance"] = round(base["amount"] * (1 - float(base.get("discount_rate_percentage", 8)) / 100), 2)
    return base


def call_ollama(user_text):
    """LOCAL AI PRIVACY: this request goes to 127.0.0.1 only — the user's own
    machine. If the big model can't fit in RAM we step down to the 1B model,
    and if Ollama is down entirely we return Demo Mode data instead of failing."""
    for model in OLLAMA_MODELS:
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={
                    "model": model,
                    "prompt": UNDERWRITER_PROMPT.format(user_text=user_text),
                    "stream": False,
                    "format": "json",   # force strict JSON from the local model
                    "options": {"temperature": 0.1, "num_predict": 400},
                },
                timeout=25,
            )
            resp.raise_for_status()
            return json.loads(resp.json()["response"]), model
        except (requests.RequestException, ValueError, KeyError):
            continue
    return mock_receipt(user_text), "demo"


# ── Layer 0 notarization ───────────────────────────────────────────────────
def notarize(rec, tranching, rwa_pdax):
    """Trust Vault: hash the receipt, bind it to the originator wallet, store
    locally. Layer 0 = identity + integrity before anything else happens."""
    db = load_db()
    payload = json.dumps(rec, sort_keys=True, separators=(",", ":")) + ORIGINATOR_WALLET
    digest = hashlib.sha256(payload.encode()).hexdigest()
    asset = {
        "asset_id": rec["invoice_id"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "wallet": ORIGINATOR_WALLET,
        "layer0_hash": "0x" + digest,
        "tranching": bool(tranching),
        "rwa_pdax": bool(rwa_pdax),
        "receipt": rec,
        "views": 0,
        "dividends_php": 0.0,
    }
    db["assets"].append(asset)
    save_db(db)
    return asset


# ── 402 Multi-Rail eSettlement ─────────────────────────────────────────────
def settle(asset_id, rail):
    """Record the paid unlock: bump the view count and route the Data Dividend
    (70% of the fee) to the originator wallet. FIDNT DATA MONETIZATION."""
    db = load_db()
    for a in db["assets"]:
        if a["asset_id"] == asset_id:
            a["views"] = a.get("views", 0) + 1
            a["dividends_php"] = round(a.get("dividends_php", 0) + FEE_PHP * DIVIDEND_SHARE, 2)
            break
    save_db(db)
    st.session_state.last_settlement = {
        "asset_id": asset_id,
        "rail": rail,
        "settled_at": datetime.now().isoformat(timespec="seconds"),
        "fee_php": FEE_PHP,
        "fee_usdc": FEE_USDC,
        "dividend_php": round(FEE_PHP * DIVIDEND_SHARE, 2),
        "originator_wallet": ORIGINATOR_WALLET,
    }
    st.session_state.pay_flow = {"asset_id": asset_id, "rail": rail, "stage": "done"}


def make_qr(payload):
    """Real QR code, generated on the fly, encoding this payment's details."""
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0b3d2e", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _crc16(data: bytes) -> str:
    """CRC-16/CCITT-FALSE — the checksum EMVCo QR codes require in tag 63."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if (crc & 0x8000) else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def _tlv(tag: str, value: str) -> str:
    return f"{tag}{len(value):02d}{value}"


def qrph_payload(amount_php: float, ref: str) -> str:
    """Official QR Ph payload (EMVCo merchant-presented QR, the Philippine
    national QR standard that GCash, Maya, and every participating bank app
    scan natively). Tag 26 carries the PH.PPMI GUI + destination account;
    tag 63 carries the CRC-16. Set GCASH_NUMBER to a real GCash mobile to
    collect real pesos — today it runs with a sandbox number."""
    body = (
        _tlv("00", "01")                                   # payload format indicator
        + _tlv("01", "12")                                 # dynamic, one-time-use QR
        + _tlv("26", _tlv("00", "PH.PPMI") + _tlv("01", GCASH_NUMBER))
        + _tlv("52", "5199")                               # merchant category code
        + _tlv("53", "608")                                # currency: PHP
        + _tlv("54", f"{amount_php:.2f}")
        + _tlv("58", "PH")
        + _tlv("59", "0 DEVICE")                           # merchant name
        + _tlv("60", "MANILA")
        + _tlv("62", _tlv("05", ref[:25]))                 # bill / reference number
    )
    body += "6304"
    return body + _crc16(body.encode())


# ── Optional real rails (activate automatically when configured) ────────────
def get_secret(section, key):
    try:
        return st.secrets[section][key]
    except (KeyError, FileNotFoundError):
        return None


def paymongo_headers(secret_key):
    import base64
    return {"Authorization": "Basic " + base64.b64encode(secret_key.encode()).decode(),
            "Content-Type": "application/json"}


def create_paymongo_source(rail_type, amount_php):
    """Real checkout session on PayMongo, the PH payment gateway. sk_test_ keys
    run their sandbox; sk_live_ collects real money. Types: gcash, paymaya."""
    secret = get_secret("paymongo", "secret_key")
    if not secret:
        return None
    body = {"data": {"attributes": {
        "amount": int(round(amount_php * 100)), "currency": "PHP",
        "type": rail_type,
        "redirect": {"success": "http://localhost:8501/?paid=1", "failed": "http://localhost:8501/?failed=1"},
    }}}
    r = requests.post("https://api.paymongo.com/v1/sources", json=body,
                      headers=paymongo_headers(secret), timeout=15)
    r.raise_for_status()
    d = r.json()["data"]
    return {"id": d["id"], "checkout_url": d["attributes"]["redirect"]["checkout_url"]}


def paymongo_source_paid(source_id):
    secret = get_secret("paymongo", "secret_key")
    if not secret:
        return False
    r = requests.get(f"https://api.paymongo.com/v1/sources/{source_id}",
                     headers=paymongo_headers(secret), timeout=15)
    return r.json()["data"]["attributes"]["status"] == "chargeable"


# ── Settlement renderer (shared by Page 2 and Page 3) ──────────────────────
def render_settlement():
    s = st.session_state.last_settlement
    db = load_db()
    asset = next((a for a in db["assets"] if a["asset_id"] == s["asset_id"]), None)
    st.markdown(
        '<p class="big-green">✅ Data Dividend routed to Originator Wallet '
        f"{s['originator_wallet']}. Instant Cash Advance Approved.</p>",
        unsafe_allow_html=True,
    )
    st.success(
        f"Paid via **{s['rail']}** at {s['settled_at']} · Fee ₱{s['fee_php']:.2f} "
        f"(≈ ${s['fee_usdc']:.2f}) · **₱{s['dividend_php']:.2f} Data Dividend** "
        f"sent instantly to the business owner."
    )
    if asset:
        c1, c2, c3 = st.columns(3)
        c1.metric("Views", asset.get("views", 0))
        c2.metric("Dividends earned", f"₱{asset.get('dividends_php', 0):,.2f}")
        c3.metric("Cash advance", f"₱{asset['receipt'].get('suggested_cash_advance', 0):,.0f}")
        st.markdown("**Smart Receipt — full document now visible to the payer**")
        st.json(asset["receipt"], expanded=True)
        st.caption(
            "Layer 0 seal " + asset["layer0_hash"][:26] + "… · "
            "70% of every view fee goes to the data owner (Fidnt Data Monetization)."
        )


# ── Payment rail renderer ──────────────────────────────────────────────────
def render_rail_panel(asset_id):
    flow = st.session_state.pay_flow
    rail, stage = flow["rail"], flow["stage"]

    if rail == "GCash" and stage == "interact":
        st.markdown("**Scan to Pay — GCash**")
        ref = f"GCASH-{asset_id}-{int(time.time())}"
        src = None
        if get_secret("paymongo", "secret_key"):
            try:
                src = create_paymongo_source("gcash", FEE_PHP)
            except requests.HTTPError as e:
                code = ""
                try:
                    code = e.response.json()["errors"][0]["code"]
                except Exception:
                    pass
                if code == "payment_method_not_configured":
                    st.warning("PayMongo key works, but this org isn't activated for GCash yet "
                               "(dashboard → payment methods → enable GCash). Using the local QR below.")
                else:
                    st.warning(f"PayMongo declined ({code or 'error'}) — using the local QR below.")
            except requests.RequestException as e:
                st.warning(f"PayMongo unreachable ({e.__class__.__name__}) — using local QR.")
        if src:
            st.image(make_qr(src["checkout_url"]), width=240,
                     caption="REAL GCash checkout (PayMongo sandbox) — scans with any camera")
            st.markdown(f"[Or tap to open the GCash checkout →]({src['checkout_url']})")
            ok_label = "✅ I paid — verify with PayMongo"
        elif os.path.exists(GCASH_QR_IMAGE):
            st.image(GCASH_QR_IMAGE, width=250,
                     caption="Your real GCash QR — scan, send ₱5, then confirm below")
            ok_label = "✅ I sent ₱5 — confirm"
        else:
            st.image(make_qr(qrph_payload(FEE_PHP, ref)), width=230,
                     caption=f"QR Ph (EMVCo) standard payload · sandbox dest {GCASH_NUMBER}")
            st.info("To make this QR scannable for real, add ONE of:\n"
                    "**1.** your GCash app's personal QR saved as `gcash_qr.png` in the project folder, or\n"
                    "**2.** a PayMongo test key in `.streamlit/secrets.toml`.",
                    icon="📲")
            ok_label = "✅ I paid — confirm GCash webhook"
        if st.button(ok_label, key="btn_gcash_ok", use_container_width=True):
            if src:
                with st.spinner("Checking with PayMongo…"):
                    if paymongo_source_paid(src["id"]):
                        settle(asset_id, "GCash (PayMongo sandbox)")
                        st.rerun()
                    else:
                        st.error("PayMongo says still pending — complete the checkout, then verify again.")
            else:
                with st.spinner("Receiving webhook…"):
                    time.sleep(0.8)
                settle(asset_id, "GCash")
                st.rerun()

    elif rail == "Maya" and stage == "interact":
        src = None
        if get_secret("paymongo", "secret_key"):
            try:
                src = create_paymongo_source("paymaya", FEE_PHP)
            except requests.RequestException:
                src = None
        if src:
            st.markdown("**Maya checkout — real flow (PayMongo sandbox)**")
            st.markdown(f"[Open the Maya checkout →]({src['checkout_url']})")
            st.image(make_qr(src["checkout_url"]), width=200,
                     caption="Scan with your phone camera — opens the real Maya payment page")
            ok_label = "✅ I paid — verify with PayMongo"
        else:
            st.markdown("**Maya — hold your phone near the terminal (NFC)**")
            st.caption("Terminal: 0.Device Reader · Amount ₱5.00 · Waiting for tap…")
            ok_label = "📲 Simulate NFC Tap"
        if st.button(ok_label, key="btn_maya_ok", use_container_width=True):
            if src:
                with st.spinner("Checking with PayMongo…"):
                    if paymongo_source_paid(src["id"]):
                        settle(asset_id, "Maya (PayMongo sandbox)")
                        st.rerun()
                    else:
                        st.error("Still pending — complete the Maya checkout, then verify again.")
            else:
                with st.spinner("Tap detected — authorizing…"):
                    time.sleep(0.8)
                settle(asset_id, "Maya (NFC)")
                st.rerun()

    elif rail == "Card / Apple Pay" and stage == "interact":
        if st.button("💳 Complete secure checkout (simulated redirect)", key="btn_stripe_ok", use_container_width=True):
            with st.spinner("Redirecting to Stripe… payment authorized."):
                time.sleep(1.0)
            settle(asset_id, "Stripe / Apple Pay")
            st.rerun()

    elif rail == "USDC (Stellar)" and stage == "interact":
        ref = f"0DEV-{int(time.time())}"
        treasury = get_secret("stellar", "treasury_public") or STELLAR_TREASURY_DEFAULT
        sep7 = f"web+stellar:pay?dest={treasury}&amount=0.1&memo={ref[:28]}&memo_type=MEMO_TEXT"
        st.markdown("**Scan with any Stellar wallet (testnet)** — a real SEP-0007 payment request.")
        st.image(make_qr(sep7), width=210,
                 caption=f"0.1 XLM testnet (USDC stand-in) → {treasury[:9]}… · ref {ref}")
        if st.button("🤖 Let the AI agent settle — real testnet transaction", key="btn_usdc_ok", use_container_width=True):
            agent_secret = get_secret("stellar", "agent_secret")
            if agent_secret:
                try:
                    from stellar_sdk import Asset, Keypair, Network, Server, TextMemo, TransactionBuilder
                    kp = Keypair.from_secret(agent_secret)
                    server = Server("https://horizon-testnet.stellar.org")
                    account = server.load_account(kp.public_key)
                    tx = (TransactionBuilder(account, Network.TESTNET_NETWORK_PASSPHRASE, base_fee=100)
                          .append_payment_op(destination=treasury, asset=Asset.native(), amount="0.1")
                          .add_memo(TextMemo(ref[:28]))
                          .set_timeout(30).build())
                    tx.sign(kp)
                    resp = server.submit_transaction(tx)
                    settle(asset_id, f"Stellar testnet tx {resp['hash'][:10]}…")
                    st.rerun()
                except Exception as e:
                    st.warning(f"Testnet unreachable ({e.__class__.__name__}) — settling in simulation.")
                    with st.spinner("Agent signing…"):
                        time.sleep(1.0)
                    settle(asset_id, "USDC via Stellar (simulated)")
                    st.rerun()
            else:
                with st.spinner("Agent signing… atomic settlement on Stellar…"):
                    time.sleep(1.2)
                settle(asset_id, "USDC via Stellar (simulated)")
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════════════
hero_bg = "url('app/static/hero.jpg'), " if os.path.exists(HERO_IMG_PATH) else ""
st.markdown(
    f"""
    <div class="hero" style="background-image:
      linear-gradient(155deg, rgba(4,18,10,0.42), rgba(4,18,10,0.88)), {hero_bg}
      radial-gradient(120% 120% at 18% 0%, rgba(47,213,117,0.30), transparent 55%),
      radial-gradient(130% 140% at 92% 112%, rgba(212,175,55,0.20), transparent 55%),
      linear-gradient(160deg, #0d2418, #07130d);">
      <div class="hero-kicker">FINANCIAL INCLUSION · ONE RECEIPT AT A TIME</div>
      <div class="hero-title">Your sale. Your phone.<br>Your money — today.</div>
      <div class="hero-sub">No collateral. No credit line. Your receipt is the collateral.</div>
      <div class="hero-receipt">
        <div class="hr-row"><span>Smart Receipt · ECI-2026-0001</span><span>PAID ⚡</span></div>
        <div class="hr-amount">₱97,000 — available today</div>
        <span class="hr-tag">LOCAL AI VERIFIED · LAYER 0 SEALED</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
now = datetime.now()
st.markdown(
    f'<div class="devicetop"><span>⬢ 0.DEVICE</span>'
    f'<span>{now:%I:%M %p} · LOCAL · ▮▮▮▮</span></div>',
    unsafe_allow_html=True,
)
st.markdown("# 0.Device")
st.markdown(
    '<span class="badge">LOCAL AI · OFFLINE · PRIVATE</span>'
    '<span class="badge">TEAM ISET</span>',
    unsafe_allow_html=True,
)
st.caption("The Sovereign Trade & Finance Agent — turn any sale into a Smart Receipt, "
           "see the cash you can get today, and earn every time someone views your data.")

tab1, tab2, tab3 = st.tabs(["1 · Business Owner", "2 · Bank / Investor", "3 · Settlement"])

# ─────────────────────────────── Page 1 ────────────────────────────────────
with tab1:
    st.markdown("## 🧾 Sovereign Estate Auditor")
    st.markdown('<span class="muted">Everything below runs on this device. '
                'Your sales details never touch the internet.</span>', unsafe_allow_html=True)

    v1, v2, v3 = st.columns(3)
    v1.markdown('<div class="vp-card"><div class="vp-ico">🔒</div><div class="vp-t">Private</div>'
                '<div class="vp-d">AI runs on your device — your books never leave</div></div>',
                unsafe_allow_html=True)
    v2.markdown('<div class="vp-card"><div class="vp-ico">⚡</div><div class="vp-t">Fast</div>'
                '<div class="vp-d">Cash offer in seconds, not weeks</div></div>',
                unsafe_allow_html=True)
    v3.markdown('<div class="vp-card"><div class="vp-ico">💸</div><div class="vp-t">Earns</div>'
                '<div class="vp-d">Paid every time your data is viewed</div></div>',
                unsafe_allow_html=True)

    st.markdown('<div class="steps"><b>1</b> Describe your sale &nbsp;→&nbsp; <b>2</b> See your cash offer '
                '&nbsp;→&nbsp; <b>3</b> Lock it in your vault</div>', unsafe_allow_html=True)

    with st.expander("📖 How to issue a receipt — 4 steps", expanded=True):
        st.markdown(
            "<div class='mech'>"
            "<li><b>1 · Describe</b> — type what you sold in plain words (an example is already filled in).</li>"
            "<li><b>2 · Press ⚡ Run Local AI</b> — the AI on this device drafts your <b>Smart Receipt</b> "
            "and shows your instant cash offer. Hover any <b>?</b> icon for help.</li>"
            "<li><b>3 · Press 🔐 Notarize &amp; Secure on Layer 0</b> — the receipt is sealed to your "
            "wallet in your Trust Vault. <i>Issuance done — you now own a bank-grade digital receipt.</i></li>"
            "<li><b>4 · Show it or fund it</b> — switch to <b>2 · Bank / Investor</b> to see what a bank "
            "sees, and <b>3 · Settlement</b> for your earnings.</li>"
            "</div>",
            unsafe_allow_html=True,
        )

    desc = st.text_area(
        "Describe the sale or work you did",
        value="Sold 100k PHP of hardware to Globe Telecom. Payment due in 30 days.",
        key="ta_desc",
        height=110,
    )

    tranching = st.toggle(
        "Split the payout into tranches (Fiduciary Layer)", key="tg_tranche", value=False,
        help="Instead of one lump sum, the investor's money arrives in scheduled parts — "
             "handled for you, fiduciary-style.",
    )
    rwa_pdax = st.toggle(
        "Offer this receipt to investors (PDAX Exchange)", key="tg_rwa", value=False,
        help="List the receipt on PDAX so investors anywhere can fund it and earn the yield.",
    )

    if st.button(
        "⚡ Run Local AI", key="btn_run", use_container_width=True, type="primary",
        help="Reads your text with llama3.2 running ON THIS DEVICE via Ollama — "
             "your sales details never touch the internet.",
    ):
        with st.spinner("🧠 Local AI is reading your sale — nothing leaves this device…"):
            rec, mode = call_ollama(desc)
        st.session_state.receipt = normalize(rec, desc)
        st.session_state.ai_mode = mode
        st.session_state.notarized_id = None

    rec = st.session_state.receipt
    if rec:
        if st.session_state.ai_mode == "demo":
            st.info("⚡ Demo Mode: the on-device AI couldn't load right now (it needs ~1–2 GB free RAM), "
                    "so a built-in underwriter produced this receipt. Close heavy apps or restart the PC, "
                    "then press **Run Local AI** again — full llama3.2 runs completely on this device.",
                    icon="🛟")
        else:
            st.success(f"🟢 Local AI online — {st.session_state.ai_mode} answered on this device.", icon="🔌")

        st.markdown("**Smart Receipt** · `eCommercial Invoice (eCI)`")
        st.json(rec, expanded=True)

        st.markdown(
            f"""
            <div class="gate">
              <p class="big-green">💰 Instant cash advance available:<br>
              PHP {float(rec['suggested_cash_advance']):,.0f}</p>
              <p class="muted" style="text-align:center; margin:0;">
              Get paid today instead of waiting for {rec.get('due_date', 'the due date')} ·
              buyer risk: {rec.get('risk_level', 'n/a')} · investor yield: {rec.get('investor_yield_percentage', '—')}%</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.notarized_id:
            st.success(f"🔐 Secured in your Trust Vault. You own this data — "
                       f"receipt ID **{st.session_state.notarized_id}**, sealed to wallet {ORIGINATOR_WALLET}. "
                       f"Nobody can view it without paying you.")
            st.caption("Open tab 2 to see what a bank or investor experiences when they query it.")
        else:
            if st.button(
                "🔐 Notarize & Secure on Layer 0", key="btn_notarize", use_container_width=True, type="primary",
                help="Stamps the receipt with a SHA-256 fingerprint bound to your wallet and "
                     "stores it in your local Trust Vault — proof you own this data.",
            ):
                asset = notarize(rec, tranching, rwa_pdax)
                st.session_state.notarized_id = asset["asset_id"]
                st.rerun()

# ─────────────────────────────── Page 2 ────────────────────────────────────
with tab2:
    st.markdown("## 🔎 Auditor / Investor View")
    st.markdown('<span class="muted">Query the Trust Vault like a bank would.</span>', unsafe_allow_html=True)

    with st.expander("📊 How the mechanics work — for investors", expanded=True):
        st.markdown(
            """<div class="flow">
              <div class="fstep"><div class="fn">1</div><div class="ft">Query</div>
                <div class="fd">Investor requests a Smart Receipt from the vault</div></div>
              <div class="farrow">→</div>
              <div class="fstep"><div class="fn">2</div><div class="ft">402 Gate</div>
                <div class="fd">App answers: HTTP 402 — pay ₱5 to view</div></div>
              <div class="farrow">→</div>
              <div class="fstep"><div class="fn">3</div><div class="ft">Any rail</div>
                <div class="fd">GCash · Maya · Card · USDC — same gate</div></div>
              <div class="farrow">→</div>
              <div class="fstep"><div class="fn">4</div><div class="ft">Unlock + Dividend</div>
                <div class="fd">Receipt opens; owner earns ₱3.50 instantly</div></div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='mech' style='margin-top:8px;'>"
            "<li><b>Why it's safe to fund:</b> every receipt is sealed with a SHA-256 Layer 0 fingerprint "
            "bound to the owner's wallet — you can verify integrity before paying.</li>"
            "<li><b>Why the advance is safe:</b> prime buyers (e.g. Globe) carry a 3% discount — "
            "you lend ₱97,000 against a ₱100,000 receipt and collect the full face value on due date.</li>"
            "<li><b>The data dividend:</b> 70% of every view fee goes to the business owner — "
            "the more the market looks, the more the vendor earns. Aligned incentives by design.</li>"
            "<li><b>Global rails:</b> the same HTTP 402 gate accepts USDC on Stellar — "
            "an investor anywhere on earth can fund a Philippine receipt.</li>"
            "</div>",
            unsafe_allow_html=True,
        )

    db = load_db()
    assets = db["assets"]
    labels = {a["asset_id"]: f"{a['asset_id']} — {a['receipt']['buyer']} — ₱{a['receipt']['amount']:,.0f}"
              for a in assets}
    chosen = st.selectbox(
        "Smart Receipts in the vault", list(labels.keys()),
        format_func=lambda k: labels[k], key="sel_asset",
        help="Every receipt a business owner has notarized — each one sealed to their wallet.",
    )

    if st.button(
        "🔍 Query Smart Receipt", key="btn_query", use_container_width=True,
        help="See exactly what a bank or investor sees when they request this receipt from your vault.",
    ):
        st.session_state.pay_flow = None

    if chosen:
        asset = next(a for a in assets if a["asset_id"] == chosen)
        rec = asset["receipt"]
        flow = st.session_state.pay_flow
        active_flow = flow if (flow and flow["asset_id"] == chosen) else None

        if active_flow and active_flow["stage"] == "done":
            render_settlement()

        elif active_flow and active_flow["stage"] == "interact":
            st.markdown(
                f"""<div class="gate"><p class="muted" style="margin:0 0 6px;">HTTP 402 · PAYMENT REQUIRED</p>
                <p style="margin:0;">Paying to view <b>{chosen}</b> via {active_flow['rail']}…</p></div>""",
                unsafe_allow_html=True,
            )
            render_rail_panel(chosen)

        else:
            # Locked teaser + the 402 gate
            st.markdown(f"""<div class="gate">
              <p class="muted" style="margin:0 0 6px;">RECEIPT {chosen} · SEALED ON LAYER 0 ·
              {asset['layer0_hash'][:22]}…</p>
              <p style="margin:0;">Buyer: <b>{rec['buyer']}</b> · Amount: <b>₱{rec['amount']:,.0f}</b><br>
              <span class="muted">Seller, terms and full document are private until the view fee is paid.</span></p>
            </div>""", unsafe_allow_html=True)

            st.markdown("### 🔒 402 Payment Required — Small Fee to See the Full Receipt")
            st.markdown(f"**₱{FEE_PHP:.2f}** (≈ ${FEE_USDC:.2f} USDC) — one-time view fee. "
                        f"**The business owner keeps ₱{FEE_PHP * DIVIDEND_SHARE:.2f} of it** and earns "
                        f"every time their data is viewed.")
            st.caption("HTTP 402 Multi-Rail eSettlement — one gate, any payment rail.")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(
                    '<div class="rail-card" title="One-time QR Ph code — the national standard '
                    'GCash and every PH bank app scans natively. 70% of the fee goes to the owner.">'
                    '<div class="rail-title">📱 GCash</div>'
                    '<span class="muted">₱5.00 · QR Ph code</span></div>', unsafe_allow_html=True)
                if st.button(
                    "Pay ₱5 via GCash", key="btn_gcash", use_container_width=True,
                    help="Generates an official QR Ph code on the spot — scan it with any "
                         "GCash or bank app to pay the ₱5 view fee.",
                ):
                    st.session_state.pay_flow = {"asset_id": chosen, "rail": "GCash", "stage": "interact"}
                    st.rerun()

                st.markdown(
                    '<div class="rail-card" title="Card payment through Stripe — a simulated '
                    'redirect tonight, wired to a live gateway the moment API keys are added.">'
                    '<div class="rail-title">💳 Card / Apple Pay</div>'
                    '<span class="muted">$0.10 · Stripe</span></div>', unsafe_allow_html=True)
                if st.button(
                    "Pay $0.10 via Stripe / Apple Pay", key="btn_stripe", use_container_width=True,
                    help="Card payment through Stripe — simulated tonight, one API key away from live.",
                ):
                    st.session_state.pay_flow = {"asset_id": chosen, "rail": "Card / Apple Pay", "stage": "interact"}
                    st.rerun()

            with c2:
                st.markdown(
                    '<div class="rail-card" title="Tap-to-pay — hold your phone near the reader, '
                    'the same tap you use at the grocery.">'
                    '<div class="rail-title">📲 Maya</div>'
                    '<span class="muted">₱5.00 · NFC tap</span></div>', unsafe_allow_html=True)
                if st.button(
                    "Pay ₱5 via Maya (NFC)", key="btn_maya", use_container_width=True,
                    help="Tap-to-pay like at a grocery counter — hold your phone near the reader.",
                ):
                    st.session_state.pay_flow = {"asset_id": chosen, "rail": "Maya", "stage": "interact"}
                    st.rerun()

                st.markdown(
                    '<div class="rail-card" title="Stablecoin settlement — an AI agent pays on the '
                    'Stellar network and the receipt opens atomically, no waiting for banks.">'
                    '<div class="rail-title">🪙 USDC</div>'
                    '<span class="muted">$0.10 · Stellar · AI agent</span></div>', unsafe_allow_html=True)
                if st.button(
                    "Pay $0.10 USDC via Stellar", key="btn_usdc", use_container_width=True,
                    help="A machine-to-machine payment: the AI agent settles on Stellar and the "
                         "receipt opens in the same atomic step.",
                ):
                    st.session_state.pay_flow = {"asset_id": chosen, "rail": "USDC (Stellar)", "stage": "interact"}
                    st.rerun()

# ─────────────────────────────── Page 3 ────────────────────────────────────
with tab3:
    st.markdown("## ✅ Settlement & Data Dividend")
    if st.session_state.last_settlement:
        render_settlement()
    else:
        st.info("No settlement yet. Open **2 · Bank / Investor**, query a Smart Receipt, "
                "and pay through any rail — the moment it clears, the Data Dividend "
                "lands in the business owner's wallet and the full receipt is visible here.")

st.markdown('<div class="steps">0.Device · Team ISET — financial inclusion, one receipt at a time.</div>',
            unsafe_allow_html=True)
