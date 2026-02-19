# main.py
import os
import json
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

# =========================
# ENV CHECK
# =========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN missing")

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY missing")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini"

TEMP_ROUTER = float(os.environ.get("TEMP_ROUTER", "0.0"))
TEMP_ANALYSIS = float(os.environ.get("TEMP_ANALYSIS", "0.2"))
TEMP_STRATEGY = float(os.environ.get("TEMP_STRATEGY", "0.4"))

print("🔧 MODEL:", MODEL)
print("🔧 TEMP_ROUTER:", TEMP_ROUTER)
print("🔧 TEMP_ANALYSIS:", TEMP_ANALYSIS)
print("🔧 TEMP_STRATEGY:", TEMP_STRATEGY)

app = FastAPI()

# =========================
# SYSTEM PROMPTS
# =========================

SYS_ROUTER = """
You are a strict routing AI.

Available modules:
- feedstock
- compete
- policy
- downstream

Return JSON only like:
{
  "modules": ["feedstock","compete"]
}
"""

SYS_FEEDSTOCK = """
Feedstock & Energy Controller.
1) Key change
2) Margin impact
3) Operational action
4) Premium impact
"""

SYS_COMPETE = """
Competition Intelligence.
1) Competitive shift
2) Our impact
3) Tactical response
4) Premium defense
"""

SYS_POLICY = """
Policy & Regulation.
1) Policy summary
2) Business impact
3) Required action
"""

SYS_DOWNSTREAM = """
Downstream & Customer.
1) Demand signal
2) Customer issue
3) Premium opportunity
4) Execution
"""

SYS_LENS = """
You are LG Chem Strategy Lens.
Integrate analysis into executive-level decision.

1) Meaning for LG Chem
2) Good options (2)
3) Risk option (1)
4) 30/90/180 day roadmap
"""

AGENT_MAP = {
    "feedstock": SYS_FEEDSTOCK,
    "compete": SYS_COMPETE,
    "policy": SYS_POLICY,
    "downstream": SYS_DOWNSTREAM,
}

# =========================
# LLM FUNCTION (DEBUG)
# =========================
def llm(system: str, user: str, temp: float):
    try:
        print("🧠 LLM CALL | temp:", temp)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temp,
        )
        result = response.choices[0].message.content.strip()
        print("✅ LLM SUCCESS")
        return result

    except Exception as e:
        print("❌ LLM CALL FAILED:", str(e))
        raise e

# =========================
# TELEGRAM SEND (DEBUG)
# =========================
def send_message(chat_id: int, text: str):
    MAX_LEN = 3500
    parts = [text[i:i+MAX_LEN] for i in range(0, len(text), MAX_LEN)] or [""]

    for part in parts:
        try:
            r = requests.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": part},
                timeout=20,
            )
            print("📤 Telegram response:", r.status_code, r.text)
        except Exception as e:
            print("❌ Telegram send error:", str(e))

# =========================
# WEBHOOK
# =========================
@app.post("/webhook")
async def webhook(req: Request):

    update = await req.json()
    print("📥 RAW UPDATE:", update)

    msg = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
        or update.get("edited_channel_post")
    )

    if not msg:
        print("No message found in update")
        return {"ok": True}

    chat_id = msg["chat"]["id"]
    text = msg.get("text")

    print("📝 TEXT:", text)

    if not text or "/ops" not in text:
        return {"ok": True}

    parts = text.split(" ", 1)
    question = parts[1].strip() if len(parts) > 1 else ""

    print("❓ QUESTION:", question)

    if not question:
        send_message(chat_id, "질문을 같이 적어주세요.")
        return {"ok": True}

    # =========================
    # ROUTER
    # =========================
    try:
        router_raw = llm(SYS_ROUTER, question, TEMP_ROUTER)
        print("🧭 ROUTER RAW:", router_raw)

        router_json = json.loads(router_raw)
        modules = router_json.get("modules", [])

        print("🧭 ROUTER MODULES:", modules)

    except Exception as e:
        print("❌ ROUTER FAILED:", str(e))
        modules = ["compete", "downstream"]

    analysis_results = []

    # =========================
    # ANALYSIS AGENTS
    # =========================
    for m in modules:
        if m in AGENT_MAP:
            try:
                print("🚀 Running agent:", m)
                result = llm(AGENT_MAP[m], question, TEMP_ANALYSIS)
                analysis_results.append(f"📌 [{m.upper()}]\n{result}")
            except Exception as e:
                print("❌ Agent failed:", m, str(e))
                analysis_results.append(f"⚠ [{m}] error: {str(e)}")

    combined_text = "\n\n".join(analysis_results)

    # =========================
    # STRATEGY LENS
    # =========================
    try:
        print("🎯 Running Strategy Lens")
        final_strategy = llm(SYS_LENS, combined_text, TEMP_STRATEGY)
        analysis_results.append(f"\n🔥 [LG STRATEGY LENS]\n{final_strategy}")
    except Exception as e:
        print("❌ Strategy Lens failed:", str(e))

    final_output = "\n\n".join(analysis_results)

    send_message(chat_id, final_output)

    return {"ok": True}
