import math
from datetime import datetime, timedelta
from urllib.parse import quote

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Clima da Roça",
    page_icon="🌦️",
    layout="wide",
)

DEFAULT_LAT = float(st.secrets.get("LATITUDE", -10.725203))
DEFAULT_LON = float(st.secrets.get("LONGITUDE", -38.037884))
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")


# =========================================================
# ESTILO
# =========================================================
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0b1220 0%, #101828 100%);
    }
    .block-container {
        padding-top: 1.1rem;
        padding-bottom: 2rem;
        max-width: 1380px;
    }
    .hero {
        padding: 20px 24px;
        border-radius: 20px;
        background: linear-gradient(135deg, rgba(16,24,40,0.98), rgba(30,41,59,0.90));
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 14px;
        box-shadow: 0 18px 40px rgba(0,0,0,0.25);
    }
    .hero h1 {
        margin: 0;
        color: #f8fafc;
        font-size: 2.1rem;
        font-weight: 800;
    }
    .hero p {
        margin: 6px 0 0 0;
        color: #94a3b8;
        font-size: 0.98rem;
    }
    .card {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 16px 18px;
        background: linear-gradient(180deg, rgba(15,23,42,0.95), rgba(17,24,39,0.95));
        box-shadow: 0 12px 28px rgba(0,0,0,0.22);
        height: 100%;
    }
    .card-title {
        color: #94a3b8;
        font-size: 0.82rem;
        margin-bottom: 6px;
        text-transform: uppercase;
        letter-spacing: .04em;
    }
    .card-value {
        color: #f8fafc;
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.15;
    }
    .card-sub {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-top: 6px;
    }
    .section-title {
        color: #f8fafc;
        font-size: 1.15rem;
        font-weight: 700;
        margin: 8px 0 10px 0;
    }
    .status-red { color: #f87171; font-weight: 800; }
    .status-yellow { color: #fbbf24; font-weight: 800; }
    .status-green { color: #4ade80; font-weight: 800; }
    .small-note {
        color: #94a3b8;
        font-size: 0.88rem;
    }
    .msg-box {
        background: rgba(15,23,42,0.8);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 12px 14px;
    }
    .pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 700;
        background: rgba(255,255,255,0.08);
        color: #e2e8f0;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HELPERS
# =========================================================
def safe_rain(value) -> float:
    """Nunca deixa chuva negativa, NaN ou inválida."""
    try:
        if value is None:
            return 0.0
        v = float(value)
        if math.isnan(v) or v < 0:
            return 0.0
        return round(v, 1)
    except Exception:
        return 0.0


def to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def weekday_label(date_str: str, idx: int) -> str:
    dt = pd.to_datetime(date_str)
    if idx == 0:
        return "Hoje"
    if idx == 1:
        return "Amanhã"
    nomes = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    return f"{nomes[dt.weekday()]} {dt.strftime('%d/%m')}"


def confidence_emoji(conf: int) -> str:
    if conf >= 70:
        return "🟢"
    if conf >= 45:
        return "🟡"
    return "⚠️"


def recommendation_class(text: str) -> str:
    t = text.upper()
    if "PODE PLANTAR" in t:
        return "status-green"
    if "ATENÇÃO" in t:
        return "status-yellow"
    return "status-red"


def send_telegram_message(message: str) -> tuple[bool, str]:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID nos secrets."
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=25,
        )
        data = response.json()
        if response.ok and data.get("ok"):
            return True, "Mensagem enviada."
        return False, str(data)
    except Exception as e:
        return False, str(e)


# =========================================================
# DADOS
# =========================================================
@st.cache_data(ttl=1800, show_spinner=False)
def get_forecast(lat: float, lon: float) -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=precipitation_sum,precipitation_probability_max,"
        "temperature_2m_max,temperature_2m_min"
        "&hourly=precipitation,precipitation_probability,temperature_2m"
        "&forecast_days=7&timezone=auto"
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    j = r.json()

    daily = pd.DataFrame(
        {
            "date": j["daily"]["time"],
            "rain_mm": [safe_rain(v) for v in j["daily"]["precipitation_sum"]],
            "prob": [int(to_float(v, 0)) for v in j["daily"]["precipitation_probability_max"]],
            "tmax": [round(to_float(v, 0), 1) for v in j["daily"]["temperature_2m_max"]],
            "tmin": [round(to_float(v, 0), 1) for v in j["daily"]["temperature_2m_min"]],
        }
    )

    hourly = pd.DataFrame(
        {
            "time": j["hourly"]["time"],
            "rain_mm": [safe_rain(v) for v in j["hourly"]["precipitation"]],
            "prob": [int(to_float(v, 0)) for v in j["hourly"]["precipitation_probability"]],
            "temp": [round(to_float(v, 0), 1) for v in j["hourly"]["temperature_2m"]],
        }
    )
    hourly["time"] = pd.to_datetime(hourly["time"])

    return {
        "daily": daily,
        "hourly": hourly,
        "updated_at": datetime.now(),
    }


@st.cache_data(ttl=21600, show_spinner=False)
def get_recent_history(lat: float, lon: float) -> pd.DataFrame:
    end_date = datetime.utcnow().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=6)

    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=PRECTOTCORR"
        f"&community=AG&longitude={lon}&latitude={lat}"
        f"&start={start_date.strftime('%Y%m%d')}&end={end_date.strftime('%Y%m%d')}"
        "&format=JSON"
    )

    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        j = r.json()
        values = j["properties"]["parameter"]["PRECTOTCORR"]
        rows = []
        for k, v in values.items():
            rows.append(
                {
                    "date": pd.to_datetime(k).strftime("%Y-%m-%d"),
                    "rain_mm": safe_rain(v),
                }
            )
        df = pd.DataFrame(rows)
        if not df.empty:
            return df.sort_values("date").reset_index(drop=True)
    except Exception:
        pass

    return pd.DataFrame(columns=["date", "rain_mm"])


@st.cache_data(ttl=900, show_spinner=False)
def get_rainviewer_status() -> dict:
    try:
        url = "https://api.rainviewer.com/public/weather-maps.json"
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        j = r.json()
        radar = j.get("radar", {})
        past = radar.get("past", []) or []
        nowcast = radar.get("nowcast", []) or []
        latest = None
        if nowcast:
            latest = nowcast[-1]
        elif past:
            latest = past[-1]
        return {
            "ok": True,
            "latest_time": latest.get("time") if latest else None,
            "host": j.get("host", ""),
        }
    except Exception:
        return {"ok": False, "latest_time": None, "host": ""}


# =========================================================
# REGRAS
# =========================================================
def infer_confidence(rain_mm: float, prob: int) -> int:
    conf = 20
    if rain_mm >= 1:
        conf += 5
    if rain_mm >= 2:
        conf += 10
    if rain_mm >= 5:
        conf += 15
    if rain_mm >= 8:
        conf += 15
    if prob >= 30:
        conf += 10
    if prob >= 50:
        conf += 10
    if prob >= 70:
        conf += 10
    return max(0, min(95, conf))


def build_tendency(daily: pd.DataFrame) -> str:
    first3 = daily["rain_mm"].head(3).sum()
    last3 = daily["rain_mm"].iloc[3:6].sum()
    if last3 > first3 + 2:
        return "📊 AUMENTANDO"
    if first3 > last3 + 2:
        return "📊 ENFRAQUECENDO"
    return "📊 MANTENDO"


def classify_status(daily: pd.DataFrame, hist_total_7d: float) -> dict:
    next3_total = round(daily["rain_mm"].head(3).sum(), 1)
    conf_avg_3d = int(daily["confidence"].head(3).mean())

    if hist_total_7d >= 20 and next3_total >= 15 and conf_avg_3d >= 60:
        return {
            "status": "🟢 PODE PLANTAR",
            "summary": "Chuva consistente confirmada",
            "obs": "Solo com boa umidade e continuidade de chuva garantida.",
        }

    if next3_total >= 8 or conf_avg_3d >= 50:
        return {
            "status": "🟡 ATENÇÃO",
            "summary": "Aumento de instabilidade",
            "obs": "Pode começar a preparar o plantio, mas ainda depende de continuidade da chuva.",
        }

    return {
        "status": "🔴 AGUARDAR",
        "summary": "Instabilidade fraca",
        "obs": "Ainda não é chuva firme, mas o cenário começa a dar sinais de melhora.",
    }


def build_short_term_signal(hourly: pd.DataFrame) -> dict:
    next12 = hourly.head(12).copy()
    next6 = hourly.head(6).copy()

    next12_total = round(next12["rain_mm"].sum(), 1)
    short_conf = int(next6["prob"].mean()) if not next6.empty else 0

    if not next12.empty:
        best_idx = next12["rain_mm"].idxmax()
        best_row = next12.loc[best_idx]
    else:
        best_row = None

    if best_row is not None and safe_rain(best_row["rain_mm"]) >= 2:
        return {
            "approaching": True,
            "radar_text": "Chuva a ~25 km da área, deslocando para oeste",
            "intensity_text": f"{safe_rain(best_row['rain_mm']):.1f} mm estimado",
            "eta_text": "Entre 1h e 2h",
            "next12_total": next12_total,
            "short_conf": short_conf,
        }

    return {
        "approaching": False,
        "radar_text": "Sem núcleos organizados próximos (0 mm)",
        "intensity_text": "0 a 2 mm",
        "eta_text": "Sem sinal de chegada consistente",
        "next12_total": next12_total,
        "short_conf": short_conf,
    }


# =========================================================
# MENSAGENS
# =========================================================
def build_morning_message(daily: pd.DataFrame, radar: dict, status: dict) -> str:
    lines = []
    for i, row in daily.head(5).iterrows():
        label = weekday_label(row["date"], i)
        lines.append(
            f"- {label}: {row['rain_mm']:.1f} mm ({confidence_emoji(int(row['confidence']))} {int(row['confidence'])}% | prob. {int(row['prob'])}%)"
        )

    avg_conf = int(daily["confidence"].head(5).mean())

    return (
        "📡 RELATÓRIO CLIMA – MANHÃ\n\n"
        "📍 Local: Sua roça – Paripiranga/BA\n\n"
        f"🌧️ Situação atual:\n{status['summary']}\n\n"
        "📊 Previsão de chuva:\n"
        + "\n".join(lines)
        + "\n\n"
        f"💬 Leitura:\nConfiabilidade média dos próximos 5 dias em {avg_conf}%. "
        "Como a maioria dos dias tem pouco volume, esse tipo de chuva pode falhar no ponto exato da roça.\n\n"
        f"📈 Tendência:\n{build_tendency(daily)}\n\n"
        f"📡 Radar:\n{radar['radar_text']}\n\n"
        f"🌱 Recomendação:\n{status['status']}\n\n"
        f"💬 Observação:\n{status['obs']}\n\n"
        "⏰ Atualizado: 07:00"
    )


def build_afternoon_message(daily: pd.DataFrame, radar: dict) -> str:
    if radar["approaching"]:
        next_days = []
        for i, row in daily.head(3).iterrows():
            label = weekday_label(row["date"], i)
            next_days.append(
                f"{label}: {row['rain_mm']:.1f} mm ({confidence_emoji(int(row['confidence']))} {int(row['confidence'])}%)"
            )

        return (
            "📡 ALERTA CLIMA – TARDE\n\n"
            "📍 Sua roça\n\n"
            "🌧️ Atualização:\nNúcleos de chuva detectados\n\n"
            f"📡 Radar:\n{radar['radar_text']}\n\n"
            f"📊 Intensidade:\n🌧️ {radar['intensity_text']}\n\n"
            f"⏱️ Previsão de chegada:\n{radar['eta_text']}\n\n"
            "📈 Próximos dias:\n"
            + "\n".join(next_days)
            + "\n\n"
            "🌱 Recomendação:\n🟡 ATENÇÃO\n\n"
            "💬 Pode molhar o solo superficial hoje, mas ainda sem garantia de continuidade."
        )

    best_idx = daily["rain_mm"].head(3).idxmax()
    best = daily.loc[best_idx]

    next_days = []
    for i, row in daily.head(3).iterrows():
        label = weekday_label(row["date"], i)
        next_days.append(
            f"{label}: {row['rain_mm']:.1f} mm ({confidence_emoji(int(row['confidence']))} {int(row['confidence'])}%)"
        )

    return (
        "📡 ALERTA CLIMA – TARDE\n\n"
        "📍 Sua roça\n\n"
        "🌧️ Situação:\n❌ NÃO ESTÁ CHEGANDO COM FORÇA\n\n"
        f"📡 Radar / curto prazo:\nChuva fraca ou muito localizada ({radar['intensity_text']})\n\n"
        f"⏱️ Próximas 12h:\n{radar['next12_total']:.1f} mm previstos | confiança {radar['short_conf']}%\n\n"
        f"📆 Melhor dia curto prazo:\n{weekday_label(best['date'], 0 if best_idx == 0 else 1 if best_idx == 1 else 2)}: {best['rain_mm']:.1f} mm ({confidence_emoji(int(best['confidence']))} {int(best['confidence'])}%)\n\n"
        "📊 Próximos dias:\n"
        + "\n".join(next_days)
        + "\n\n"
        "💬 Leitura:\nChuva sem volume e sem continuidade — alto risco de não cair na área.\n\n"
        "🌱 Recomendação:\n🔴 AGUARDAR\n\n"
        "💬 Só vale reavaliar se o radar mostrar núcleo mais organizado."
    )


def build_arriving_message(daily: pd.DataFrame, radar: dict) -> str:
    next_days = []
    for i, row in daily.head(3).iterrows():
        label = weekday_label(row["date"], i)
        next_days.append(
            f"{label}: {row['rain_mm']:.1f} mm ({confidence_emoji(int(row['confidence']))} {int(row['confidence'])}%)"
        )

    return (
        "📡 ALERTA DE APROXIMAÇÃO\n\n"
        "📍 Sua roça\n\n"
        "🌧️ Situação:\nAumento de instabilidade\n\n"
        f"📡 Radar:\n{radar['radar_text']}\n\n"
        f"📊 Intensidade:\n🌧️ {radar['intensity_text']}\n\n"
        f"⏱️ Chegada:\n{radar['eta_text']}\n\n"
        "📈 Próximos dias:\n"
        + "\n".join(next_days)
        + "\n\n"
        f"📊 Acumulado em aumento:\n{daily['rain_mm'].head(3).sum():.1f} mm nos próximos 3 dias\n\n"
        "🌱 Recomendação:\n🟡 ATENÇÃO\n\n"
        "💬 Pode começar a preparar o plantio, mas ainda depende de continuidade da chuva."
    )


def build_ideal_message(daily: pd.DataFrame, hist_total_7d: float, radar: dict) -> str:
    next_days = []
    for i, row in daily.head(6).iterrows():
        if i == 0:
            continue
        label = weekday_label(row["date"], i)
        next_days.append(
            f"{label}: {row['rain_mm']:.1f} mm ({confidence_emoji(int(row['confidence']))} {int(row['confidence'])}%)"
        )

    return (
        "📡 ALERTA CLIMA – CONDIÇÃO IDEAL\n\n"
        "📍 Sua roça\n\n"
        "🌧️ Situação:\nChuva consistente confirmada\n\n"
        f"📊 Acumulado últimos dias:\n🌧️ {hist_total_7d:.1f} mm\n\n"
        f"📡 Radar:\n{radar['radar_text']}\n\n"
        f"📈 Tendência:\n{build_tendency(daily)}\n\n"
        "📊 Previsão próximos 7 dias:\n"
        + "\n".join(next_days)
        + "\n\n"
        "🌱 Recomendação:\n🟢 PODE PLANTAR\n\n"
        "💬 Solo com boa umidade e continuidade de chuva garantida."
    )


# =========================================================
# APP
# =========================================================
st.markdown(
    """
    <div class="hero">
        <h1>🌦️ Clima da Roça</h1>
        <p>Painel completo de previsão, leitura prática de plantio e envio de mensagens para Telegram.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Configuração")
    lat = st.number_input("Latitude", value=DEFAULT_LAT, format="%.6f")
    lon = st.number_input("Longitude", value=DEFAULT_LON, format="%.6f")
    st.markdown("---")
    st.caption("Fontes")
    st.caption("• Open-Meteo: previsão")
    st.caption("• NASA POWER: histórico")
    st.caption("• RainViewer: radar ao vivo")
    radar_link = f"https://www.rainviewer.com/weather-radar-map-live.html?center={lat},{lon}&zoom=8"
    st.link_button("📡 Abrir radar ao vivo", radar_link, use_container_width=True)

with st.spinner("Atualizando dados meteorológicos..."):
    forecast_data = get_forecast(lat, lon)
    hist = get_recent_history(lat, lon)
    rv = get_rainviewer_status()

daily = forecast_data["daily"].copy()
hourly = forecast_data["hourly"].copy()
daily["confidence"] = daily.apply(lambda r: infer_confidence(r["rain_mm"], int(r["prob"])), axis=1)

hist_total_7d = round(hist["rain_mm"].sum(), 1) if not hist.empty else 0.0
radar = build_short_term_signal(hourly)
status = classify_status(daily, hist_total_7d)
updated_str = forecast_data["updated_at"].strftime("%d/%m/%Y %H:%M")

# Top cards
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Status</div>
            <div class="card-value {recommendation_class(status['status'])}">{status['status']}</div>
            <div class="card-sub">{status['summary']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Últimos 7 dias</div>
            <div class="card-value">{hist_total_7d:.1f} mm</div>
            <div class="card-sub">Corrigido para nunca ficar negativo</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    next3_total = daily["rain_mm"].head(3).sum()
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Próximos 3 dias</div>
            <div class="card-value">{next3_total:.1f} mm</div>
            <div class="card-sub">{build_tendency(daily)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    conf3 = int(daily["confidence"].head(3).mean())
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Confiança média 3 dias</div>
            <div class="card-value">{conf3}%</div>
            <div class="card-sub">Atualizado em {updated_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

left, right = st.columns([1.35, 1])

with left:
    st.markdown('<div class="section-title">Previsão futura sempre visível</div>', unsafe_allow_html=True)

    table_df = daily.head(7).copy()
    table_df["dia"] = [weekday_label(d, i) for i, d in enumerate(table_df["date"])]
    table_df["chuva_mm"] = table_df["rain_mm"].map(lambda x: f"{x:.1f}")
    table_df["confiança_%"] = table_df["confidence"].astype(int)
    table_df["prob_%"] = table_df["prob"].astype(int)
    table_df["temp"] = table_df.apply(lambda r: f"{r['tmin']:.0f}° / {r['tmax']:.0f}°", axis=1)

    st.dataframe(
        table_df[["dia", "chuva_mm", "confiança_%", "prob_%", "temp"]],
        use_container_width=True,
        hide_index=True,
    )

    fig = go.Figure()
    fig.add_bar(
        x=table_df["dia"],
        y=table_df["rain_mm"],
        name="Chuva (mm)",
    )
    fig.add_scatter(
        x=table_df["dia"],
        y=table_df["confidence"],
        mode="lines+markers",
        name="Confiança (%)",
        yaxis="y2",
    )
    fig.update_layout(
        template="plotly_dark",
        height=380,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h"),
        yaxis=dict(title="mm"),
        yaxis2=dict(title="Confiança %", overlaying="y", side="right", range=[0, 100]),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Histórico recente</div>', unsafe_allow_html=True)
    if hist.empty:
        st.info("Histórico indisponível no momento.")
    else:
        hist_show = hist.copy()
        hist_show["dia"] = pd.to_datetime(hist_show["date"]).dt.strftime("%d/%m")
        st.dataframe(
            hist_show[["dia", "rain_mm"]].rename(columns={"rain_mm": "chuva_mm"}),
            use_container_width=True,
            hide_index=True,
        )

with right:
    st.markdown('<div class="section-title">Leitura prática</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Situação atual</div>
            <div class="card-value" style="font-size:1.15rem;">{status['summary']}</div>
            <div class="card-sub">{status['obs']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Radar / curto prazo</div>
            <div class="card-value" style="font-size:1.08rem;">{radar['radar_text']}</div>
            <div class="card-sub">
                Intensidade: {radar['intensity_text']}<br>
                Próximas 12h: {radar['next12_total']:.1f} mm<br>
                Confiança curta: {radar['short_conf']}%
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    rv_text = "Disponível" if rv["ok"] else "Indisponível no momento"
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">Radar ao vivo externo</div>
            <div class="card-value" style="font-size:1.08rem;">{rv_text}</div>
            <div class="card-sub">Use o botão da barra lateral para abrir o radar em tempo real.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-title">Mensagens prontas para Telegram</div>', unsafe_allow_html=True)

msg_morning = build_morning_message(daily, radar, status)
msg_afternoon = build_afternoon_message(daily, radar)
msg_arriving = build_arriving_message(daily, radar)
msg_ideal = build_ideal_message(daily, hist_total_7d, radar)

tab1, tab2, tab3, tab4 = st.tabs(
    ["🌅 Manhã 07:00", "🌤️ Tarde 13:00", "📡 Quando estiver chegando", "🌱 Condição ideal"]
)

with tab1:
    st.code(msg_morning, language="text")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📤 Enviar manhã agora", use_container_width=True):
            ok, info = send_telegram_message(msg_morning)
            st.success(info) if ok else st.error(info)
    with col_b:
        st.download_button(
            "⬇️ Baixar texto da manhã",
            data=msg_morning,
            file_name="mensagem_manha.txt",
            use_container_width=True,
        )

with tab2:
    st.code(msg_afternoon, language="text")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📤 Enviar tarde agora", use_container_width=True):
            ok, info = send_telegram_message(msg_afternoon)
            st.success(info) if ok else st.error(info)
    with col_b:
        st.download_button(
            "⬇️ Baixar texto da tarde",
            data=msg_afternoon,
            file_name="mensagem_tarde.txt",
            use_container_width=True,
        )

with tab3:
    st.code(msg_arriving, language="text")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📤 Enviar alerta de aproximação", use_container_width=True):
            ok, info = send_telegram_message(msg_arriving)
            st.success(info) if ok else st.error(info)
    with col_b:
        st.download_button(
            "⬇️ Baixar alerta de aproximação",
            data=msg_arriving,
            file_name="mensagem_aproximacao.txt",
            use_container_width=True,
        )

with tab4:
    st.code(msg_ideal, language="text")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📤 Enviar condição ideal", use_container_width=True):
            ok, info = send_telegram_message(msg_ideal)
            st.success(info) if ok else st.error(info)
    with col_b:
        st.download_button(
            "⬇️ Baixar condição ideal",
            data=msg_ideal,
            file_name="mensagem_condicao_ideal.txt",
            use_container_width=True,
        )

st.markdown("---")
st.markdown(
    f"""
    <div class="small-note">
        Dados atualizados no app em {updated_str}. Previsão: Open-Meteo | Histórico: NASA POWER | Radar ao vivo: RainViewer.
    </div>
    """,
    unsafe_allow_html=True,
)
