"""Headless smoke test — drives the full happy path in Demo Mode (no Ollama).
Run:  python tests/smoke_test.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest

at = AppTest.from_file(os.path.join(os.path.dirname(__file__), "..", "app.py"), default_timeout=120)
at.run()
assert not at.exception, f"boot failed: {at.exception}"

# Page 1: run the local AI (falls back to Demo Mode when Ollama is absent)
at.button(key="btn_run").click().run()
assert not at.exception, f"Run Local AI failed: {at.exception}"
assert at.session_state["receipt"] is not None, "no receipt generated"
assert at.session_state["ai_mode"] == "demo" or str(at.session_state["ai_mode"]).startswith("llama3.2")

# Page 1: notarize to the Trust Vault
at.button(key="btn_notarize").click().run()
assert not at.exception, f"Notarize failed: {at.exception}"
assert at.session_state["notarized_id"], "no asset id after notarize"

# Page 2: query the vault -> 402 gate appears
at.button(key="btn_query").click().run()
assert not at.exception, f"Query failed: {at.exception}"

# Page 2: all four rails settle (GCash, Maya, card, USDC/Stellar)
for rail_btn, ok_btn, expected in [
    ("btn_gcash", "btn_gcash_ok", "GCash"),
    ("btn_maya", "btn_maya_ok", "Maya (NFC)"),
    ("btn_stripe", "btn_stripe_ok", "Stripe / Apple Pay"),
    ("btn_usdc", "btn_usdc_ok", "Stellar"),          # real testnet tx or graceful simulation
]:
    at.session_state["pay_flow"] = None              # fresh investor query each time
    at.run()
    at.button(key=rail_btn).click().run()
    assert at.session_state["pay_flow"]["stage"] == "interact", rail_btn
    at.button(key=ok_btn).click().run()
    assert not at.exception, ok_btn
    s = at.session_state["last_settlement"]
    if expected == "Stellar":
        assert s["rail"].startswith("Stellar testnet") or "simulated" in s["rail"], s["rail"]
    else:
        assert s["rail"] == expected, (expected, s["rail"])
    print(f"  rail ok: {s['rail']}")

# Page 3: settlement + data dividend held in state and rendered by render_settlement()
s = at.session_state["last_settlement"]
assert s["dividend_php"] == 3.50 and s["originator_wallet"] == "0xUser1"

print("SMOKE OK — boot, local-AI receipt, notarize, 402 query, 4-rail settlement, dividends all pass.")
