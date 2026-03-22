import requests
import time
from datetime import datetime, timezone
import telebot

from config import *
from database import *

print("🚀 Iniciando bot...")

try:
    bot = telebot.TeleBot(TOKEN)
    print("✅ Telegram OK")
except Exception as e:
    print("❌ Erro Telegram:", e)

try:
    criar_tabela()
    print("✅ Banco OK")
except Exception as e:
    print("❌ Erro banco:", e)

# =========================
REQUESTS_POR_DIA = 3
INTERVALO = int(86400 / REQUESTS_POR_DIA)
SCORE_MINIMO = 40
# =========================


def buscar_passagens():
    print("🔍 Buscando passagens...")

    try:
        url = "http://api.aviationstack.com/v1/flights"
        params = {
            "access_key": AVIATIONSTACK_KEY,
            "dep_iata": ORIGEM,
            "arr_iata": DESTINOS[0]
        }

        response = requests.get(url, params=params)
        print("Status API:", response.status_code)

        data = response.json()
        print("Resposta API recebida")

        return [{"destino": DESTINOS[0], "preco": 300, "score": 50}]

    except Exception as e:
        print("❌ Erro API:", e)
        return []


def enviar_alertas():
    print("📩 Preparando envio...")

    voos = buscar_passagens()

    if not voos:
        print("⚠️ Nenhum voo")
        return

    try:
        bot.send_message(CHAT_ID, "✅ Bot rodando no Railway!")
        print("✅ Mensagem enviada")
    except Exception as e:
        print("❌ Erro envio Telegram:", e)


def main():
    print("🔁 Entrando no loop...")

    while True:
        enviar_alertas()
        print(f"⏱ Aguardando {INTERVALO}s")
        time.sleep(INTERVALO)


if __name__ == "__main__":
    try:
        print("🚀 Start principal")
        bot.send_message(CHAT_ID, "🚀 Deploy funcionando!")
        main()
    except Exception as e:
        print("💥 ERRO FATAL:", e)
