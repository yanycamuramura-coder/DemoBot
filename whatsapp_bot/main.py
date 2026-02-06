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
VERIFY_TOKEN = "meutoken123"

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
                        "Olá 👋 Sou o assistente da Clínica Saúde+. Como posso ajudar?",
                        [
                            {"id": "marcar", "title": "📅 Marcar consulta"},
                            {"id": "horarios", "title": "🕒 Horários"},
                            {"id": "atendente", "title": "👩‍⚕️ Atendente"}
                        ]
                    )
                    user_state.pop(sender, None)
                    continue

                # NOME DO USUÁRIO (após escolher especialidade)
                if sender in user_state and user_state[sender].get("step") == "nome":
                    especialidade = user_state[sender]["especialidade"]
                    nome = message["text"]["body"].strip()
                    send_text(
                        sender,
                        f"Perfeito ✅\nSeu agendamento em *{especialidade}* foi registrado para *{nome}*.\nEm breve entraremos em contato!"
                    )
                    user_state.pop(sender, None)
                    continue

            # =========================
            # BOTÕES
            # =========================
            elif message["type"] == "interactive":
                button_id = message["interactive"]["button_reply"]["id"]

                if button_id == "marcar":
                    send_buttons(
                        sender,
                        "Qual especialidade deseja?",
                        [
                            {"id": "clinica_geral", "title": "Clínica Geral"},
                            {"id": "pediatria", "title": "Pediatria"},
                            {"id": "odontologia", "title": "Odontologia"}
                        ]
                    )
                    user_state[sender] = {"step": "especialidade"}
                    continue

                elif button_id in ["clinica_geral", "pediatria", "odontologia"]:
                    especialidade_map = {
                        "clinica_geral": "Clínica Geral",
                        "pediatria": "Pediatria",
                        "odontologia": "Odontologia"
                    }
                    especialidade = especialidade_map[button_id]
                    send_text(
                        sender,
                        f"Perfeito ✅\nEnvie seu *nome completo* para confirmar o agendamento em {especialidade}."
                    )
                    user_state[sender] = {"step": "nome", "especialidade": especialidade}
                    continue

                elif button_id == "horarios":
                    send_text(sender, "Atendemos de segunda a sexta, das 08h às 17h.")
                    continue

                elif button_id == "atendente":
                    send_text(sender, "Ok 👍 Vou te encaminhar para a recepção.")
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

