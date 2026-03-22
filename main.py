import requests
import time
from datetime import datetime, timezone
import telebot

from config import *
from database import *

print("🚀 Iniciando bot...")

bot = telebot.TeleBot(TOKEN)
criar_tabela()

# =========================
# ⚙️ CONFIG
# =========================
REQUESTS_POR_DIA = 3
INTERVALO = int(86400 / REQUESTS_POR_DIA)
SCORE_MINIMO = 40


# =========================
# 🧠 REGRESSÃO
# =========================
def prever_regressao(historico):

    if not historico or len(historico) < 5:
        return 0

    n = len(historico)
    x = list(range(n))
    y = historico[::-1]

    mx = sum(x) / n
    my = sum(y) / n

    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    den = sum((x[i] - mx) ** 2 for i in range(n))

    if den == 0:
        return 0

    return num / den


# =========================
# 🌍 SAZONALIDADE
# =========================
def fator_sazonalidade(data_voo):

    try:
        dt = datetime.fromisoformat(data_voo.replace("Z", "+00:00"))
        if dt.weekday() >= 4:
            return 1.2
    except:
        pass

    return 1.0


# =========================
# 🔮 PREVISÃO
# =========================
def prever_preco(historico, data_voo):

    slope = prever_regressao(historico)
    sazonal = fator_sazonalidade(data_voo)

    if slope > 5:
        return "SUBINDO 📈", "COMPRAR AGORA", slope, sazonal
    elif slope < -5:
        return "CAINDO 📉", "ESPERAR", slope, sazonal
    else:
        return "ESTÁVEL ➖", "MONITORAR", slope, sazonal


# =========================
# 🧠 SCORE
# =========================
def calcular_score(preco, media, dias, slope, sazonal):

    if not media:
        deal = 50
    else:
        deal = ((media - preco) / media) * 100

    trend = -slope * 2

    if dias < 7:
        urg = 100
    elif dias < 30:
        urg = 70
    else:
        urg = 40

    score = (
        deal * 0.5 +
        trend * 0.2 +
        urg * 0.2 +
        (sazonal * 50) * 0.1
    )

    return max(0, min(100, score))


# =========================
# ✈️ BUSCA
# =========================
def buscar_passagens():

    print("🔍 Buscando passagens inteligentes...")
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
                except:
                    continue

                preco = base_precos.get(destino, 400) + (hash(destino + companhia) % 200)

                salvar_preco(ORIGEM, destino, partida, preco, 2.5, companhia)

                media, _ = obter_stats(ORIGEM, destino)
                historico = historico_recente(ORIGEM, destino)

                tendencia, recomendacao, slope, sazonal = prever_preco(historico, partida)

                score = calcular_score(preco, media, dias, slope, sazonal)

                print(f"{destino} | R${preco} | Score {score:.1f}")

                if score >= SCORE_MINIMO:
                    resultados.append({
                        "destino": destino,
                        "preco": preco,
                        "dias": dias,
                        "score": score,
                        "tendencia": tendencia,
                        "recomendacao": recomendacao
                    })

        except Exception as e:
            print("Erro:", e)

    print("VOOS FILTRADOS:", len(resultados))

    return resultados


# =========================
# 📩 ALERTAS
# =========================
def enviar_alertas():

    voos = buscar_passagens()

    if not voos:
        bot.send_message(CHAT_ID, "⚠️ Nenhuma oportunidade hoje.")
        return

    voos.sort(key=lambda x: x["score"], reverse=True)

    msg = "🔥 TOP PROMOÇÕES INTELIGENTES:\n\n"

    enviados = 0

    for voo in voos[:3]:

        try:
            if ja_enviado(ORIGEM, voo["destino"], voo["preco"]):
                continue

            registrar_alerta(ORIGEM, voo["destino"], voo["preco"])
        except:
            pass

        msg += f"""
✈️ {ORIGEM} → {voo['destino']}
💰 R$ {voo['preco']}
📊 Score: {voo['score']:.0f}

🧠 {voo['tendencia']}
📊 {voo['recomendacao']}
"""

        enviados += 1

    if enviados > 0:
        bot.send_message(CHAT_ID, msg)
        print("✅ Alertas enviados")


# =========================
# 🔁 LOOP
# =========================
def main():
    print("🔁 Loop ativo")
    while True:
        enviar_alertas()
        time.sleep(INTERVALO)


# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    bot.send_message(CHAT_ID, "🚀 Bot inteligente ativo (Fase 2)")
    main()
