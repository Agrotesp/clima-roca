import streamlit as st
import requests
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
        return v
    except:
        return 0.0

# =========================
# PREVISÃO
# =========================
def get_forecast():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=precipitation_sum&timezone=auto"
    r = requests.get(url).json()

    days = r["daily"]["time"]
    rain = [safe_rain(x) for x in r["daily"]["precipitation_sum"]]

    return days, rain

# =========================
# TELEGRAM
# =========================
def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# =========================
# TEXTO MANHÃ
# =========================
def build_morning(days, rain):
    return f"""
📡 RELATÓRIO CLIMA – MANHÃ

📍 Sua roça

🌧️ Situação:
Instabilidade fraca

📊 Previsão:
Hoje: {rain[0]} mm
Amanhã: {rain[1]} mm
{days[2]}: {rain[2]} mm

🌱 Recomendação:
AGUARDAR

⏰ 07:00
"""

# =========================
# TEXTO TARDE
# =========================
def build_afternoon(days, rain):
    return f"""
📡 ALERTA CLIMA – TARDE

🌧️ Atualização:
Radar sem força

📊 Hoje: {rain[0]} mm

🌱 Recomendação:
AGUARDAR

⏰ 13:00
"""

# =========================
# UI
# =========================
st.title("🌦️ Clima da Roça")

days, rain = get_forecast()

st.write("### Previsão")
for d, r in zip(days[:5], rain[:5]):
    st.write(d, "→", r, "mm")

if st.button("📤 Enviar manhã"):
    send(build_morning(days, rain))

if st.button("📤 Enviar tarde"):
    send(build_afternoon(days, rain))
