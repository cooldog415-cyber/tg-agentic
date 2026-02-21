import os
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

BOT_TOKEN = os.environ["BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

print("API KEY PREFIX:", OPENAI_API_KEY[:20])

client = OpenAI(api_key=OPENAI_API_KEY)

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI()

def send_message(chat_id: int, text: str):
    try:
        r = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=20,
        )
        print("Telegram response:", r.status_code)
    except Exception as e:
        print("Telegram send error:", e)

@app.post("/webhook")
async def webhook(req: Request):
    update = await req.json()
    print("RAW UPDATE:", update)

    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return {"ok": True}

    chat_id = msg["chat"]["id"]
    text = msg.get("text")

    if not text or "/ops" not in text:
        return {"ok": True}

    question = text.replace("/ops", "").strip()

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": question}],
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"OpenAI error: {e}"

    send_message(chat_id, answer)
    return {"ok": True}
