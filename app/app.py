
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
from folium.features import DivIcon
from streamlit_folium import st_folium

st.set_page_config(page_title="Clima da Roça Pro", page_icon="🌧️", layout="wide")

DEFAULT_LAT = -10.725203
DEFAULT_LON = -38.037884
TZ = "America/Bahia"

CSS = """
<style>
:root {
  --green: #0f7b45;
  --green-soft: #eaf7ef;
  --amber: #b7791f;
  --amber-soft: #fff7e6;
  --red: #b42318;
  --red-soft: #fff0ef;
  --ink: #0f172a;
  --muted: #475569;
  --card: rgba(255,255,255,0.90);
  --line: rgba(15, 23, 42, 0.08);
}
html, body, [data-testid="stAppViewContainer"] {
  background: radial-gradient(circle at top left, #eff6ff 0%, #f0fdf4 35%, #f8fafc 100%);
}
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1400px;}
.hero {
  background: linear-gradient(135deg, #082f49 0%, #0f766e 40%, #14532d 100%);
  color: white; padding: 1.3rem 1.35rem; border-radius: 22px;
  box-shadow: 0 20px 40px rgba(2, 6, 23, 0.18); margin-bottom: 1rem;
}
.hero-grid {display:grid; grid-template-columns: 1.4fr 0.9fr; gap: 1rem; align-items:center;}
.hero h1 {margin: 0; font-size: 2.15rem; line-height: 1.1;}
.hero p {margin: 0.45rem 0 0 0; opacity: 0.94; font-size: 1rem;}
.small-pill {
  display: inline-block; background: rgba(255,255,255,0.13); border: 1px solid rgba(255,255,255,0.16);
  padding: 0.35rem 0.8rem; border-radius: 999px; margin-right: 0.45rem; margin-top: 0.55rem; font-size: 0.9rem;
}
.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 1rem 1rem 0.95rem;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06); height: 100%;
}
.title-row {display:flex; align-items:center; justify-content:space-between; gap:0.7rem; margin-bottom:0.65rem;}
.section-title {font-size: 1.05rem; font-weight: 700; color: var(--ink); margin: 0;}
.section-sub {color: var(--muted); font-size: 0.92rem; margin: 0.25rem 0 0 0;}
.metric-card {
  border-radius: 18px; padding: 1rem; color: white; min-height: 118px; box-shadow: 0 12px 26px rgba(15, 23, 42, 0.14);
}
.metric-card .label {font-size: 0.92rem; opacity: 0.9;}
.metric-card .value {font-size: 1.8rem; font-weight: 800; line-height: 1.15; margin-top: 0.25rem;}
.metric-card .sub {font-size: 0.9rem; opacity: 0.95; margin-top: 0.4rem;}
.metric-green {background: linear-gradient(135deg, #16a34a, #166534);}
.metric-blue {background: linear-gradient(135deg, #0284c7, #075985);}
.metric-purple {background: linear-gradient(135deg, #7c3aed, #6d28d9);}
.metric-slate {background: linear-gradient(135deg, #334155, #0f172a);}
.status-box {border-radius: 20px; padding: 1.1rem 1.15rem; color: white; margin-bottom: 0.8rem; box-shadow: 0 14px 30px rgba(15, 23, 42, 0.14);}
.status-good {background: linear-gradient(135deg, #15803d, #166534);}
.status-warn {background: linear-gradient(135deg, #d97706, #b45309);}
.status-bad {background: linear-gradient(135deg, #dc2626, #b91c1c);}
.status-box h2 {margin: 0; font-size: 1.75rem;}
.status-box p {margin: 0.45rem 0 0 0;}
.status-chip {display:inline-block; background: rgba(255,255,255,0.16); border:1px solid rgba(255,255,255,0.16); padding:0.3rem 0.7rem; border-radius:999px; margin-top:0.7rem; font-size:0.86rem;}
.soft {border: none; height: 1px; background: rgba(15,23,42,0.08); margin: 0.9rem 0 0.95rem;}
.caption-note {color: var(--muted); font-size: 0.92rem;}
.kpi-grid {display:grid; grid-template-columns:repeat(4, 1fr); gap:0.8rem;}
.info-badge {display:inline-block; background:#eef2ff; color:#3730a3; border:1px solid #c7d2fe; padding:0.3rem 0.65rem; border-radius:999px; font-size:0.84rem; font-weight:600;}
.alert-card {background:#ecfeff; border:1px solid #a5f3fc; border-radius:18px; padding:1rem;}
pre.alert-preview {white-space:pre-wrap; background:#0f172a; color:#e2e8f0; padding:0.9rem; border-radius:14px; font-size:0.9rem;}
@media (max-width: 900px) {
  .hero-grid, .kpi-grid {grid-template-columns:1fr;}
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

def fetch_json(url, params=None, timeout=30):
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

def planting_signal(daily_df):
    next3 = daily_df.head(3)
    next5 = daily_df.head(5)
    total3 = float(next3["precipitation_sum"].fillna(0).sum())
    total5 = float(next5["precipitation_sum"].fillna(0).sum())
    strong_days = int((next5["precipitation_sum"].fillna(0) >= 10).sum())
    probable_days = int((next5["precipitation_probability_max"].fillna(0) >= 70).sum())
    score = 0
    score += 2 if total3 >= 20 else 1 if total3 >= 10 else 0
    score += 2 if total5 >= 30 else 1 if total5 >= 18 else 0
    score += 2 if strong_days >= 2 else 1 if strong_days == 1 else 0
    score += 1 if probable_days >= 3 else 0
    if score >= 5:
        return "SINAL BOM", "status-good", "Há chuva mais útil desenhada. Mesmo assim, confirme no solo antes de entrar forte no plantio."
    if score >= 3:
        return "ATENÇÃO", "status-warn", "O cenário melhorou, mas ainda mistura dia bom com dia duvidoso. Vale acompanhar mais 24 a 48 horas."
    return "AGUARDAR", "status-bad", "A chuva segue fraca, espaçada ou pouco confiável. Eu não teria confiança para plantar agora."

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
    if weak >= 5:
        return "A maior parte dos próximos 7 dias tem volume muito baixo. Esse tipo de previsão costuma falhar no ponto exato da roça."
    return "Existe alguma regularidade, mas ainda vale confirmar com radar e chuva observada na propriedade."

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

st.markdown(
    f"""
<div class="hero">
  <div class="hero-grid">
    <div>
      <h1>Clima da Roça Pro</h1>
      <p>Painel visual para acompanhar chuva, radar, semáforo de plantio e leitura automática da sua área.</p>
      <span class="small-pill">Mapa da roça</span>
      <span class="small-pill">Radar sobre satélite</span>
      <span class="small-pill">Semáforo de plantio</span>
    </div>
    <div>
      <div class="card" style="background: rgba(255,255,255,0.12); color: white; border-color: rgba(255,255,255,0.12);">
        <div style="font-size:0.95rem; opacity:0.9;">Leitura automática</div>
        <div style="font-size:1.45rem; font-weight:800; margin-top:0.35rem;">Está chegando ou não?</div>
        <div style="margin-top:0.5rem; opacity:0.95;">O painel cruza previsão horária, diária, radar e histórico recente para traduzir o cenário do campo em linguagem simples.</div>
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

daily_df = daily_dataframe(forecast)
hourly_df = hourly_dataframe(forecast)
current = current_dict(forecast)
power_df = power_dataframe(power)
area_properties = area_geojson["features"][0].get("properties", {})
area_ha = area_properties.get("approx_area_ha")
if area_ha is None:
    coords = area_coords(area_geojson)[:-1]
    area_ha = round(polygon_area_ha(coords), 2)

status_label, status_class, status_msg = planting_signal(daily_df)
arrival_label, arrival_msg = arrival_signal(hourly_df, daily_df)
confidence_msg = confidence_note(daily_df)

frames_df = frames_table(rainviewer)
radar_url = None
radar_label = None
if not frames_df.empty:
    default_frame = len(frames_df) - 1
    frame_choice = st.slider("Frame do radar", min_value=0, max_value=default_frame, value=default_frame)
    radar_url, radar_ts = radar_tile_url(rainviewer, frame_index=frame_choice)
    if radar_ts:
        radar_label = datetime.fromtimestamp(radar_ts, tz=timezone.utc).strftime("%d/%m %H:%M UTC")

col_a, col_b = st.columns([1.1, 0.9])
with col_a:
    st.markdown(f'<div class="status-box {status_class}"><h2>{status_label}</h2><p>{status_msg}</p><span class="status-chip">Chegada da chuva: {arrival_label}</span></div>', unsafe_allow_html=True)
with col_b:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Resumo do dia")
    st.markdown(f"**Chegada da chuva:** {arrival_label}")
    st.markdown(f"**Confiança:** {confidence_msg}")
    st.markdown(f"**Área da roça:** {area_ha:.2f} ha")
    st.markdown(f"**Vento agora:** {current.get('wind_speed_10m', 0):.0f} km/h ({direction_text(current.get('wind_direction_10m'))})")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
kpi_cols = st.columns(4)
with kpi_cols[0]:
    st.markdown(f'<div class="metric-card metric-green"><div class="label">Acumulado 3 dias</div><div class="value">{daily_df.head(3)["precipitation_sum"].fillna(0).sum():.1f} mm</div><div class="sub">Ajuda a medir se a chuva firma ou engana</div></div>', unsafe_allow_html=True)
with kpi_cols[1]:
    st.markdown(f'<div class="metric-card metric-blue"><div class="label">Acumulado 7 dias</div><div class="value">{daily_df.head(7)["precipitation_sum"].fillna(0).sum():.1f} mm</div><div class="sub">Janela curta de safra</div></div>', unsafe_allow_html=True)
with kpi_cols[2]:
    st.markdown(f'<div class="metric-card metric-purple"><div class="label">Temperatura agora</div><div class="value">{current.get("temperature_2m", 0):.1f}°C</div><div class="sub">Umidade {current.get("relative_humidity_2m", 0):.0f}%</div></div>', unsafe_allow_html=True)
with kpi_cols[3]:
    st.markdown(f'<div class="metric-card metric-slate"><div class="label">Melhor dia próximo</div><div class="value">{daily_df.iloc[daily_df["precipitation_sum"].fillna(0).values.argmax()]["precipitation_sum"]:.1f} mm</div><div class="sub">Maior volume previsto nos próximos dias</div></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

left, right = st.columns([1.2, 0.8])
with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Mapa da roça com radar</div><div class="section-sub">Área desenhada sobre o satélite com radar RainViewer</div></div><span class="info-badge">{}</span></div>'.format(radar_label or "Sem radar"), unsafe_allow_html=True)
    fmap = make_map(area_geojson, lat, lon, radar_url=radar_url, radar_label=radar_label, show_satellite=show_satellite, show_points=show_points)
    st_folium(fmap, width=None, height=560, returned_objects=[])
    st.markdown('</div>', unsafe_allow_html=True)
with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Leitura automática</div><div class="section-sub">Resumo profissional para decisão de campo</div></div><span class="info-badge">IA analítica</span></div>', unsafe_allow_html=True)
    st.markdown(f"**Status de plantio:** {status_label}")
    st.markdown(f"**Chegada da chuva:** {arrival_label}")
    st.markdown(f"**Leitura de confiança:** {confidence_msg}")
    st.markdown("### Interpretação")
    st.write(status_msg)
    st.write(arrival_msg)
    st.info("Use este resumo junto com a chuva observada na propriedade e a umidade real do solo.")
    best_day = daily_df.iloc[daily_df["precipitation_sum"].fillna(0).values.argmax()]
    st.markdown("### Melhor janela próxima")
    st.markdown(f"**Data:** {best_day['time'].date()}  ")
    st.markdown(f"**Chuva prevista:** {best_day['precipitation_sum']:.1f} mm  ")
    st.markdown(f"**Probabilidade máxima:** {best_day['precipitation_probability_max']:.0f}%")
    st.markdown('</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="title-row"><div><div class="section-title">Previsão diária</div><div class="section-sub">Volume previsto e chance máxima por dia</div></div></div>', unsafe_allow_html=True)
    daily_plot = daily_df.copy()
    daily_plot["dia"] = daily_plot["time"].dt.strftime("%d/%m")
    bars = alt.Chart(daily_plot).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("dia:N", sort=None, title="Dia"),
        y=alt.Y("precipitation_sum:Q", title="Chuva (mm)"),
        tooltip=["time:T", alt.Tooltip("precipitation_sum:Q", format=".1f"), alt.Tooltip("precipitation_probability_max:Q", format=".0f")],
    )
    line = alt.Chart(daily_plot).mark_line(point=True).encode(
        x=alt.X("dia:N", sort=None),
        y=alt.Y("precipitation_probability_max:Q", title="Probabilidade (%)"),
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
    st.markdown('<div class="title-row"><div><div class="section-title">Tabela de apoio</div><div class="section-sub">Resumo para conferir ponto a ponto</div></div></div>', unsafe_allow_html=True)
    table_df = daily_df[["time", "precipitation_sum", "precipitation_probability_max", "temperature_2m_min", "temperature_2m_max", "wind_speed_10m_max"]].copy()
    table_df.columns = ["Data", "Chuva (mm)", "Prob. máx (%)", "Temp mín (°C)", "Temp máx (°C)", "Vento máx (km/h)"]
    st.dataframe(table_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="title-row"><div><div class="section-title">Como interpretar o painel</div><div class="section-sub">Leitura simples para acompanhar a chuva dia após dia</div></div></div>', unsafe_allow_html=True)
st.markdown(
    """
1. **AGUARDAR**: chuva fraca, espaçada ou muito duvidosa para início seguro do plantio.
2. **ATENÇÃO**: o cenário melhorou, mas ainda precisa de confirmação no solo e nas próximas 24 a 48 horas.
3. **SINAL BOM**: há chuva mais útil desenhada; mesmo assim confirme se a água realmente entrou no solo.
4. **Está chegando ou não?** usa o desenho horário da previsão e a condição recente do radar para mostrar se a chuva tem cara de chegar com força.
5. O mapa mostra sua roça sobre satélite com o radar disponível por cima, para você enxergar se existe núcleo de chuva mais próximo.
"""
)
st.markdown('</div>', unsafe_allow_html=True)
