import requests
import time
from datetime import datetime, timezone
import telebot

from config import *
from database import *

print("🚀 Iniciando bot...")

# =========================
# 🔐 INIT
# =========================
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
# ⚙️ CONFIG
# =========================
REQUESTS_POR_DIA = 3
INTERVALO = int(86400 / REQUESTS_POR_DIA)


# =========================
# ✈️ BUSCA REAL (ESTÁVEL)
# =========================
def buscar_passagens():
    print("🔍 Buscando passagens reais...")

    resultados = []

    for destino in DESTINOS:

        try:
            url = "http://api.aviationstack.com/v1/flights"

            params = {
                "access_key": AVIATIONSTACK_KEY,
                "dep_iata": ORIGEM,
                "arr_iata": destino
            }

            response = requests.get(url, params=params)
            print(f"API {destino}:", response.status_code)

            data = response.json()
            voos = data.get("data", [])[:2]

            for voo in voos:

                companhia = voo.get("airline", {}).get("name", "N/A")
                partida = voo.get("departure", {}).get("scheduled")

                if not partida:
                    continue

                try:
                    dt = datetime.fromisoformat(partida.replace("Z", "+00:00"))
                    dias = (dt - datetime.now(timezone.utc)).days
                except Exception as e:
                    print("Erro datetime:", e)
                    continue

                # 🔧 preço simulado (API não fornece preço)
                preco = 300 + (hash(destino + companhia) % 300)

                resultados.append({
                    "destino": destino,
                    "preco": preco,
                    "companhia": companhia,
                    "dias": dias,
                    "score": 50
                })

        except Exception as e:
            print(f"Erro {destino}:", e)

    print("TOTAL VOOS:", len(resultados))

    return resultados


# =========================
# 📩 ALERTAS
# =========================
def enviar_alertas():
    print("📩 Preparando alertas...")

    voos = buscar_passagens()

    if not voos:
        print("⚠️ Nenhum voo encontrado")
        return

    msg = "🔥 VOOS ENCONTRADOS:\n\n"

    for voo in voos[:3]:
        msg += f"""
✈️ {ORIGEM} → {voo['destino']}
💰 R$ {voo['preco']}
📅 {voo['dias']} dias
"""

    try:
        bot.send_message(CHAT_ID, msg)
        print("✅ Enviado com sucesso")
    except Exception as e:
        print("❌ Erro Telegram:", e)


# =========================
# 🔁 LOOP
# =========================
def main():
    print("🔁 Entrando no loop...")

    while True:
        enviar_alertas()
        print(f"⏱ Aguardando {INTERVALO/3600:.1f} horas...")
        time.sleep(INTERVALO)


# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    try:
        print("🚀 Start principal")

        bot.send_message(CHAT_ID, "🚀 Bot ativo no Railway (Fase 1)")
        main()

    except Exception as e:
        print("💥 ERRO FATAL:", e)
