from fastapi import FastAPI, Query, Request
from fastapi.responses import PlainTextResponse
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
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return hub_challenge
    return "forbidden"

# =========================
# RECEBER MENSAGENS (POST)
# =========================
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        print("Recebi dados:", data)

        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        for message in messages:
            sender = message["from"]

            # =========================
            # TEXTO
            # =========================
            if message["type"] == "text":
                text = message["text"]["body"].strip().lower()

                # SAUDAÇÕES INICIAIS
                greetings = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "olaa"]
                if any(g in text for g in greetings):
                    send_buttons(
                        sender,
                        "Olá 👋 Bem-vindo ao nosso restaurante! Como posso ajudar?",
                        [
                            {"id": "menu", "title": "📖 Ver Menu"},
                            {"id": "pedido", "title": "🛒 Fazer Pedido"},
                            {"id": "atendente", "title": "👤 Atendente"}
                        ]
                    )
                    user_state.pop(sender, None)
                    continue

                # RECEBER PEDIDO FINAL
                if sender in user_state and user_state[sender].get("step") == "pedido":
                    item = user_state[sender]["item"]
                    detalhes = message["text"]["body"].strip()

                    send_text(
                        sender,
                        f"Perfeito ✅\nSeu pedido de *{item}* foi registrado.\nDetalhes: {detalhes}\n\nEm breve vamos confirmar o seu pedido!"
                    )

                    user_state.pop(sender, None)
                    continue

            # =========================
            # BOTÕES
            # =========================
            elif message["type"] == "interactive":
                button_id = message["interactive"]["button_reply"]["id"]

                # VER MENU
                if button_id == "menu":
                    send_buttons(
                        sender,
                        "Aqui está o nosso menu 🍔🍕\nEscolha uma opção:",
                        [
                            {"id": "pizza", "title": "🍕 Pizza"},
                            {"id": "hamburguer", "title": "🍔 Hambúrguer"},
                            {"id": "bebidas", "title": "🥤 Bebidas"}
                        ]
                    )
                    continue

                # FAZER PEDIDO
                elif button_id == "pedido":
                    send_buttons(
                        sender,
                        "O que deseja pedir?",
                        [
                            {"id": "pizza", "title": "🍕 Pizza"},
                            {"id": "hamburguer", "title": "🍔 Hambúrguer"},
                            {"id": "bebidas", "title": "🥤 Bebidas"}
                        ]
                    )
                    user_state[sender] = {"step": "escolha_item"}
                    continue

                # ESCOLHA DO ITEM
                elif button_id in ["pizza", "hamburguer", "bebidas"]:
                    item_map = {
                        "pizza": "Pizza",
                        "hamburguer": "Hambúrguer",
                        "bebidas": "Bebidas"
                    }
                    item = item_map[button_id]

                    send_text(
                        sender,
                        f"Boa escolha 😋\nVocê escolheu *{item}*.\n\nEnvie os detalhes do seu pedido (quantidade, sabor, endereço, etc)."
                    )

                    user_state[sender] = {"step": "pedido", "item": item}
                    continue

                # ATENDENTE HUMANO
                elif button_id == "atendente":
                    send_text(sender, "Ok 👍 Vou te encaminhar para um atendente.")
                    continue

    except Exception as e:
        print("Erro ao processar mensagem:", e)

    return {"status": "ok"}

# =========================
# FUNÇÕES DE ENVIO
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
    resp = requests.post(url, headers=headers, json=payload)
    print("Resposta WhatsApp (text):", resp.json())

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

    resp = requests.post(url, headers=headers, json=payload)
    print("Resposta WhatsApp (buttons):", resp.json())
