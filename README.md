# 0.Device — The Sovereign Trade & Finance Agent

**Team ISET · AppBuildersPH Hackathon 2026 · Theme: Local AI**

A small business owner types what they sold. A local AI turns it into a **Smart Receipt**, shows the **cash they can get today** instead of waiting 30–90 days, and seals it in their **Trust Vault** — on their own device. When a bank or investor wants to see the full receipt, they hit an **HTTP 402 gate** and pay a small fee through **GCash, Maya, card, or USDC**. The business owner **earns 70% of every view fee**, forever.

---

## Why does this product benefit from running AI locally? *(mandatory answer)*

1. **Privacy is the product.** The input is a real business's sales data — the most sensitive numbers a Filipino MSME has. With 0.Device that data never leaves the device: the underwriting model (llama3 via Ollama) runs on the user's own machine. A cloud-only version would ask vendors to hand their books to an unknown server. Local AI is the difference between "useful app" and "app people will actually trust with their books."
2. **Works with zero signal.** Market vendors and rural suppliers often have no reliable data connection. The core flow — describe sale → Smart Receipt → cash advance figure → notarize — works fully offline.
3. **Zero API cost per document.** An MSME can notarize hundreds of receipts without paying per-token cloud fees, so the tool is viable at sari-sari-store scale, not just enterprise scale.

## The story in everyday words

| We say (users) | Under the hood |
|---|---|
| Smart Receipt | eCommercial Invoice (eCI) |
| Trust Vault | Local JSON ledger + SHA-256 Layer 0 notarization |
| "Cash you can get today" | Discounted cash advance (3% prime / 8% unverified buyer) |
| "Small fee to see the full receipt" | HTTP 402 Payment Required gate |
| Pay via GCash / Maya / card / USDC | Multi-rail eSettlement (QR, NFC, card redirect, atomic settlement) |
| Data Dividend | 70% of every view fee routed to the originator wallet (Fidnt Data Monetization) |

## The three screens

1. **Business Owner (Originator)** — describe the sale, run the local AI, review the Smart Receipt and suggested instant cash advance, then notarize it to your wallet (`0xUser1`) with a SHA-256 seal. Optional toggles: split payouts into tranches (fiduciary layer), offer the receipt to investors (PDAX).
2. **Bank / Investor** — query the Trust Vault. The receipt is sealed; the app answers **HTTP 402 Payment Required** (₱5.00 / $0.10). Pay via GCash (live QR code), Maya (NFC tap), Stripe/Apple Pay (redirect), or USDC on Stellar (AI-agent atomic settlement).
3. **Settlement & Data Dividend** — the full receipt is revealed to the payer, and the Data Dividend lands instantly in the originator's wallet. A running ledger shows views and dividends earned.

## Run it (judges)

```bash
# 1. Python 3.10+ then:
pip install -r requirements.txt

# 2. (Optional, for the real local AI) install Ollama from https://ollama.com then:
ollama pull llama3.2        # 3.2B model; on machines with <4 GB free RAM use: ollama pull llama3.2:1b

# 3. Run:
streamlit run app.py
```

The app opens at http://localhost:8501.

**Demo Mode:** if Ollama isn't running, the app does not fail — it switches to a built-in rule-based underwriter (clearly labeled on screen) with the exact same output contract. Everything else (402 gate, QR, settlement, dividends) works identically. This is a deliberate fail-safe so the demo is repeatable anywhere, including offline on stage.

## Payments: three levels of real

The GCash rail has three tiers — the app picks the best one configured and degrades gracefully:

1. **PayMongo checkout (real sandbox flows)** — with a PayMongo secret key (`sk_test_...`) in `.streamlit/secrets.toml`, the ₱5 fee creates a **real GCash/Maya checkout session**: the QR opens PayMongo's actual payment page, and the app verifies the status against PayMongo's API before unlocking. Free signup at [developers.paymongo.com](https://developers.paymongo.com); `sk_live_` keys collect real money with zero code changes.
2. **Your personal GCash QR (real money, zero signup)** — save your GCash app's own QR (Profile → My QR Code → screenshot) as `gcash_qr.png` in the project folder. Anyone scanning it with GCash sends real pesos to your account; keep the amount note on screen. (This file is gitignored — personal data stays out of the public repo.)
3. **QR Ph builder (standard, sandbox)** — with neither configured, the app generates a standards-correct **QR Ph payload** (EMVCo TLV, PH.PPMI GUI, CRC-16 checksum, amount and bill reference encoded) to a sandbox destination. Honest note: consumer GCash QRs cannot be minted from a phone number — GCash only recognizes QRs it issued — which is why tiers 1 and 2 exist.

**USDC rail is real blockchain:** a funded **Stellar testnet** account settles 0.1 XLM (USDC stand-in) on-chain — the QR is a live **SEP-0007 payment URI** any Stellar wallet can scan, and the "AI agent settles" button broadcasts a genuine testnet transaction with a verifiable hash. Card/Apple Pay remains a labeled simulation (real card rails require a gateway contract).

Hover any toggle, button, or payment card in the app — each carries a plain-language tooltip explaining what it does.

## What runs locally vs. what needs internet

| Component | Where it runs |
|---|---|
| Underwriting (llama3.2 via Ollama) | **Local** — user's device |
| Receipt storage, hashing, Trust Vault | **Local** — JSON file + SHA-256 |
| QR Ph code generation | **Local** — `qrcode` library, official EMVCo payload |
| Payment rails (GCash/Maya/USDC) | **Local by default**; real flows via optional PayMongo sandbox + Stellar testnet (never required) |

Internet required: **none**. Cloud AI APIs used: **none**.

## Disclosures (required by the rules)

- **Models:** `llama3.2` (3.2B, Q4_K_M) running locally via Ollama — `llama3.2:1b` on low-RAM machines (fallback: built-in rule-based Demo Mode, disclosed on screen).
- **Technologies / frameworks:** Python 3, Streamlit, requests, qrcode, Pillow.
- **APIs and cloud services:** none required — the Local AI core runs fully offline. Optional secondary services (activated only by config): PayMongo (payments sandbox) and the Stellar Horizon **testnet** for the settlement rail.
- **Existing code and assets:** none — built during the hackathon.
- **AI development tools:** AI-assisted development (agentic coding assistant) was used to write the code, per the allowed rules.

## 5-minute pitch outline

1. **Problem (45s):** Filipino MSMEs wait 30–90 days to get paid; banks won't advance cash without verified documents; vendors won't upload their books to a cloud AI they don't trust.
2. **Demo, Page 1 (90s):** type a sale → local AI builds the Smart Receipt on-device → "₱97,000 available today" → notarize to Trust Vault.
3. **Demo, Page 2 (90s):** switch seats, be the bank → HTTP 402 → pay ₱5 via GCash QR (or tap the other rails).
4. **Demo, Page 3 (30s):** receipt unlocked, Data Dividend lands in the vendor's wallet instantly.
5. **Why local AI (30s):** privacy + offline + zero per-document cost — the trust that makes a vendor say yes.
6. **Roadmap (15s):** real GCash/Maya APIs, PDAX RWA listing, on-chain anchoring, voice input in Tagalog via local speech models.

## Team

Team ISET — members as listed on the official AppBuildersPH participant list.
