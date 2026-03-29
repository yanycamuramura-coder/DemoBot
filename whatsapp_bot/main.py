from fastapi import FastAPI, Query, Request
from fastapi.responses import PlainTextResponse, JSONResponse
import os
import requests

app = FastAPI()

# =========================
# CONFIGURAÇÕES
# =========================
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# =========================
# HEALTH CHECK (IMPORTANTE PRO RENDER)
# =========================
@app.get("/")
def home():
    return {"status": "running"}

# =========================
# ESTADO DOS USUÁRIOS
# =========================
user_state = {}

# =========================
# VERIFICAÇÃO DO WEBHOOK (GET)
# =========================
@app.get("/webhook", response_class=PlainTextResponse)
def webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    print("Verificação recebida")

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        print("Webhook verificado com sucesso")
        return hub_challenge

    print("Falha na verificação")
    return PlainTextResponse("Forbidden", status_code=403)

# =========================
# RECEBER MENSAGENS (POST)
# =========================
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        print("Recebi dados:", data)

        entry = data.get("entry", [])
        if not entry:
            return {"status": "no entry"}

        changes = entry[0].get("changes", [])
        if not changes:
            return {"status": "no changes"}

        value = changes[0].get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "no messages"}

        for message in messages:
            sender = message.get("from")

            if not sender:
                continue

            # =========================
            # TEXTO
            # =========================
            if message["type"] == "text":
                text = message["text"]["body"].strip().lower()

                greetings = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "olaa"]
                if any(g in text for g in greetings):
                    send_buttons(
                        sender,
                        "Olá 👋 Bem-vindo! Como posso ajudar?",
                        [
                            {"id": "menu", "title": "📖 Menu"},
                            {"id": "pedido", "title": "🛒 Pedido"},
                            {"id": "atendente", "title": "👤 Atendente"}
                        ]
                    )
                    user_state.pop(sender, None)
                    continue

                if sender in user_state and user_state[sender].get("step") == "pedido":
                    item = user_state[sender]["item"]
                    detalhes = message["text"]["body"].strip()

                    send_text(
                        sender,
                        f"Pedido confirmado ✅\n*{item}*\nDetalhes: {detalhes}"
                    )

                    user_state.pop(sender, None)
                    continue

            # =========================
            # BOTÕES
            # =========================
            elif message["type"] == "interactive":
                button_id = message["interactive"]["button_reply"]["id"]

                if button_id == "menu":
                    send_buttons(
                        sender,
                        "Menu 🍔🍕",
                        [
                            {"id": "pizza", "title": "🍕 Pizza"},
                            {"id": "hamburguer", "title": "🍔 Hambúrguer"},
                            {"id": "bebidas", "title": "🥤 Bebidas"}
                        ]
                    )

                elif button_id == "pedido":
                    send_buttons(
                        sender,
                        "Escolha o item:",
                        [
                            {"id": "pizza", "title": "🍕 Pizza"},
                            {"id": "hamburguer", "title": "🍔 Hambúrguer"},
                            {"id": "bebidas", "title": "🥤 Bebidas"}
                        ]
                    )
                    user_state[sender] = {"step": "escolha_item"}

                elif button_id in ["pizza", "hamburguer", "bebidas"]:
                    item_map = {
                        "pizza": "Pizza",
                        "hamburguer": "Hambúrguer",
                        "bebidas": "Bebidas"
                    }

                    item = item_map[button_id]

                    send_text(
                        sender,
                        f"Escolheste *{item}* 😋\nEnvia detalhes (quantidade, endereço, etc)."
                    )

                    user_state[sender] = {"step": "pedido", "item": item}

                elif button_id == "atendente":
                    send_text(sender, "Já vou chamar um atendente 👍")

    except Exception as e:
        print("ERRO:", str(e))

    return JSONResponse({"status": "ok"}, status_code=200)

# =========================
# ENVIO DE MENSAGENS
# =========================
def send_text(to: str, message: str):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }

    r = requests.post(url, headers=headers, json=payload)
    print("Send text:", r.json())


def send_buttons(to: str, message: str, buttons: list):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": message},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": b["id"],
                            "title": b["title"]
                        }
                    } for b in buttons
                ]
            }
        }
    }

    r = requests.post(url, headers=headers, json=payload)
    print("Send buttons:", r.json())
