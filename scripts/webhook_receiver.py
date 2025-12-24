from fastapi import FastAPI, Request
import uvicorn
import logging

app = FastAPI()

# Simple logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

@app.post("/webhook")
async def webhook_receiver(request: Request):
    """
    Receives alerts from the main proxy via webhook.
    Logs them and returns acknowledgement.
    """
    data = await request.json()
    logging.info(f"🚨 Webhook alert received: {data}")
    return {"status": "ok", "received": data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
