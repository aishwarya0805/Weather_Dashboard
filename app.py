import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- Config ---
API_KEY = "57b0d132585bcfc961b5eb812123a65b"
BASE_URL = "https://api.openweathermap.org/data/2.5"

st.set_page_config(page_title="Weather Dashboard", page_icon="🌤", layout="wide")
st.title("🌤 Weather Dashboard")

# --- Search ---
city = st.text_input("Enter city name")

# --- Helper functions ---
def kelvin_to_c(k): return round(k - 273.15, 1)
def c_to_f(c): return round(c * 9/5 + 32, 1)
def wind_dir(deg):
    dirs = ['N','NE','E','SE','S','SW','W','NW']
    return dirs[round(deg / 45) % 8]

@st.cache_data(ttl=600)
def fetch_weather(city):
    current = requests.get(f"{BASE_URL}/weather",
        params={"q": city, "appid": API_KEY, "units": "metric"}).json()
    forecast = requests.get(f"{BASE_URL}/forecast",
        params={"q": city, "appid": API_KEY, "units": "metric"}).json()
    return current, forecast

def transform_forecast(forecast):
    rows = []
    for item in forecast["list"]:
        rows.append({
            "datetime":  datetime.fromtimestamp(item["dt"]),
            "temp_c":    round(item["main"]["temp"], 1),
            "temp_f":    c_to_f(item["main"]["temp"]),
            "feels_c":   round(item["main"]["feels_like"], 1),
            "humidity":  item["main"]["humidity"],
            "wind_kmh":  round(item["wind"]["speed"] * 3.6, 1),
            "wind_dir":  wind_dir(item["wind"].get("deg", 0)),
            "condition": item["weather"][0]["main"],
            "desc":      item["weather"][0]["description"],
            "pressure":  item["main"]["pressure"],
        })
    return pd.DataFrame(rows)

# --- Main app ---
if city:
    try:
        current, forecast = fetch_weather(city)

        if current.get("cod") != 200:
            st.error(f"City not found: {current.get('message', 'unknown error')}")
            st.stop()

        df = transform_forecast(forecast)

        # --- Unit toggle ---
        unit = st.radio("Temperature unit", ["°C", "°F"], horizontal=True)
        temp_col = "temp_c" if unit == "°C" else "temp_f"
        temp_now = round(current["main"]["temp"], 1) if unit == "°C" else c_to_f(current["main"]["temp"])
        feels = round(current["main"]["feels_like"], 1) if unit == "°C" else c_to_f(current["main"]["feels_like"])

        st.subheader(f"{current['name']}, {current['sys']['country']} — {current['weather'][0]['description'].title()}")

        # --- Metric cards ---
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Temperature", f"{temp_now}{unit}", f"Feels like {feels}{unit}")
        c2.metric("Humidity", f"{current['main']['humidity']}%")
        c3.metric("Wind", f"{round(current['wind']['speed'] * 3.6)} km/h", wind_dir(current['wind'].get('deg', 0)))
        c4.metric("Pressure", f"{current['main']['pressure']} hPa")
        c5.metric("Visibility", f"{round(current.get('visibility', 0) / 1000, 1)} km")

        st.divider()

        # --- Hourly temperature chart ---
        st.subheader("Hourly temperature — next 24h")
        hourly = df.head(8).copy()
        hourly["hour"] = hourly["datetime"].dt.strftime("%H:%M")
        st.line_chart(hourly.set_index("hour")[temp_col])

        # --- Humidity & wind charts side by side ---
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Humidity % — next 24h")
            st.bar_chart(hourly.set_index("hour")["humidity"])
        with col2:
            st.subheader("Wind speed (km/h) — next 24h")
            st.line_chart(hourly.set_index("hour")["wind_kmh"])

        st.divider()

        # --- 5-day forecast ---
        st.subheader("5-day forecast")
        daily = df.groupby(df["datetime"].dt.date).agg(
            High=(temp_col, "max"),
            Low=(temp_col, "min"),
            Humidity=("humidity", "mean"),
            Wind=("wind_kmh", "max"),
            Condition=("condition", "first")
        ).reset_index()
        daily.columns = ["Date", f"High ({unit})", f"Low ({unit})", "Avg Humidity %", "Max Wind km/h", "Condition"]
        daily["Avg Humidity %"] = daily["Avg Humidity %"].round(1)
        st.dataframe(daily, use_container_width=True, hide_index=True)

        st.divider()

        # --- Raw data expander ---
        with st.expander("View raw transformed data"):
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Something went wrong: {e}")