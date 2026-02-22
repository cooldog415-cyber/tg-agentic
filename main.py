import os
import httpx
from fastapi import FastAPI, Request
from openai import AsyncOpenAI

BOT_TOKEN = os.environ["BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
client = AsyncOpenAI(api_key=OPENAI_API_KEY)
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
app = FastAPI()

async def send_message(chat_id: int, text: str):
    try:
        async with httpx.AsyncClient() as http:
            r = await http.post(
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
    text = msg.get("text", "")

    if not text.startswith("/ops"):
        return {"ok": True}

    question = text[4:].strip()
    if not question:
        await send_message(chat_id, "질문을 입력해주세요. 예: /ops 오늘 날씨 어때?")
        return {"ok": True}

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question}],
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"OpenAI error: {e}"

    await send_message(chat_id, answer)
    return {"ok": True}
