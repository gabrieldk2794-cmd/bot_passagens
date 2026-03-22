import requests
import time
from datetime import datetime
import telebot

from config import *
from database import *

bot = telebot.TeleBot(TOKEN)

criar_tabela()


# =========================
# 🧠 CLASSIFICAÇÃO
# =========================
def classificar_oferta(score):
    if score >= 80:
        return "🔥 IMPERDÍVEL"
    elif score >= 65:
        return "🚀 ÓTIMA"
    elif score >= 50:
        return "✈️ BOA"
    else:
        return "⚠️ NORMAL"


# =========================
# 🧠 SCORE PRO
# =========================
def calcular_score(preco, media, desvio, dias, duracao, historico):

    if not media:
        deal_score = 50
    else:
        desconto = (media - preco) / media
        deal_score = desconto * 100

    trend_score = 0
    if historico and len(historico) >= 3:
        recente = historico[:3]
        antigo = historico[-3:]

        media_recente = sum(recente) / len(recente)
        media_antiga = sum(antigo) / len(antigo)

        if media_antiga > 0:
            queda = (media_antiga - media_recente) / media_antiga
            trend_score = queda * 100

    if dias < 7:
        urgencia = 100
    elif dias < 15:
        urgencia = 80
    elif dias < 30:
        urgencia = 60
    else:
        urgencia = 30

    if duracao <= 3:
        qualidade = 100
    elif duracao <= 6:
        qualidade = 70
    else:
        qualidade = 40

    score = (
        deal_score * 0.4 +
        trend_score * 0.2 +
        urgencia * 0.2 +
        qualidade * 0.2
    )

    return max(0, min(100, score))


# =========================
# ✈️ BUSCA (AVIATIONSTACK + FALLBACK)
# =========================
def buscar_passagens():

    resultados = []

    base_precos = {
        "GRU": 250, "GIG": 300, "SSA": 500, "REC": 600,
        "FOR": 700, "BSB": 300, "POA": 650,
        "CUR": 200, "FLN": 400, "MCZ": 650
    }

    for destino in DESTINOS:

        try:
            url = "http://api.aviationstack.com/v1/flights"

            params = {
                "access_key": AVIATIONSTACK_KEY,
                "dep_iata": ORIGEM,
                "arr_iata": destino
            }

            response = requests.get(url, params=params)
            data = response.json()

            print(f"\n==== AVIATIONSTACK ({destino}) ====")
            print(data)

            voos = data.get("data", [])[:3]

            if not isinstance(voos, list):
                voos = []

            for voo in voos:

                companhia = voo.get("airline", {}).get("name", "N/A")
                partida = voo.get("departure", {}).get("scheduled")

                if not partida:
                    continue

                try:
                    data_voo_dt = datetime.fromisoformat(partida.replace("Z", ""))
                except:
                    continue

                dias = (data_voo_dt - datetime.now()).days

                variacao = (hash(destino + companhia) % 200)
                preco = base_precos.get(destino, 400) + variacao
                duracao = 1.5 + (hash(companhia) % 5)

                salvar_preco(ORIGEM, destino, partida, preco, duracao, companhia)

                media, desvio = obter_stats(ORIGEM, destino)
                historico = historico_recente(ORIGEM, destino)

                score = calcular_score(preco, media, desvio, dias, duracao, historico)

                resultados.append({
                    "destino": destino,
                    "preco": preco,
                    "duracao": duracao,
                    "companhia": companhia,
                    "dias": dias,
                    "score": score
                })

        except Exception as e:
            print(f"Erro API {destino}: {e}")

    # =========================
    # 🚨 FALLBACK INTELIGENTE
    # =========================
    if not resultados:
        print("⚠️ ATIVANDO FALLBACK")

        for destino in DESTINOS:
            preco = base_precos.get(destino, 400) + (hash(destino) % 300)

            resultados.append({
                "destino": destino,
                "preco": preco,
                "duracao": 2.5,
                "companhia": "Fallback",
                "dias": 30,
                "score": 50
            })

    print(f"TOTAL VOOS ENCONTRADOS: {len(resultados)}")

    return resultados


# =========================
# 📩 ALERTAS
# =========================
def enviar_alertas():

    voos = buscar_passagens()

    print("VOOS BRUTOS:", len(voos))

    # 🔥 DESATIVANDO FILTRO PRA TESTE
    melhores = voos if voos else []

    print("VOOS FILTRADOS:", len(melhores))

    if not melhores:
        bot.send_message(CHAT_ID, "⚠️ Sem dados suficientes, mas o bot está ativo.")
        return

    melhores.sort(key=lambda x: x["score"], reverse=True)

    msg = "🔥 TOP PROMOÇÕES:\n\n"

    enviados = 0

    for voo in melhores[:3]:

        if ja_enviado(ORIGEM, voo["destino"], voo["preco"]):
            continue

        registrar_alerta(ORIGEM, voo["destino"], voo["preco"])

        tag = classificar_oferta(voo["score"])

        link = f"https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{voo['destino']}/{datetime.now().strftime('%y%m%d')}/"

        msg += f"""
{tag}

✈️ {ORIGEM} → {voo['destino']}
💰 R$ {voo['preco']}
📊 Score: {voo['score']:.0f}

🕒 {voo['duracao']:.1f}h
📅 {voo['dias']} dias

🔎 Ver preço real:
{link}

"""
        enviados += 1

    if enviados > 0:
        print("Enviando alerta...")
        bot.send_message(CHAT_ID, msg)
    else:
        print("Nada novo para enviar")


# =========================
# 🔁 LOOP
# =========================
def main():
    while True:
        print("Rodando busca...")
        enviar_alertas()
        time.sleep(INTERVALO)


# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    bot.send_message(CHAT_ID, "🚀 Bot PRO rodando (com fallback inteligente)")
    main()
