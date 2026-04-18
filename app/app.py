import html
import json
import math
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import altair as alt
import folium
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from folium.features import DivIcon
from streamlit_folium import st_folium

st.set_page_config(page_title="Clima da Roça Pro", page_icon="🌦️", layout="wide")

DEFAULT_LAT = -10.725203
DEFAULT_LON = -38.037884
TZ = "America/Bahia"

CSS = """
<style>
:root {
  --green: #1f7a3b;
  --green-soft: #e8f7ed;
  --amber: #b9770e;
  --amber-soft: #fff6e5;
  --red: #b42318;
  --red-soft: #fff0ef;
  --blue: #0f4c81;
  --ink: #0f172a;
  --muted: #475569;
  --card: rgba(255,255,255,0.90);
  --line: rgba(15, 23, 42, 0.08);
}
html, body, [data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg, #f8fafc 0%, #f0fdf4 55%, #f8fafc 100%);
}
.block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 1450px;}
.hero {
  background: linear-gradient(135deg, #052e16 0%, #14532d 45%, #0f766e 100%);
  color: white; padding: 1.35rem 1.4rem; border-radius: 24px;
  box-shadow: 0 22px 45px rgba(2, 6, 23, 0.18); margin-bottom: 0.95rem;
}
.hero-grid {display:grid; grid-template-columns: 1.4fr 1fr; gap: 1rem; align-items: stretch;}
.hero h1 {margin: 0; font-size: 2.3rem; line-height: 1.05;}
.hero p {margin: 0.45rem 0 0 0; opacity: 0.94; font-size: 1rem;}
.small-pill {
  display: inline-block; background: rgba(255,255,255,0.13); border: 1px solid rgba(255,255,255,0.18);
  padding: 0.35rem 0.8rem; border-radius: 999px; margin-right: 0.45rem; margin-top: 0.55rem; font-size: 0.88rem;
}
.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 20px; padding: 1rem 1rem 0.95rem;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06); height: 100%;
}
.title-row {display:flex; align-items:flex-start; justify-content:space-between; gap:0.7rem; margin-bottom:0.65rem;}
.section-title {font-size: 1.06rem; font-weight: 800; color: var(--ink); margin: 0;}
.section-sub {color: var(--muted); font-size: 0.92rem; margin: 0.22rem 0 0 0;}
.metric-card {
  border-radius: 18px; padding: 1rem; color: white; min-height: 118px; box-shadow: 0 12px 26px rgba(15, 23, 42, 0.14);
}
.metric-card .label {font-size: 0.92rem; opacity: 0.9;}
.metric-card .value {font-size: 1.8rem; font-weight: 800; line-height: 1.15; margin-top: 0.22rem;}
.metric-card .sub {font-size: 0.9rem; opacity: 0.95; margin-top: 0.38rem;}
.metric-green {background: linear-gradient(135deg, #16a34a, #166534);} 
.metric-blue {background: linear-gradient(135deg, #0284c7, #075985);} 
.metric-purple {background: linear-gradient(135deg, #7c3aed, #6d28d9);} 
.metric-slate {background: linear-gradient(135deg, #334155, #0f172a);} 
.status-box {border-radius: 22px; padding: 1.15rem 1.2rem; color: white; margin-bottom: 0.8rem; box-shadow: 0 14px 30px rgba(15, 23, 42, 0.14);} 
.status-good {background: linear-gradient(135deg, #15803d, #166534);} 
.status-warn {background: linear-gradient(135deg, #d97706, #b45309);} 
.status-bad {background: linear-gradient(135deg, #dc2626, #b91c1c);} 
.status-box h2 {margin: 0; font-size: 1.85rem;} 
.status-box p {margin: 0.45rem 0 0 0;} 
.status-chip {display:inline-block; background: rgba(255,255,255,0.16); border:1px solid rgba(255,255,255,0.16); padding:0.3rem 0.7rem; border-radius:999px; margin-top:0.7rem; font-size:0.86rem;} 
.info-badge {display:inline-block; background:#eef2ff; color:#3730a3; border:1px solid #c7d2fe; padding:0.3rem 0.65rem; border-radius:999px; font-size:0.84rem; font-weight:700;} 
.kpi-grid {display:grid; grid-template-columns:repeat(4, 1fr); gap:0.8rem; margin-bottom:0.85rem;} 
.days-wrap {display:grid; grid-template-columns:repeat(7, 1fr); gap:0.65rem;} 
.day-card {background:white; border:1px solid rgba(15,23,42,.08); border-radius:18px; padding:.9rem .8rem; box-shadow: 0 6px 18px rgba(15,23,42,.05);} 
.day-card .d1 {font-size:.88rem; color:#475569; font-weight:700;} 
.day-card .d2 {font-size:1.5rem; color:#0f172a; font-weight:800; line-height:1.1; margin-top:.15rem;} 
.day-card .d3 {font-size:.85rem; color:#475569; margin-top:.2rem;} 
.day-card .conf {margin-top:.55rem; display:inline-block; padding:.22rem .55rem; border-radius:999px; font-size:.8rem; font-weight:700;} 
.conf-low {background: var(--red-soft); color: var(--red); border:1px solid #f8b4b4;} 
.conf-mid {background: var(--amber-soft); color: var(--amber); border:1px solid #f6d48e;} 
.conf-high {background: var(--green-soft); color: var(--green); border:1px solid #b7e0c2;} 
.good-window {background: linear-gradient(135deg, #0f4c81, #0b7285); color:white; border-radius:20px; padding:1rem 1.05rem; box-shadow: 0 14px 30px rgba(15,23,42,.14);} 
.good-window h3 {margin:0; font-size:1.25rem;} 
.good-window ul {margin:.65rem 0 0 1.1rem;} 
.good-window li {margin:.18rem 0;} 
.msg-box {background:#0f172a; color:#e2e8f0; border-radius:16px; padding:.85rem; font-family:ui-monospace, SFMono-Regular, Menlo, monospace; white-space:pre-wrap; font-size:.9rem; min-height:180px;} 
.copy-wrap {margin-top: .55rem;} 
.caption-note {color: var(--muted); font-size: 0.9rem;} 
@media (max-width: 1150px) {
  .days-wrap {grid-template-columns:repeat(3, 1fr);} 
}
@media (max-width: 900px) {
  .hero-grid, .kpi-grid, .days-wrap {grid-template-columns:1fr;} 
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


def fetch_json(url, params=None, timeout=35):
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=1800)
def get_forecast(lat: float, lon: float):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": TZ,
        "forecast_days": 16,
        "hourly": ",".join([
            "precipitation", "precipitation_probability", "temperature_2m",
            "relative_humidity_2m", "cloud_cover", "wind_speed_10m",
            "wind_direction_10m", "soil_temperature_0cm", "soil_moisture_0_to_1cm",
        ]),
        "daily": ",".join([
            "precipitation_sum", "precipitation_hours", "precipitation_probability_max",
            "temperature_2m_max", "temperature_2m_min", "wind_speed_10m_max",
        ]),
        "current": ",".join([
            "temperature_2m", "relative_humidity_2m", "cloud_cover",
            "precipitation", "wind_speed_10m", "wind_direction_10m",
        ]),
    }
    return fetch_json(url, params)


@st.cache_data(ttl=21600)
def get_nasa_power(lat: float, lon: float):
    end = datetime.utcnow().date() - timedelta(days=1)
    start = end - timedelta(days=119)
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "PRECTOTCORR,T2M_MAX,T2M_MIN,RH2M,WS2M",
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    return fetch_json(url, params)


@st.cache_data(ttl=900)
def get_rainviewer_index():
    return fetch_json("https://api.rainviewer.com/public/weather-maps.json")


def daily_dataframe(forecast_json):
    df = pd.DataFrame(forecast_json["daily"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def hourly_dataframe(forecast_json):
    df = pd.DataFrame(forecast_json["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def current_dict(forecast_json):
    return forecast_json.get("current", {})


def power_dataframe(power_json):
    params = power_json["properties"]["parameter"]
    dates = list(params["PRECTOTCORR"].keys())
    df = pd.DataFrame({
        "date": pd.to_datetime(dates, format="%Y%m%d"),
        "chuva_mm": list(params["PRECTOTCORR"].values()),
        "temp_max": list(params["T2M_MAX"].values()),
        "temp_min": list(params["T2M_MIN"].values()),
        "umidade": list(params["RH2M"].values()),
        "vento": list(params["WS2M"].values()),
    })
    for col in ["chuva_mm", "temp_max", "temp_min", "umidade", "vento"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def parse_kml(file_bytes: bytes):
    root = ET.fromstring(file_bytes)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    points = []
    for coord in root.findall(".//kml:Point/kml:coordinates", ns):
        text = (coord.text or "").strip()
        if not text:
            continue
        lon, lat, *_ = [float(x) for x in text.split(",") if x != ""]
        points.append([lon, lat])
    return points


def monotonic_hull(points):
    points = sorted(set((float(lon), float(lat)) for lon, lat in points))
    if len(points) <= 1:
        return points

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def polygon_area_ha(coords):
    if len(coords) < 3:
        return 0.0
    mean_lat = sum(lat for lon, lat in coords) / len(coords)
    xy = []
    for lon, lat in coords:
        x = lon * 111320 * math.cos(math.radians(mean_lat))
        y = lat * 110540
        xy.append((x, y))
    area = 0.0
    for i in range(len(xy)):
        x1, y1 = xy[i]
        x2, y2 = xy[(i + 1) % len(xy)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2 / 10000


def load_default_area():
    path = os.path.join("areas", "minha_roca.geojson")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def area_coords(geojson):
    return geojson["features"][0]["geometry"]["coordinates"][0]


def area_center_from_geojson(geojson):
    coords = area_coords(geojson)[:-1]
    lons = [p[0] for p in coords]
    lats = [p[1] for p in coords]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def direction_text(deg):
    if deg is None or pd.isna(deg):
        return "sem leitura"
    dirs = ["N", "NE", "L", "SE", "S", "SO", "O", "NO"]
    idx = int((float(deg) + 22.5) // 45) % 8
    return dirs[idx]


def confidence_percent(mm, prob, precip_hours, day_index, neighborhood_mm):
    prob = 0 if pd.isna(prob) else float(prob)
    mm = 0 if pd.isna(mm) else float(mm)
    precip_hours = 0 if pd.isna(precip_hours) else float(precip_hours)
    neighborhood_mm = max(0.0, float(neighborhood_mm))
    score = 22
    score += min(prob * 0.45, 34)
    score += min(mm * 2.2, 22)
    score += min(precip_hours * 2.5, 12)
    score += min(neighborhood_mm * 0.8, 10)
    score -= day_index * 4.5
    if mm < 2:
        score -= 10
    elif mm < 5:
        score -= 4
    score = max(22, min(92, round(score)))
    return int(score)


def confidence_label(score):
    if score >= 72:
        return "Alta", "conf-high"
    if score >= 52:
        return "Média", "conf-mid"
    return "Baixa", "conf-low"


def enrich_daily(daily_df):
    df = daily_df.copy().reset_index(drop=True)
    confs = []
    for i in range(len(df)):
        neigh = df.iloc[max(0, i - 1): min(len(df), i + 2)]["precipitation_sum"].fillna(0).sum() - float(df.loc[i, "precipitation_sum"] or 0)
        confs.append(confidence_percent(df.loc[i, "precipitation_sum"], df.loc[i, "precipitation_probability_max"], df.loc[i, "precipitation_hours"], i, neigh))
    df["confidence_pct"] = confs
    df[["confidence_label", "confidence_class"]] = df["confidence_pct"].apply(lambda x: pd.Series(confidence_label(x)))
    df["dia_txt"] = df["time"].dt.strftime("%d/%m")
    df["weekday"] = df["time"].dt.strftime("%a").str.replace("Mon", "Seg").str.replace("Tue", "Ter").str.replace("Wed", "Qua").str.replace("Thu", "Qui").str.replace("Fri", "Sex").str.replace("Sat", "Sáb").str.replace("Sun", "Dom")
    return df


def planting_signal(daily_df):
    next3 = daily_df.head(3)
    next5 = daily_df.head(5)
    total3 = float(next3["precipitation_sum"].fillna(0).sum())
    total5 = float(next5["precipitation_sum"].fillna(0).sum())
    strong_days = int((next5["precipitation_sum"].fillna(0) >= 10).sum())
    probable_days = int((next5["precipitation_probability_max"].fillna(0) >= 70).sum())
    avg_conf = float(next3["confidence_pct"].mean())
    score = 0
    score += 2 if total3 >= 20 else 1 if total3 >= 10 else 0
    score += 2 if total5 >= 30 else 1 if total5 >= 18 else 0
    score += 2 if strong_days >= 2 else 1 if strong_days == 1 else 0
    score += 1 if probable_days >= 3 else 0
    score += 1 if avg_conf >= 65 else 0
    if score >= 6:
        return "SINAL BOM", "status-good", "Há chuva mais útil desenhada. Se o solo também confirmar, já começa a aparecer janela de plantio.", score
    if score >= 4:
        return "ATENÇÃO", "status-warn", "O cenário melhorou, mas ainda mistura dia bom com dia duvidoso. Vale acompanhar mais 24 a 48 horas.", score
    return "AGUARDAR", "status-bad", "A chuva segue fraca, espaçada ou pouco confiável. Eu não teria confiança para plantar agora.", score


def arrival_signal(hourly_df, daily_df):
    next12 = hourly_df.head(12)
    next24 = hourly_df.head(24)
    rain12 = float(next12["precipitation"].fillna(0).sum())
    rain24 = float(next24["precipitation"].fillna(0).sum())
    prob12 = float(next12["precipitation_probability"].fillna(0).max())
    cloud12 = float(next12["cloud_cover"].fillna(0).mean())
    if rain12 >= 8 or (rain24 >= 12 and prob12 >= 80):
        return "SIM, TEM CARA DE ESTAR CHEGANDO", "Há sinal horário mais consistente nas próximas horas. Vale ficar de olho no céu e no solo."
    if rain24 >= 4 and prob12 >= 60 and cloud12 >= 65:
        return "PODE CHEGAR, MAS AINDA É DUVIDOSO", "Existe chance real de pancada útil, mas ainda sem cara de chuva firme generalizada."
    best_day = daily_df.head(5).iloc[daily_df.head(5)["precipitation_sum"].fillna(0).values.argmax()]
    return "NÃO ESTÁ CHEGANDO COM FORÇA", f"O desenho ainda é de chuva fraca ou muito localizada. O melhor dia no curto prazo é {best_day['time'].date()} com {best_day['precipitation_sum']:.1f} mm."


def confidence_note(daily_df):
    weak = int((daily_df.head(7)["precipitation_sum"].fillna(0) < 3).sum())
    avg_conf = float(daily_df.head(5)["confidence_pct"].mean())
    if weak >= 5:
        return f"Confiabilidade média dos próximos 5 dias em {avg_conf:.0f}%. Como a maioria dos dias tem pouco volume, esse tipo de chuva pode falhar no ponto exato da roça."
    return f"Confiabilidade média dos próximos 5 dias em {avg_conf:.0f}%. Ainda vale confirmar com radar e chuva observada na propriedade."


def true_green_window(daily_df, power_df):
    obs7 = float(power_df.tail(7)["chuva_mm"].fillna(0).sum()) if not power_df.empty else 0.0
    fc3 = float(daily_df.head(3)["precipitation_sum"].fillna(0).sum())
    strong5 = int((daily_df.head(5)["precipitation_sum"].fillna(0) >= 8).sum())
    avg_conf = float(daily_df.head(3)["confidence_pct"].mean())
    criteria = [
        (obs7 >= 10, f"Últimos 7 dias observados: {obs7:.1f} mm (meta: ≥10 mm)"),
        (fc3 >= 20, f"Próximos 3 dias previstos: {fc3:.1f} mm (meta: ≥20 mm)"),
        (strong5 >= 2, f"Dias fortes nos próximos 5 dias: {strong5} (meta: ≥2 dias com ≥8 mm)"),
        (avg_conf >= 60, f"Confiabilidade média 3 dias: {avg_conf:.0f}% (meta: ≥60%)"),
    ]
    met = sum(1 for ok, _ in criteria if ok)
    if met >= 4:
        title = "AGORA ESTÁ COM CARA DE CHUVA FIRME"
        desc = "Os critérios principais de umidade e continuidade estão batendo juntos. Se a sua área também estiver respondendo no solo, já é uma janela bem mais séria."
        cls = "status-good"
    elif met >= 2:
        title = "ESTÁ MELHORANDO, MAS AINDA NÃO FIRMOu"
        desc = "Alguns sinais apareceram, mas ainda faltam peças para chamar de chuva firme de safra."
        cls = "status-warn"
    else:
        title = "AINDA NÃO É O BOM DE VERDADE"
        desc = "O quadro ainda não junta volume, sequência e confiança suficientes para plantar com segurança." 
        cls = "status-bad"
    return title, desc, cls, criteria, met


def future_summary(daily_df, days=7):
    rows = []
    for _, r in daily_df.head(days).iterrows():
        rows.append({
            "date": r["time"].strftime("%d/%m"),
            "weekday": r["weekday"],
            "mm": float(r["precipitation_sum"] or 0),
            "prob": float(r["precipitation_probability_max"] or 0),
            "conf": int(r["confidence_pct"]),
            "conf_label": r["confidence_label"],
            "conf_class": r["confidence_class"],
            "tmax": float(r["temperature_2m_max"] or 0),
            "tmin": float(r["temperature_2m_min"] or 0),
        })
    return rows


def day_line(row):
    return f"{row['weekday']} {row['date']}: {row['mm']:.1f} mm | confiança {row['conf']}% | prob. {row['prob']:.0f}%"


def generate_morning_message(daily_df, status_label, arrival_label, confidence_msg):
    top = future_summary(daily_df, days=4)
    lines = [
        "📡 RELATÓRIO CLIMA – MANHÃ",
        "",
        "📍 Local: Sua roça – Paripiranga/BA",
        "",
        f"🌱 Semáforo: {status_label}",
        f"🌧️ Chegada da chuva: {arrival_label}",
        "",
        "📊 Próximos dias:",
    ]
    lines.extend([f"- {day_line(r)}" for r in top])
    lines.extend([
        "",
        f"💬 Leitura: {confidence_msg}",
        "⏰ Atualizado agora",
    ])
    return "\n".join(lines)


def generate_afternoon_message(hourly_df, daily_df, arrival_label, arrival_msg):
    next12 = hourly_df.head(12)
    rain12 = float(next12["precipitation"].fillna(0).sum())
    prob12 = float(next12["precipitation_probability"].fillna(0).max())
    best = daily_df.head(3).iloc[daily_df.head(3)["precipitation_sum"].fillna(0).values.argmax()]
    lines = [
        "📡 ALERTA CLIMA – TARDE",
        "",
        f"🌧️ Situação: {arrival_label}",
        f"📡 Radar/curto prazo: {arrival_msg}",
        f"⏱️ Próximas 12h: {rain12:.1f} mm previstos | confiança curta {prob12:.0f}%",
        f"📆 Melhor dia curto prazo: {best['time'].strftime('%d/%m')} com {best['precipitation_sum']:.1f} mm e confiança {best['confidence_pct']:.0f}%",
        "",
        "💬 Se o radar mudar e aparecer núcleo organizado, vale revisar o campo de novo.",
    ]
    return "\n".join(lines)


def radar_tile_url(index_json, frame_index=-1, color=4, smooth=1, snow=1):
    radar_past = index_json.get("radar", {}).get("past", [])
    if not radar_past:
        return None, None
    frame = radar_past[frame_index]
    host = index_json.get("host", "https://tilecache.rainviewer.com")
    path = frame.get("path")
    ts = frame.get("time")
    url = f"{host}{path}/256/{{z}}/{{x}}/{{y}}/{color}/{smooth}_{snow}.png"
    return url, ts


def frames_table(index_json):
    rows = []
    for i, frame in enumerate(index_json.get("radar", {}).get("past", [])):
        rows.append({"frame": i, "utc": datetime.fromtimestamp(frame["time"], tz=timezone.utc)})
    return pd.DataFrame(rows)


def add_area_to_map(m, geojson, lat, lon, show_points=True):
    feature = geojson["features"][0]
    coords = feature["geometry"]["coordinates"][0]
    folium.GeoJson(
        geojson,
        style_function=lambda _: {"color": "#22c55e", "weight": 3, "fillColor": "#22c55e", "fillOpacity": 0.16},
        tooltip=feature.get("properties", {}).get("name", "Área da roça"),
    ).add_to(m)
    if show_points:
        for idx, (lonp, latp) in enumerate(coords[:-1], start=1):
            folium.CircleMarker(location=[latp, lonp], radius=4, color="#ef4444", fill=True, fill_opacity=0.95, tooltip=f"Ponto {idx}").add_to(m)
            folium.map.Marker([latp, lonp], icon=DivIcon(html=f'<div style="font-size: 10pt; color: #111827; font-weight: 700;">{idx}</div>')).add_to(m)
    folium.Marker([lat, lon], tooltip="Ponto usado na consulta", icon=folium.Icon(color="blue", icon="cloud")).add_to(m)


def make_map(geojson, lat, lon, radar_url=None, radar_label=None, show_satellite=True, show_points=True):
    m = folium.Map(location=[lat, lon], zoom_start=15, control_scale=True, tiles=None)
    folium.TileLayer("OpenStreetMap", name="Mapa").add_to(m)
    if show_satellite:
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery", name="Satélite", overlay=False, control=True,
        ).add_to(m)
    add_area_to_map(m, geojson, lat, lon, show_points=show_points)
    if radar_url:
        folium.raster_layers.TileLayer(
            tiles=radar_url, attr="RainViewer", name=f"Radar {radar_label or ''}".strip(), overlay=True, control=True, opacity=0.58,
        ).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m


def copy_box(text, key, label="Copiar mensagem"):
    safe_text = html.escape(text)
    components.html(
        f"""
        <div class="copy-wrap">
          <textarea id="txt-{key}" style="width:100%;height:190px;border-radius:14px;padding:10px;background:#0f172a;color:#e2e8f0;border:none;font-family:ui-monospace,monospace;font-size:13px;">{safe_text}</textarea>
          <button onclick="navigator.clipboard.writeText(document.getElementById('txt-{key}').value); this.innerText='Copiado';"
                  style="margin-top:8px;background:#14532d;color:white;border:none;border-radius:10px;padding:10px 14px;font-weight:700;cursor:pointer;">{label}</button>
        </div>
        """,
        height=265,
    )


def get_secret(name, default=""):
    try:
        return st.secrets[name]
    except Exception:
        return default


def telegram_api_url(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def telegram_get_updates(token: str):
    return fetch_json(telegram_api_url(token, "getUpdates"))


def telegram_chat_candidates(updates_json):
    results = []
    seen = set()
    for upd in updates_json.get("result", []):
        msg = upd.get("message") or upd.get("edited_message") or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            continue
        key = (chat_id, chat.get("type"))
        if key in seen:
            continue
        seen.add(key)
        display = chat.get("title") or " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")])) or chat.get("username") or str(chat_id)
        results.append({
            "chat_id": str(chat_id),
            "nome": display,
            "tipo": chat.get("type", "desconhecido"),
        })
    return results


def telegram_send_message(token: str, chat_id: str, text: str):
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(telegram_api_url(token, "sendMessage"), json=payload, timeout=35)
    response.raise_for_status()
    return response.json()


st.markdown(
    """
<div class="hero">
  <div class="hero-grid">
    <div>
      <h1>Clima da Roça Pro</h1>
      <p>Painel de decisão para acompanhar chuva, radar, previsão futura sempre visível e leitura automática para plantio.</p>
      <span class="small-pill">Previsão futura sempre à vista</span>
      <span class="small-pill">Radar sobre satélite</span>
      <span class="small-pill">Mensagens automáticas</span>
    </div>
    <div>
      <div class="card" style="background: rgba(255,255,255,0.10); color: white; border-color: rgba(255,255,255,0.12);">
        <div style="font-size:0.95rem; opacity:0.9;">Foco da versão</div>
        <div style="font-size:1.45rem; font-weight:800; margin-top:0.35rem;">Quando estiver bom de verdade</div>
        <div style="margin-top:0.5rem; opacity:0.95;">O app destaca a janela realmente mais séria, mostra os mm por dia e estima a confiabilidade da previsão em porcentagem.</div>
      </div>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Configuração")
    default_area = load_default_area()
    if default_area:
        default_lat, default_lon = area_center_from_geojson(default_area)
    else:
        default_lat, default_lon = DEFAULT_LAT, DEFAULT_LON
    lat = st.number_input("Latitude", value=float(default_lat), format="%.6f")
    lon = st.number_input("Longitude", value=float(default_lon), format="%.6f")
    st.caption("O app consulta previsão para o centro da área.")

    uploaded = st.file_uploader("Trocar área da roça (KML/GeoJSON)", type=["kml", "geojson", "json"])
    area_geojson = default_area
    area_msg = "Usando a área padrão salva no projeto."

    if uploaded is not None:
        if uploaded.name.lower().endswith(".kml"):
            points = parse_kml(uploaded.getvalue())
            hull = monotonic_hull(points)
            poly = hull + [hull[0]] if hull else []
            area_geojson = {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {
                        "name": uploaded.name,
                        "source": "upload KML",
                        "approx_area_ha": round(polygon_area_ha(hull), 2),
                        "num_points": len(points),
                    },
                    "geometry": {"type": "Polygon", "coordinates": [poly]},
                }],
            }
            area_msg = f"KML lido com {len(points)} marcadores; contorno gerado automaticamente."
        else:
            area_geojson = json.loads(uploaded.getvalue().decode("utf-8"))
            area_msg = "GeoJSON carregado com sucesso."

    show_satellite = st.toggle("Usar base satélite", value=True)
    show_points = st.toggle("Mostrar pontos da área", value=True)
    st.info(area_msg)

if area_geojson is None:
    st.error("Não encontrei uma área padrão. Envie um KML ou GeoJSON.")
    st.stop()

try:
    forecast = get_forecast(lat, lon)
    power = get_nasa_power(lat, lon)
    rainviewer = get_rainviewer_index()
except Exception as e:
    st.error(f"Falha ao consultar dados externos: {e}")
    st.stop()

daily_df = enrich_daily(daily_dataframe(forecast))
hourly_df = hourly_dataframe(forecast)
current = current_dict(forecast)
power_df = power_dataframe(power)
area_properties = area_geojson["features"][0].get("properties", {})
area_ha = area_properties.get("approx_area_ha")
if area_ha is None:
    coords = area_coords(area_geojson)[:-1]
    area_ha = round(polygon_area_ha(coords), 2)

status_label, status_class, status_msg, status_score = planting_signal(daily_df)
arrival_label, arrival_msg = arrival_signal(hourly_df, daily_df)
confidence_msg = confidence_note(daily_df)
good_title, good_desc, good_class, good_criteria, good_met = true_green_window(daily_df, power_df)
future_cards = future_summary(daily_df, days=7)
morning_msg = generate_morning_message(daily_df, status_label, arrival_label, confidence_msg)
afternoon_msg = generate_afternoon_message(hourly_df, daily_df, arrival_label, arrival_msg)

frames_df = frames_table(rainviewer)
radar_url = None
radar_label = None
if not frames_df.empty:
    default_frame = len(frames_df) - 1
    frame_choice = st.slider("Frame do radar", min_value=0, max_value=default_frame, value=default_frame)
    radar_url, radar_ts = radar_tile_url(rainviewer, frame_index=frame_choice)
    if radar_ts:
        radar_label = datetime.fromtimestamp(radar_ts, tz=timezone.utc).strftime("%d/%m %H:%M UTC")

col_a, col_b = st.columns([1.15, 0.85])
with col_a:
    st.markdown(f'<div class="status-box {status_class}"><h2>{status_label}</h2><p>{status_msg}</p><span class="status-chip">Chegada da chuva: {arrival_label}</span> <span class="status-chip">Score agrícola: {status_score}/8</span></div>', unsafe_allow_html=True)
with col_b:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Resumo do dia")
    st.markdown(f"**Chegada da chuva:** {arrival_label}")
    st.markdown(f"**Confiança geral:** {confidence_msg}")
    st.markdown(f"**Área da roça:** {area_ha:.2f} ha")
    st.markdown(f"**Vento agora:** {current.get('wind_speed_10m', 0):.0f} km/h ({direction_text(current.get('wind_direction_10m'))})")
    st.markdown(f"**Temperatura agora:** {current.get('temperature_2m', 0):.1f}°C")
    st.markdown('</div>', unsafe_allow_html=True)

kpi_cols = st.columns(4)
with kpi_cols[0]:
    st.markdown(f'<div class="metric-card metric-green"><div class="label">Acumulado 3 dias</div><div class="value">{daily_df.head(3)["precipitation_sum"].fillna(0).sum():.1f} mm</div><div class="sub">Base curta de decisão</div></div>', unsafe_allow_html=True)
with kpi_cols[1]:
    st.markdown(f'<div class="metric-card metric-blue"><div class="label">Acumulado 7 dias</div><div class="value">{daily_df.head(7)["precipitation_sum"].fillna(0).sum():.1f} mm</div><div class="sub">Janela curta de safra</div></div>', unsafe_allow_html=True)
with kpi_cols[2]:
    st.markdown(f'<div class="metric-card metric-purple"><div class="label">Confiab. média 3 dias</div><div class="value">{daily_df.head(3)["confidence_pct"].mean():.0f}%</div><div class="sub">Heurística do painel para chuva</div></div>', unsafe_allow_html=True)
with kpi_cols[3]:
    best_row = daily_df.iloc[daily_df["precipitation_sum"].fillna(0).values.argmax()]
    st.markdown(f'<div class="metric-card metric-slate"><div class="label">Melhor dia próximo</div><div class="value">{best_row["precipitation_sum"]:.1f} mm</div><div class="sub">{best_row["time"].strftime("%d/%m")} | confiança {best_row["confidence_pct"]:.0f}%</div></div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="title-row"><div><div class="section-title">Previsão futura sempre à vista</div><div class="section-sub">Próximos 7 dias com mm, probabilidade e confiança estimada</div></div><span class="info-badge">Foco principal</span></div>', unsafe_allow_html=True)
html_days = '<div class="days-wrap">'
for row in future_cards:
    html_days += f'''<div class="day-card"><div class="d1">{row['weekday']} · {row['date']}</div><div class="d2">{row['mm']:.1f} mm</div><div class="d3">Prob. {row['prob']:.0f}% · {row['tmin']:.0f}/{row['tmax']:.0f}°C</div><span class="conf {row['conf_class']}">Conf. {row['conf']}%</span></div>'''
html_days += '</div>'
st.markdown(html_days, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

left, right = st.columns([1.1, 0.9])
with left:
    st.markdown('<div class="good-window">', unsafe_allow_html=True)
    st.markdown(f"<h3>🌱 🌧️ QUANDO ESTIVER BOM DE VERDADE</h3><div style='margin-top:.45rem;font-size:1.05rem;font-weight:800;'>{good_title}</div><div style='margin-top:.35rem;opacity:.96;'>{good_desc}</div>", unsafe_allow_html=True)
    crit_html = "<ul>"
    for ok, txt in good_criteria:
        crit_html += f"<li>{'✅' if ok else '⚪'} {txt}</li>"
    crit_html += "</ul><div style='margin-top:.3rem; opacity:.94;'>Critérios batidos: <b>{}/4</b></div>".format(good_met)
    st.markdown(crit_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Leitura automática</div><div class="section-sub">Resumo objetivo para decisão de campo</div></div><span class="info-badge">IA analítica</span></div>', unsafe_allow_html=True)
    st.markdown(f"**Status de plantio:** {status_label}")
    st.markdown(f"**Chegada da chuva:** {arrival_label}")
    st.markdown(f"**Leitura de confiança:** {confidence_msg}")
    st.write(status_msg)
    st.write(arrival_msg)
    st.info("Use este resumo junto com a chuva observada na propriedade e a umidade real do solo.")
    st.markdown('</div>', unsafe_allow_html=True)

map_col, msg_col = st.columns([1.18, 0.82])
with map_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Mapa da roça com radar</div><div class="section-sub">Área desenhada sobre satélite com radar RainViewer</div></div><span class="info-badge">{}</span></div>'.format(radar_label or "Sem radar"), unsafe_allow_html=True)
    fmap = make_map(area_geojson, lat, lon, radar_url=radar_url, radar_label=radar_label, show_satellite=show_satellite, show_points=show_points)
    st_folium(fmap, width=None, height=570, returned_objects=[])
    st.markdown('</div>', unsafe_allow_html=True)
with msg_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Mensagens automáticas</div><div class="section-sub">Prévia da manhã e da tarde para copiar ou enviar no Telegram</div></div><span class="info-badge">Telegram opcional</span></div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Mensagem da manhã", "Mensagem da tarde"])
    with tab1:
        st.caption("Visão geral com próximos dias, mm e confiança.")
        copy_box(morning_msg, "manha")
    with tab2:
        st.caption("Atualização curta baseada no radar e nas próximas horas.")
        copy_box(afternoon_msg, "tarde")
    st.markdown('</div>', unsafe_allow_html=True)


tele_col1, tele_col2 = st.columns([1.05, 0.95])
with tele_col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Telegram</div><div class="section-sub">Envio de teste, descoberta de chat_id e disparo da mensagem da manhã/tarde</div></div><span class="info-badge">Opcional</span></div>', unsafe_allow_html=True)
    secret_token = get_secret("TELEGRAM_BOT_TOKEN", "")
    secret_chat = get_secret("TELEGRAM_CHAT_ID", "")
    if secret_token:
        st.success("Token carregado dos secrets do Streamlit.")
    custom_token = st.text_input("Token do bot (opcional sobrescrever)", type="password", placeholder="Cole aqui só se quiser testar manualmente agora")
    telegram_token = custom_token.strip() or secret_token
    custom_chat = st.text_input("Chat ID principal", value=secret_chat, help="Pode ser seu ID pessoal ou o ID de um grupo/canal onde o bot esteja.")
    st.caption("Se o chat_id ainda não estiver claro, clique em buscar chats. Antes disso, abra o bot no Telegram e envie /start para ele.")
    cta1, cta2 = st.columns(2)
    with cta1:
        if st.button("Buscar chats do bot", use_container_width=True, disabled=not telegram_token):
            try:
                updates = telegram_get_updates(telegram_token)
                st.session_state["telegram_candidates"] = telegram_chat_candidates(updates)
                if not st.session_state["telegram_candidates"]:
                    st.warning("Não encontrei chats nas atualizações do bot. No Telegram, abra o bot e envie /start; depois tente de novo.")
            except Exception as e:
                st.error(f"Falha ao consultar getUpdates: {e}")
    with cta2:
        if st.button("Enviar teste curto", use_container_width=True, disabled=not (telegram_token and custom_chat.strip())):
            try:
                telegram_send_message(telegram_token, custom_chat.strip(), "✅ Teste do Clima da Roça Pro: bot integrado com sucesso.")
                st.success("Mensagem de teste enviada.")
            except Exception as e:
                st.error(f"Falha ao enviar teste: {e}")
    candidates = st.session_state.get("telegram_candidates", [])
    if candidates:
        st.write("**Chats encontrados pelo bot**")
        st.dataframe(pd.DataFrame(candidates), use_container_width=True, hide_index=True)
        picked = st.selectbox("Escolha um chat_id encontrado", options=[""] + [c["chat_id"] for c in candidates], index=0)
        if picked:
            st.info(f"Use este chat_id: {picked}")
    st.markdown('</div>', unsafe_allow_html=True)

with tele_col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Enviar relatório no Telegram</div><div class="section-sub">Usa a mesma mensagem detalhada com emojis, mm e confiança</div></div><span class="info-badge">Pronto para usar</span></div>', unsafe_allow_html=True)
    send_chat = st.text_input("Chat ID para envio", value=secret_chat, key="telegram_send_chat")
    s1, s2 = st.columns(2)
    with s1:
        if st.button("Enviar mensagem da manhã", use_container_width=True, disabled=not (telegram_token and send_chat.strip())):
            try:
                telegram_send_message(telegram_token, send_chat.strip(), morning_msg)
                st.success("Mensagem da manhã enviada no Telegram.")
            except Exception as e:
                st.error(f"Falha ao enviar mensagem da manhã: {e}")
    with s2:
        if st.button("Enviar mensagem da tarde", use_container_width=True, disabled=not (telegram_token and send_chat.strip())):
            try:
                telegram_send_message(telegram_token, send_chat.strip(), afternoon_msg)
                st.success("Mensagem da tarde enviada no Telegram.")
            except Exception as e:
                st.error(f"Falha ao enviar mensagem da tarde: {e}")
    st.caption("Para produção, salve o token e o chat_id em secrets. Não coloque essas credenciais dentro do repositório.")
    st.markdown('</div>', unsafe_allow_html=True)


c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Previsão diária</div><div class="section-sub">Volume previsto e confiança estimada por dia</div></div></div>', unsafe_allow_html=True)
    plot_daily = daily_df.head(10).copy()
    bars = alt.Chart(plot_daily).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("dia_txt:N", sort=None, title="Dia"),
        y=alt.Y("precipitation_sum:Q", title="Chuva (mm)"),
        tooltip=["time:T", alt.Tooltip("precipitation_sum:Q", format=".1f"), alt.Tooltip("precipitation_probability_max:Q", format=".0f"), alt.Tooltip("confidence_pct:Q", format=".0f")],
    )
    line = alt.Chart(plot_daily).mark_line(point=True).encode(
        x=alt.X("dia_txt:N", sort=None),
        y=alt.Y("confidence_pct:Q", title="Confiança (%)"),
    )
    st.altair_chart((bars + line).resolve_scale(y="independent"), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Próximas 72 horas</div><div class="section-sub">Leitura horária para saber se está chegando</div></div></div>', unsafe_allow_html=True)
    next72 = hourly_df.head(72).copy()
    next72["hora"] = next72["time"].dt.strftime("%d/%m %Hh")
    hourly_chart = alt.Chart(next72).mark_bar().encode(
        x=alt.X("hora:N", sort=None, title="Hora", axis=alt.Axis(labelAngle=-55)),
        y=alt.Y("precipitation:Q", title="Chuva (mm/h)"),
        tooltip=["time:T", alt.Tooltip("precipitation:Q", format=".1f"), alt.Tooltip("precipitation_probability:Q", format=".0f")],
    )
    st.altair_chart(hourly_chart, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

c3, c4 = st.columns(2)
with c3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Histórico recente</div><div class="section-sub">NASA POWER - últimos 120 dias</div></div></div>', unsafe_allow_html=True)
    rain_hist = alt.Chart(power_df.tail(45)).mark_bar().encode(
        x=alt.X("date:T", title="Data"),
        y=alt.Y("chuva_mm:Q", title="Chuva (mm)"),
        tooltip=["date:T", alt.Tooltip("chuva_mm:Q", format=".1f")],
    )
    st.altair_chart(rain_hist, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
with c4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Tabela de apoio</div><div class="section-sub">Previsão diária com confiança sempre visível</div></div></div>', unsafe_allow_html=True)
    table_df = daily_df[["time", "precipitation_sum", "confidence_pct", "precipitation_probability_max", "temperature_2m_min", "temperature_2m_max", "wind_speed_10m_max"]].copy()
    table_df.columns = ["Data", "Chuva (mm)", "Confiança (%)", "Prob. máx (%)", "Temp mín (°C)", "Temp máx (°C)", "Vento máx (km/h)"]
    st.dataframe(table_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
