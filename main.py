import requests
import time
from datetime import datetime
import telebot

from config import *
from database import *

bot = telebot.TeleBot(TOKEN)

criar_tabela()

ultimo_relatorio = None


# =========================
# 🧠 SCORE INTELIGENTE
# =========================
def calcular_score(preco, media, desvio, dias, duracao):

    if not media:
        return 65

    desconto = (media - preco) / media
    raridade = (media - preco) / desvio if desvio else 0

    if dias < 7:
        timing = 1.0
    elif dias < 30:
        timing = 0.7
    else:
        timing = 0.3

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

    resultados = []

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

                salvar_preco(ORIGEM, destino, data_voo, preco, duracao, companhia)

                media, desvio = obter_stats(ORIGEM, destino)

                score = calcular_score(preco, media, desvio, dias, duracao)

                print(f"{destino} | R$ {preco} | Score: {score:.1f}")

                resultados.append({
                    "destino": destino,
                    "preco": preco,
                    "duracao": duracao,
                    "companhia": companhia,
                    "dias": dias,
                    "score": score
                })

        except Exception as e:
            print(f"Erro em {destino}: {e}")

    return resultados


# =========================
# 📩 ALERTAS INTELIGENTES
# =========================
def enviar_alertas():

    voos = buscar_passagens()

    melhores = [v for v in voos if v["score"] >= SCORE_MINIMO]

    if not melhores:
        print("Nenhuma promo relevante")
        return

    melhores.sort(key=lambda x: x["score"], reverse=True)
    top = melhores[:3]

    msg = "🔥 TOP PROMOÇÕES AGORA:\n\n"
    enviados = 0

    for i, voo in enumerate(top, 1):

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
# 📊 RELATÓRIO DIÁRIO (TESTE FORÇADO)
# =========================
def enviar_relatorio_diario():

    print("Gerando relatório diário...")

    voos = buscar_passagens()

    if not voos:
        bot.send_message(CHAT_ID, "📊 Nenhum voo encontrado hoje.")
        return

    voos.sort(key=lambda x: x["preco"])
    top = voos[:5]

    msg = "📊 MELHORES PREÇOS DE HOJE:\n\n"

    for i, voo in enumerate(top, 1):
        msg += f"""
{i}. ✈️ {ORIGEM} → {voo['destino']}
💰 R$ {voo['preco']}
📊 Score: {voo['score']:.0f}

🕒 {voo['duracao']:.1f}h
📅 {voo['dias']} dias

"""

    bot.send_message(CHAT_ID, msg)


# =========================
# 🔁 LOOP PRINCIPAL
# =========================
def main():
    global ultimo_relatorio

    while True:
        print("Buscando passagens...")
        enviar_alertas()

        # 🔥 FORÇADO PRA TESTE (vai mandar sempre)
        if True:
            if ultimo_relatorio != datetime.now().date():
                enviar_relatorio_diario()
                ultimo_relatorio = datetime.now().date()

        time.sleep(INTERVALO)


# =========================
# 🚀 INÍCIO
# =========================
if __name__ == "__main__":
    print("Bot iniciado!")
    bot.send_message(CHAT_ID, "🚀 TESTE: Bot com relatório diário ativo!")
    main()
