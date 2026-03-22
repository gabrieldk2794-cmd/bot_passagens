import requests
import time
from datetime import datetime
import telebot

from config import *
from database import *

bot = telebot.TeleBot(TOKEN)

criar_tabela()


# =========================
# 🧠 SCORE INTELIGENTE
# =========================
def calcular_score(preco, media, desvio, dias, duracao):

    # 🔥 BOOTSTRAP (início do sistema)
    if not media:
        return 65

    desconto = (media - preco) / media
    raridade = (media - preco) / desvio if desvio else 0

    # 📅 timing
    if dias < 7:
        timing = 1.0
    elif dias < 30:
        timing = 0.7
    else:
        timing = 0.3

    # ✈️ qualidade do voo
    if duracao <= 3:
        qualidade = 1.0
    elif duracao <= 6:
        qualidade = 0.7
    else:
        qualidade = 0.4

    score = (
        desconto * 50 +
        raridade * 20 +
        timing * 15 +
        qualidade * 15
    )

    return max(0, min(100, score))


# =========================
# ✈️ BUSCA DE VOOS
# =========================
def buscar_passagens():

    melhores = []

    for destino in DESTINOS:

        url = "https://kiwi-com-cheap-flights.p.rapidapi.com/round-trip"

        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "kiwi-com-cheap-flights.p.rapidapi.com"
        }

        params = {
            "source": ORIGEM,
            "destination": destino,
            "currency": "BRL"
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()

            voos = data.get("data", [])[:3]

            for voo in voos:

                preco = voo.get("price", 0)
                duracao = voo.get("duration", 0) / 3600
                companhia = voo.get("airlines", ["N/A"])[0]
                data_voo = voo.get("route", [{}])[0].get("local_departure", "")

                if not preco or not data_voo:
                    continue

                try:
                    data_voo_dt = datetime.fromisoformat(data_voo)
                except:
                    continue

                dias = (data_voo_dt - datetime.now()).days

                # 💾 salva histórico
                salvar_preco(ORIGEM, destino, data_voo, preco, duracao, companhia)

                # 📊 estatísticas
                media, desvio = obter_stats(ORIGEM, destino)

                # 🧠 score
                score = calcular_score(preco, media, desvio, dias, duracao)

                print(f"{destino} | R$ {preco} | Score: {score:.1f}")

                # 🎯 filtro inteligente
                if score >= SCORE_MINIMO:
                    melhores.append({
                        "destino": destino,
                        "preco": preco,
                        "duracao": duracao,
                        "companhia": companhia,
                        "dias": dias,
                        "score": score
                    })

        except Exception as e:
            print(f"Erro em {destino}: {e}")

    return melhores


# =========================
# 📩 ENVIO DE ALERTAS
# =========================
def enviar_alertas():

    melhores = buscar_passagens()

    if not melhores:
        print("Nenhuma promo relevante")
        return

    melhores.sort(key=lambda x: x["score"], reverse=True)
    top = melhores[:3]

    msg = "🔥 TOP PROMOÇÕES AGORA:\n\n"
    enviados = 0

    for i, voo in enumerate(top, 1):

        # 🚫 anti-spam
        if ja_enviado(ORIGEM, voo["destino"], voo["preco"]):
            continue

        registrar_alerta(ORIGEM, voo["destino"], voo["preco"])

        link = f"https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{voo['destino']}"

        msg += f"""
{i}. ✈️ {ORIGEM} → {voo['destino']}
💰 R$ {voo['preco']}
📊 Score: {voo['score']:.0f}/100

🕒 {voo['duracao']:.1f}h
📅 Daqui {voo['dias']} dias

🔗 {link}

"""
        enviados += 1

    if enviados > 0:
        print("Enviando alerta...")
        bot.send_message(CHAT_ID, msg)
    else:
        print("Nada novo para enviar")


# =========================
# 🤖 COMANDOS TELEGRAM
# =========================
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "✈️ Bot de passagens ativo!")


@bot.message_handler(commands=['buscar'])
def buscar_cmd(msg):
    enviar_alertas()
    bot.send_message(msg.chat.id, "🔍 Busca finalizada!")


# =========================
# 🔁 LOOP PRINCIPAL
# =========================
def main():
    while True:
        print("Buscando passagens...")
        enviar_alertas()
        time.sleep(INTERVALO)


# =========================
# 🚀 INÍCIO
# =========================
if __name__ == "__main__":
    print("Bot iniciado!")
    bot.send_message(CHAT_ID, "🚀 Bot rodando em modo inteligente!")
    main()