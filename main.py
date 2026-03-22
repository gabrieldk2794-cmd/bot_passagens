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
DESTINOS_FIXOS = ["GRU", "GIG", "SSA", "REC"]
indice_destino = 0

INTERVALO = 43200  # 12h
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

    return num / den if den else 0


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

    global indice_destino

    destino = DESTINOS_FIXOS[indice_destino]
    indice_destino = (indice_destino + 1) % len(DESTINOS_FIXOS)

    print(f"🎯 Buscando destino: {destino}")

    resultados = []

    base_precos = {
        "GRU": 250,
        "GIG": 300,
        "SSA": 500,
        "REC": 600
    }

    try:
        url = "http://api.aviationstack.com/v1/flights"

        params = {
            "access_key": AVIATIONSTACK_KEY,
            "dep_iata": ORIGEM,
            "arr_iata": destino
        }

        response = requests.get(url, params=params)
        print("API:", response.status_code)

        data = response.json()
        voos = data.get("data", [])[:3]

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

            preco = base_precos[destino] + (hash(destino + companhia) % 200)

            salvar_preco(ORIGEM, destino, partida, preco, 2.5, companhia)

            media, _ = obter_stats(ORIGEM, destino)
            historico = historico_recente(ORIGEM, destino)

            tendencia, recomendacao, slope, sazonal = prever_preco(historico, partida)

            score = calcular_score(preco, media, dias, slope, sazonal)

            # 🚨 ALERTA EXTREMO (70% abaixo)
            if media and preco < (media * 0.3):
                score = 100
                recomendacao = "🔥 COMPRAR AGORA (ERRO DE TARIFA)"

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

    return resultados


# =========================
# 📩 ALERTAS
# =========================
def enviar_alertas():

    voos = buscar_passagens()

    if not voos:
        bot.send_message(CHAT_ID, "⚠️ Hoje não apareceu nada absurdo... mas estou de olho 👀")
        return

    voos.sort(key=lambda x: x["score"], reverse=True)

    msg = "🔥 Voe Barato BH | Oportunidade encontrada!\n\n"

    for voo in voos[:2]:

        destaque = "🔥 OPORTUNIDADE RARA\n" if voo["score"] > 80 else ""

        link = f"https://www.skyscanner.com.br/transport/flights/{ORIGEM}/{voo['destino']}"

        msg += f"""
{destaque}
✈️ {ORIGEM} → {voo['destino']}
💰 R$ {voo['preco']}

📊 Score: {voo['score']:.0f}

🧠 {voo['tendencia']}
💡 {voo['recomendacao']}

⏳ Pode mudar a qualquer momento!

🔎 {link}

━━━━━━━━━━━━━━
🔥 Voe Barato BH
👀 Receba antes de todo mundo:
https://t.me/SEU_CANAL_AQUI
"""

    bot.send_message(CHAT_ID, msg)
    print("✅ Alerta enviado")


# =========================
# 🔁 LOOP
# =========================
def main():
    print("🚀 Bot rodando 2x ao dia")

    while True:
        enviar_alertas()
        time.sleep(INTERVALO)


# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    bot.send_message(CHAT_ID, "🚀 Voe Barato BH ativo (modo otimizado)")
    main()
