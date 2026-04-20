import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# =========================
# CONFIG
# =========================
LAT = float(st.secrets["LATITUDE"])
LON = float(st.secrets["LONGITUDE"])
TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]

# =========================
# FUNÇÃO SEGURA DE CHUVA
# =========================
def safe_rain(v):
    try:
        v = float(v)
        if v < 0:
            return 0.0
        return round(v,1)
    except:
        return 0.0

# =========================
# PREVISÃO
# =========================
def get_forecast():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=precipitation_sum,precipitation_probability_max&timezone=auto"
    r = requests.get(url).json()

    days = r["daily"]["time"]
    rain = [safe_rain(x) for x in r["daily"]["precipitation_sum"]]
    prob = r["daily"]["precipitation_probability_max"]

    return days, rain, prob

# =========================
# TELEGRAM
# =========================
def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# =========================
# FORMATAR DIAS
# =========================
def format_day(date_str, i):
    d = datetime.strptime(date_str, "%Y-%m-%d")

    if i == 0:
        return "Hoje"
    if i == 1:
        return "Amanhã"

    nomes = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
    return f"{nomes[d.weekday()]} {d.strftime('%d/%m')}"

# =========================
# TEXTO MANHÃ
# =========================
def build_morning(days, rain, prob):
    texto = "📡 RELATÓRIO CLIMA – MANHÃ\n\n📍 Sua roça\n\n"

    for i in range(5):
        texto += f"{format_day(days[i],i)}: {rain[i]} mm | prob {prob[i]}%\n"

    texto += "\n🌱 Recomendação:\nAGUARDAR\n\n⏰ 07:00"

    return texto

# =========================
# TEXTO TARDE
# =========================
def build_afternoon(days, rain, prob):
    texto = "📡 ALERTA CLIMA – TARDE\n\n📍 Sua roça\n\n"

    texto += f"Hoje: {rain[0]} mm\n"
    texto += f"Amanhã: {rain[1]} mm\n\n"

    texto += "🌱 Recomendação:\nAGUARDAR\n\n⏰ 13:00"

    return texto

# =========================
# UI
# =========================
st.title("🌦️ Clima da Roça")

days, rain, prob = get_forecast()

st.write("### Previsão")

for i in range(5):
    st.write(f"{format_day(days[i],i)} → {rain[i]} mm")

# BOTÕES
if st.button("📤 Enviar manhã"):
    send(build_morning(days, rain, prob))

if st.button("📤 Enviar tarde"):
    send(build_afternoon(days, rain, prob))
