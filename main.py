# main.py
import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

BOT_TOKEN = os.environ["BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL=os.environ.get("OPENAI_MODEL","gpt-4.1-mini")
TEMP_ROUTER=float(os.environ.get("TEMP_ROUTER","0.0"))
TEMP_ANALYSIS=float(os.environ.get("TEMP_ROUTER","0.2"))
TEMP_STRATEGY=float(os.environ.get("TEMP_ROUTER","0.4"))

app = FastAPI()

# --- Agent System Prompts ---
SYS_FEEDSTOCK = """... (위 내용 그대로) ..."""
SYS_COMPETE = """..."""
SYS_POLICY = """..."""
SYS_DOWNSTREAM = """..."""
SYS_LENS = """..."""

AGENTS = [
    ("Feedstock Ops", SYS_FEEDSTOCK),
    ("Compete Intel", SYS_COMPETE),
    ("Policy & K-Chem", SYS_POLICY),
    ("Downstream & Customer", SYS_DOWNSTREAM),
    ("LG Chem Lens", SYS_LENS),
]

def llm(system: str, user: str, temperatur: Float) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=TEMPERATURE,
    )
    return resp.choices[0].message.content.strip()

def send_message(chat_id: int, text: str):
    print("Sending message to Telegram... chat_id=", chat_id)

    try:
        r = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            },
            timeout=20
        )
        print("Telegram response:", r.status_code, r.text)

    except Exception as e:
        print("Telegram send exception:", e)

@app.post("/webhook")
async def webhook(req: Request):
    update = await req.json()
        print("raw update:", update)

    msg = update.get("message") or update.get("edited_message") or update.get("channel_post")
    if not msg:
        print("no message found in update")
        return {"ok": True}

    text = msg.get("text")
        print("extracted text:", text)
    if not text:
        return {"ok": True}

    # 트리거 명령어
    if text.startswith("/ops"):
        question=text.split(" ",1)[1] if " " in text else ""
    elif text.startswith("/ops@"):
        parts=text.split(" ",1)
        question=parts[1] if len(parts) > 1
        else ""
    else:
    if not question:
        send_message(chat_id, "질문을 같이 적어주세요.")
        return {"ok": True}

    # --- Orchestrator ---
    outputs = []
    for name, sys in AGENTS:
        if name == "LG Chem Lens":
            temp=TEMP_STRATEGY
        else:
            temp=TEMP_ANALYSIS
        try:
            ans = llm(sys, question)
            outputs.append(f"📌 [{name}]\n{ans}")
        except Exception as e:
            outputs.append(f"⚠ [{name}] 오류 발생")

    final_report = "\n\n".join(outputs)

    send_message(chat_id, final_report)
    return {"ok": True}
