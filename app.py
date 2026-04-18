
import json
import math
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import altair as alt
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

st.set_page_config(page_title="Clima da Roça Pro", layout="wide")

DEFAULT_LAT = -10.725203
DEFAULT_LON = -38.037884
TZ = "America/Bahia"


def fetch_json(url, params=None, timeout=30):
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=1800)
def get_forecast(lat: float, lon: float):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": TZ,
        "hourly": ",".join([
            "precipitation",
            "precipitation_probability",
            "temperature_2m",
            "relative_humidity_2m",
            "cloud_cover",
            "wind_speed_10m",
            "soil_temperature_0cm",
            "soil_moisture_0_to_1cm",
        ]),
        "daily": ",".join([
            "precipitation_sum",
            "precipitation_probability_max",
            "temperature_2m_max",
            "temperature_2m_min",
            "wind_speed_10m_max",
        ]),
        "forecast_days": 16,
    }
    return fetch_json(url, params)


@st.cache_data(ttl=21600)
def get_nasa_power(lat: float, lon: float):
    end = datetime.utcnow().date() - timedelta(days=1)
    start = end - timedelta(days=89)
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
    url = "https://api.rainviewer.com/public/weather-maps.json"
    return fetch_json(url)


def daily_dataframe(forecast_json):
    daily = forecast_json["daily"]
    df = pd.DataFrame(daily)
    df["time"] = pd.to_datetime(df["time"])
    return df


def hourly_dataframe(forecast_json):
    hourly = forecast_json["hourly"]
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    return df


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


def classify_day(chuva, prob):
    if chuva >= 15:
        return "Boa"
    if chuva >= 8 and prob >= 70:
        return "Moderada"
    if chuva >= 3 and prob >= 60:
        return "Fraca/duvidosa"
    return "Muito incerta"


def planting_signal(daily_df):
    next3 = daily_df.head(3)
    next5 = daily_df.head(5)
    total3 = float(next3["precipitation_sum"].fillna(0).sum())
    total5 = float(next5["precipitation_sum"].fillna(0).sum())
    strong_days = int((next5["precipitation_sum"].fillna(0) >= 8).sum())
    high_prob_days = int((next5["precipitation_probability_max"].fillna(0) >= 70).sum())

    score = 0
    score += 2 if total3 >= 20 else 1 if total3 >= 10 else 0
    score += 2 if total5 >= 30 else 1 if total5 >= 18 else 0
    score += 2 if strong_days >= 2 else 1 if strong_days == 1 else 0
    score += 1 if high_prob_days >= 3 else 0

    if score >= 5:
        return "SINAL BOM", "Há indicativo mais consistente de chuva útil para plantio. Ainda vale conferir chuva real no solo."
    if score >= 3:
        return "ATENÇÃO", "Há alguma chance de melhora, mas ainda não é um cenário de plena confiança para plantar sem chuva observada."
    return "AGUARDAR", "A chuva prevista segue fraca, irregular ou pouco consistente. Eu não confiaria para plantio ainda."


def consistency_note(daily_df):
    weak_days = (daily_df.head(7)["precipitation_sum"].fillna(0) < 3).sum()
    if weak_days >= 5:
        return "A maior parte dos próximos 7 dias tem chuva muito baixa; esse padrão costuma falhar no ponto exato."
    return "Existe alguma regularidade, mas vale vigiar radar e chuva observada antes de decidir."


def parse_kml(file_bytes: bytes):
    root = ET.fromstring(file_bytes)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    points = []
    for coord in root.findall(".//kml:Point/kml:coordinates", ns):
        txt = (coord.text or "").strip()
        if not txt:
            continue
        lon, lat, *_ = [float(x) for x in txt.split(",") if x != ""]
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


def area_center_from_geojson(geojson):
    try:
        coords = geojson["features"][0]["geometry"]["coordinates"][0]
        lons = [p[0] for p in coords[:-1]]
        lats = [p[1] for p in coords[:-1]]
        return sum(lats) / len(lats), sum(lons) / len(lons)
    except Exception:
        return DEFAULT_LAT, DEFAULT_LON


st.title("Clima da Roça Pro")
st.caption("Painel focado em decisão de safra: ver se a chuva está chegando de verdade, no ponto da roça.")

with st.sidebar:
    st.header("Localização")
    default_area = load_default_area()
    if default_area:
        default_area_lat, default_area_lon = area_center_from_geojson(default_area)
    else:
        default_area_lat, default_area_lon = DEFAULT_LAT, DEFAULT_LON

    lat = st.number_input("Latitude", value=float(default_area_lat), format="%.6f")
    lon = st.number_input("Longitude", value=float(default_area_lon), format="%.6f")
    st.caption("O app consulta previsão para o centro da área. Você pode ajustar manualmente.")

    st.header("Área da roça")
    uploaded = st.file_uploader("Envie um KML ou GeoJSON da sua área", type=["kml", "geojson", "json"])
    area_geojson = default_area
    area_info = "Usando a área padrão salva no projeto."

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
            area_info = f"KML lido com {len(points)} marcadores. O contorno foi gerado automaticamente."
        else:
            area_geojson = json.loads(uploaded.getvalue().decode("utf-8"))
            area_info = "GeoJSON carregado com sucesso."

    st.info(area_info)

try:
    forecast = get_forecast(lat, lon)
    power = get_nasa_power(lat, lon)
    rv = get_rainviewer_index()
except Exception as e:
    st.error(f"Erro ao buscar dados: {e}")
    st.stop()

df_daily = daily_dataframe(forecast)
df_hourly = hourly_dataframe(forecast)
df_power = power_dataframe(power)
status, explanation = planting_signal(df_daily)
consistency = consistency_note(df_daily)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Chuva 3 dias", f"{df_daily.head(3)['precipitation_sum'].sum():.1f} mm")
col2.metric("Chuva 7 dias", f"{df_daily.head(7)['precipitation_sum'].sum():.1f} mm")
col3.metric("Maior prob. 5 dias", f"{df_daily.head(5)['precipitation_probability_max'].max():.0f}%")
col4.metric("Status de plantio", status)

st.subheader("Leitura do momento")
st.info(explanation + " " + consistency)

tab1, tab2, tab3, tab4 = st.tabs(["Resumo", "Mapa da roça", "Previsão", "Histórico"])

with tab1:
    st.markdown(
        f"""
### Diagnóstico rápido
- **Status atual:** {status}
- **Leitura prática:** {explanation}
- **Confiabilidade prática:** {consistency}
- **Próximos 5 dias:** {df_daily.head(5)['precipitation_sum'].sum():.1f} mm acumulados
- **Próximos 10 dias:** {df_daily.head(10)['precipitation_sum'].sum():.1f} mm acumulados
"""
    )

with tab2:
    st.subheader("Área da roça no mapa")
    if area_geojson:
        feature = area_geojson["features"][0]
        coords = feature["geometry"]["coordinates"][0]
        hull_points = coords[:-1]
        area_ha = feature.get("properties", {}).get("approx_area_ha", polygon_area_ha(hull_points))
        st.write(f"**Área aproximada:** {area_ha:.2f} ha")
        st.write(f"**Centro consultado para previsão:** lat {lat:.6f}, lon {lon:.6f}")

        polygon_layer = pdk.Layer(
            "GeoJsonLayer",
            data=area_geojson,
            pickable=True,
            stroked=True,
            filled=True,
            extruded=False,
            get_fill_color=[20, 120, 80, 70],
            get_line_color=[20, 120, 80, 220],
            line_width_min_pixels=3,
        )

        points_df = pd.DataFrame([{"lon": p[0], "lat": p[1], "ordem": i + 1} for i, p in enumerate(hull_points)])
        point_layer = pdk.Layer(
            "ScatterplotLayer",
            data=points_df,
            get_position="[lon, lat]",
            get_radius=14,
            get_fill_color=[220, 60, 60, 220],
            pickable=True,
        )

        view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=14)
        st.pydeck_chart(pdk.Deck(
            map_style="light",
            initial_view_state=view_state,
            layers=[polygon_layer, point_layer],
            tooltip={"text": "{ordem}"},
        ))

        st.markdown("#### Pontos usados no contorno")
        st.dataframe(points_df, use_container_width=True)
    else:
        st.warning("Nenhuma área carregada. Envie um KML ou GeoJSON na barra lateral.")

with tab3:
    c1, c2 = st.columns(2)
    with c1:
        chart_daily = alt.Chart(df_daily.head(10)).mark_bar().encode(
            x=alt.X("time:T", title="Dia"),
            y=alt.Y("precipitation_sum:Q", title="Chuva prevista (mm)"),
            tooltip=["time:T", "precipitation_sum:Q", "precipitation_probability_max:Q"]
        ).properties(height=320)
        st.altair_chart(chart_daily, use_container_width=True)

    with c2:
        hourly_72 = df_hourly.head(72).copy()
        chart_hourly = alt.Chart(hourly_72).mark_line().encode(
            x=alt.X("time:T", title="Hora"),
            y=alt.Y("precipitation:Q", title="Chuva horária (mm)"),
            tooltip=["time:T", "precipitation:Q", "precipitation_probability:Q", "cloud_cover:Q"]
        ).properties(height=320)
        st.altair_chart(chart_hourly, use_container_width=True)

    st.subheader("Tabela diária")
    df_show = df_daily.head(10).copy()
    df_show["classificacao"] = df_show.apply(
        lambda r: classify_day(r["precipitation_sum"], r["precipitation_probability_max"]), axis=1
    )
    st.dataframe(
        df_show[
            [
                "time",
                "precipitation_sum",
                "precipitation_probability_max",
                "temperature_2m_min",
                "temperature_2m_max",
                "wind_speed_10m_max",
                "classificacao",
            ]
        ],
        use_container_width=True,
    )

    st.subheader("Resumo automático")
    next5 = df_daily.head(5)
    strongest = next5.loc[next5["precipitation_sum"].idxmax()]
    st.markdown(
        f"""
- **Janela principal:** próximos 5 dias com **{next5['precipitation_sum'].sum():.1f} mm** no total.
- **Melhor dia previsto:** **{strongest['time'].date()}** com **{strongest['precipitation_sum']:.1f} mm** e probabilidade máxima de **{strongest['precipitation_probability_max']:.0f}%**.
- **Leitura prática:** {explanation}
- **Confiabilidade prática:** {consistency}
"""
    )

    st.subheader("Radar / satélite rápido")
    radar_frames = rv.get("radar", {}).get("past", [])
    if radar_frames:
        last = radar_frames[-1]
        st.code(f"Último frame radar UTC: {last.get('time')} | host: {rv.get('host')}")
        st.caption("Você pode evoluir este bloco depois para sobrepor os frames em tempo real no mapa.")
    else:
        st.warning("Nenhum frame de radar retornado agora.")

with tab4:
    st.subheader("Histórico recente (NASA POWER, 90 dias)")
    rolling = df_power[["date", "chuva_mm"]].copy()
    rolling["acumulado_7d"] = rolling["chuva_mm"].rolling(7).sum()
    chart_hist = alt.Chart(rolling).mark_line().encode(
        x=alt.X("date:T", title="Data"),
        y=alt.Y("acumulado_7d:Q", title="Acumulado 7 dias (mm)"),
        tooltip=["date:T", "acumulado_7d:Q"]
    ).properties(height=320)
    st.altair_chart(chart_hist, use_container_width=True)

    st.subheader("Tabela do histórico")
    st.dataframe(df_power.tail(20), use_container_width=True)

st.caption("Este painel ajuda na decisão, mas a confirmação final deve considerar chuva observada na propriedade e condição real do solo.")
