import os
import requests
from fastapi import FastAPI, Request

BOT_TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI()

def send_message(chat_id: int, text: str):
    try:
        r = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=20,)
        print("Telegram response:", r.status_code, r.text)
    except Exception as e:
        print("Telegram send exception:", e)


@app.post("/webhook")
async def webhook(req: Request):
    update = await req.json()
    print("RAW UPDATE:", update)

    msg = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post"))

    if not msg:
        return {"ok": True}

    chat_id = msg["chat"]["id"]
    text = msg.get("text")

    if not text:
        return {"ok": True}

    if "/ops" not in text:
        return {"ok": True}

    parts = text.split(" ", 1)
    question = parts[1] if len(parts) > 1 else ""

    if not question:
        send_message(chat_id, "질문을 같이 적어주세요.")
        return {"ok": True}

    send_message(chat_id, f"질문 확인: {question}")

    return {"ok": True}
