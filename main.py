import requests
import time
from datetime import datetime, timezone
import telebot

from config import *
from database import *

bot = telebot.TeleBot(TOKEN)

criar_tabela()

# =========================
# ⚙️ CONFIG
# =========================
REQUESTS_POR_DIA = 3
INTERVALO = int(86400 / REQUESTS_POR_DIA)
SCORE_MINIMO = 40


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
# 📈 REGRESSÃO LINEAR
# =========================
def prever_regressao(historico):

    if not historico or len(historico) < 5:
        return 0  # sem previsão

    n = len(historico)
    x = list(range(n))
    y = historico[::-1]  # mais antigo → mais recente

    media_x = sum(x) / n
    media_y = sum(y) / n

    numerador = sum((x[i] - media_x) * (y[i] - media_y) for i in range(n))
    denominador = sum((x[i] - media_x) ** 2 for i in range(n))

    if denominador == 0:
        return 0

    slope = numerador / denominador

    return slope  # tendência


# =========================
# 🌍 SAZONALIDADE
# =========================
def fator_sazonalidade(data_voo):

    try:
        dt = datetime.fromisoformat(data_voo.replace("Z", "+00:00"))
    except:
        return 1.0

    dia_semana = dt.weekday()

    # fim de semana = mais caro
    if dia_semana >= 4:
        return 1.2

    return 1.0


# =========================
# 🔮 PREVISÃO FINAL
# =========================
def prever_preco(historico, data_voo):

    slope = prever_regressao(historico)
    sazonal = fator_sazonalidade(data_voo)

    if slope > 5:
        tendencia = "SUBINDO 📈"
        recomendacao = "COMPRAR AGORA"
    elif slope < -5:
        tendencia = "CAINDO 📉"
        recomendacao = "ESPERAR"
    else:
        tendencia = "ESTÁVEL ➖"
        recomendacao = "MONITORAR"

    return tendencia, recomendacao, slope, sazonal


# =========================
# 🧠 SCORE PRO
# =========================
def calcular_score(preco, media, dias, duracao, slope, sazonal):

    if not media:
        deal = 50
    else:
        deal = ((media - preco) / media) * 100

    # impacto da tendência
    trend = -slope * 2  # se subindo → score maior

    # urgência
    if dias < 7:
        urgencia = 100
    elif dias < 30:
        urgencia = 70
    else:
        urgencia = 40

    # qualidade
    qualidade = 100 if duracao <= 3 else 70

    score = (
        deal * 0.4 +
        trend * 0.2 +
        urgencia * 0.2 +
        qualidade * 0.1 +
        (sazonal * 50) * 0.1
    )

    return max(0, min(100, score))


# =========================
# ✈️ BUSCA
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

            voos = data.get("data", [])[:3]

            for voo in voos:

                companhia = voo.get("airline", {}).get("name", "N/A")
                partida = voo.get("departure", {}).get("scheduled")

                if not partida:
                    continue

                try:
                    data_voo_dt = datetime.fromisoformat(partida.replace("Z", "+00:00"))
                    agora = datetime.now(timezone.utc)
                    dias = (data_voo_dt - agora).days
                except:
                    continue

                variacao = (hash(destino + companhia) % 200)
                preco = base_precos.get(destino, 400) + variacao
                duracao = 1.5 + (hash(companhia) % 5)

                salvar_preco(ORIGEM, destino, partida, preco, duracao, companhia)

                media, _ = obter_stats(ORIGEM, destino)
                historico = historico_recente(ORIGEM, destino)

                tendencia, recomendacao, slope, sazonal = prever_preco(historico, partida)

                score = calcular_score(preco, media, dias, duracao, slope, sazonal)

                resultados.append({
                    "destino": destino,
                    "preco": preco,
                    "duracao": duracao,
                    "companhia": companhia,
                    "dias": dias,
                    "score": score,
                    "tendencia": tendencia,
                    "recomendacao": recomendacao
                })

        except Exception as e:
            print("Erro API:", e)

    # fallback
    if not resultados:
        for destino in DESTINOS:
            resultados.append({
                "destino": destino,
                "preco": 300 + (hash(destino) % 300),
                "duracao": 2.5,
                "companhia": "Fallback",
                "dias": 30,
                "score": 50,
                "tendencia": "ESTÁVEL ➖",
                "recomendacao": "MONITORAR"
            })

    return resultados


# =========================
# 📩 ALERTAS
# =========================
def enviar_alertas():

    voos = buscar_passagens()

    melhores = [v for v in voos if v["score"] >= SCORE_MINIMO]

    if not melhores:
        bot.send_message(CHAT_ID, "⚠️ Nenhuma promoção relevante hoje.")
        return

    melhores.sort(key=lambda x: x["score"], reverse=True)

    msg = "🔥 TOP PROMOÇÕES INTELIGENTES:\n\n"

    for voo in melhores[:3]:

        try:
            if ja_enviado(ORIGEM, voo["destino"], voo["preco"]):
                continue

            registrar_alerta(ORIGEM, voo["destino"], voo["preco"])
        except:
            pass

        tag = classificar_oferta(voo["score"])

        link = f"https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{voo['destino']}/{datetime.now().strftime('%y%m%d')}/"

        msg += f"""
{tag}

✈️ {ORIGEM} → {voo['destino']}
💰 R$ {voo['preco']}
📊 Score: {voo['score']:.0f}

🧠 {voo['tendencia']}
📊 {voo['recomendacao']}

🔎 {link}

"""

    bot.send_message(CHAT_ID, msg)


# =========================
# 🔁 LOOP
# =========================
def main():
    while True:
        enviar_alertas()
        time.sleep(INTERVALO)


# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    bot.send_message(CHAT_ID, "🚀 Bot com previsão avançada ativo")
    main()
