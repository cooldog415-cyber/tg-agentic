import os
import json
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

# =========================
# Env
# =========================
BOT_TOKEN = os.environ["BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

TEMP_ROUTER = float(os.environ.get("TEMP_ROUTER", "0.0"))
TEMP_ANALYSIS = float(os.environ.get("TEMP_ANALYSIS", "0.2"))
TEMP_STRATEGY = float(os.environ.get("TEMP_STRATEGY", "0.4"))

app = FastAPI()

# =========================
# System Prompts
# =========================

SYS_ROUTER = """
You are a strict routing AI.
Classify the question into required analysis modules.

Available modules:
- feedstock
- compete
- policy
- downstream
- strategy

Return JSON only:
{
  "modules": ["feedstock","compete"],
  "reason": "short explanation"
}
Do NOT explain outside JSON.
"""

SYS_FEEDSTOCK = """Feedstock & Energy Controller.
Focus: oil, naphtha, LPG, utilities, spreads, FX.
Format:
1) Key shift
2) Margin impact
3) Operational action
4) Premium product impact
"""

SYS_COMPETE = """Competition Intelligence.
Focus: capacity, dumping, TA, region shifts.
Format:
1) Competitive event
2) Impact
3) Tactical response
4) Premium defense
"""

SYS_POLICY = """Policy & Regulation.
Focus: CBAM, carbon, trade, domestic competitiveness.
Format:
1) Policy summary
2) Business impact
3) Required action
"""

SYS_DOWNSTREAM = """Downstream & Customers.
Focus: Auto, battery, construction, packaging.
Format:
1) Demand signal
2) Customer pain point
3) Premium opportunity
4) Execution step
"""

SYS_LENS = """LG Chem Strategy Lens.
Deliver executive-level action.
Format:
1) Meaning for LG Chem
2) Good options (2)
3) Bad option (1)
4) 30/90/180 day roadmap
"""

AGENT_MAP = {
    "feedstock": SYS_FEEDSTOCK,
    "compete": SYS_COMPETE,
    "policy": SYS_POLICY,
    "downstream": SYS_DOWNSTREAM,
}

# =========================
# LLM Helper
# =========================
def llm(system: str, user: str, temp: float):
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temp,
    )
    return resp.choices[0].message.content.strip()


def send_message(chat_id: int, text: str):
    MAX_LEN = 3800
    chunks = [text[i:i+MAX_LEN] for i in range(0, len(text), MAX_LEN)] or [""]

    for c in chunks:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": c},
            timeout=20,
        )

# =========================
# Webhook
# =========================
@app.post("/webhook")
async def webhook(req: Request):
    update = await req.json()

    msg = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
        or update.get("edited_channel_post")
    )

    if not msg:
        return {"ok": True}

    chat_id = msg["chat"]["id"]
    text = msg.get("text")

    if not text or "/ops" not in text:
        return {"ok": True}

    parts = text.split(" ", 1)
    question = parts[1].strip() if len(parts) > 1 else ""

    if not question:
        send_message(chat_id, "질문을 같이 적어주세요.")
        return {"ok": True}

    # =========================
    # 1️⃣ ROUTER 단계
    # =========================
    try:
        router_raw = llm(SYS_ROUTER, question, TEMP_ROUTER)
        router_json = json.loads(router_raw)
        modules = router_json.get("modules", [])
    except:
        modules = ["feedstock","compete","downstream"]

    outputs = []

    # =========================
    # 2️⃣ 필요한 Agent만 실행
    # =========================
    for m in modules:
        if m in AGENT_MAP:
            try:
                ans = llm(AGENT_MAP[m], question, TEMP_ANALYSIS)
                outputs.append(f"📌 [{m.upper()}]\n{ans}")
            except Exception as e:
                outputs.append(f"⚠ [{m}] error")

    # =========================
    # 3️⃣ 전략 통합 (Lens)
    # =========================
    combined_text = "\n\n".join(outputs)

    try:
        final = llm(SYS_LENS, combined_text, TEMP_STRATEGY)
        outputs.append(f"\n\n🔥 [LG STRATEGY LENS]\n{final}")
    except:
        pass

    final_report = "\n\n".join(outputs)

    send_message(chat_id, final_report)

    return {"ok": True}
