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
assert at.session_state["ai_mode"] in ("local", "demo")

# Page 1: notarize to the Trust Vault
at.button(key="btn_notarize").click().run()
assert not at.exception, f"Notarize failed: {at.exception}"
assert at.session_state["notarized_id"], "no asset id after notarize"

# Page 2: query the vault -> 402 gate appears
at.button(key="btn_query").click().run()
assert not at.exception, f"Query failed: {at.exception}"

# Page 2: GCash rail -> QR -> simulated webhook
at.button(key="btn_gcash").click().run()
assert at.session_state["pay_flow"]["stage"] == "interact"
at.button(key="btn_gcash_ok").click().run()
assert not at.exception, f"GCash settle failed: {at.exception}"
assert at.session_state["pay_flow"]["stage"] == "done"
assert at.session_state["last_settlement"]["rail"] == "GCash"

# Page 3: settlement + data dividend held in state and rendered by render_settlement()
s = at.session_state["last_settlement"]
assert s["dividend_php"] == 3.50 and s["originator_wallet"] == "0xUser1"

print("SMOKE OK — boot, local-AI receipt, notarize, 402 query, GCash pay, settlement all pass.")
