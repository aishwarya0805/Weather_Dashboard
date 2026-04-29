import streamlit as st
import requests
import pandas as pd
import sqlite3
import os
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from datetime import datetime

# Load API key from .env file
load_dotenv()
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

st.set_page_config(page_title="Weather Dashboard", page_icon="🌤", layout="wide")
st.title("🌤 Weather Dashboard")

# ─── SQLite Setup ─────────────────────────────────────────────
# Creates weather.db in your project folder automatically
# All searches get saved here for history tracking

def init_db():
    # Connect to SQLite database (creates file if it doesn't exist)
    conn = sqlite3.connect("weather.db")
    
    # Create searches table if it doesn't already exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            city        TEXT,
            country     TEXT,
            temp_c      REAL,
            feels_c     REAL,
            humidity    INTEGER,
            wind_kmh    REAL,
            pressure    INTEGER,
            visibility  REAL,
            condition   TEXT,
            searched_at TEXT
        )
    """)
    conn.commit()
    return conn

def save_search(conn, city, country, current):
    # Save each search to SQLite for history tracking
    conn.execute("""
        INSERT INTO searches (
            city, country, temp_c, feels_c, humidity,
            wind_kmh, pressure, visibility, condition, searched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        city,
        country,
        round(current["main"]["temp"], 1),
        round(current["main"]["feels_like"], 1),
        current["main"]["humidity"],
        round(current["wind"]["speed"] * 3.6, 1),
        current["main"]["pressure"],
        round(current.get("visibility", 0) / 1000, 1),
        current["weather"][0]["main"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()

def get_search_history(conn):
    # Fetch last 50 searches from SQLite ordered by most recent
    return pd.read_sql("""
        SELECT city, country, temp_c, humidity,
               wind_kmh, condition, searched_at
        FROM searches
        ORDER BY searched_at DESC
        LIMIT 10
    """, conn)

def get_city_stats(conn, city):
    # SQL aggregation — avg/min/max per city across all searches
    return pd.read_sql("""
        SELECT
            COUNT(*)            AS total_searches,
            ROUND(AVG(temp_c),1)AS avg_temp,
            ROUND(MAX(temp_c),1)AS max_temp,
            ROUND(MIN(temp_c),1)AS min_temp,
            ROUND(AVG(humidity))AS avg_humidity
        FROM searches
        WHERE LOWER(city) = LOWER(?)
    """, conn, params=(city,))


# ─── Helper functions ──────────────────────────────────────────

def c_to_f(c): 
    return round(c * 9/5 + 32, 1)

def wind_dir(deg):
    dirs = ['N','NE','E','SE','S','SW','W','NW']
    return dirs[round(deg / 45) % 8]

def weather_emoji(condition):
    # Map condition string to a relevant emoji
    icons = {
        "thunderstorm": "⛈",
        "drizzle":      "🌦",
        "rain":         "🌧",
        "snow":         "❄",
        "mist":         "🌫",
        "fog":          "🌫",
        "clear":        "☀",
        "clouds":       "☁"
    }
    condition_lower = condition.lower()
    for key, icon in icons.items():
        if key in condition_lower:
            return icon
    return "🌡"


# ─── API fetch ─────────────────────────────────────────────────

@st.cache_data(ttl=600)
def fetch_weather(city):
    # Cache results for 10 minutes to avoid burning API quota
    current = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"q": city, "appid": WEATHER_API_KEY, "units": "metric"}
    ).json()
    forecast = requests.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={"q": city, "appid": WEATHER_API_KEY, "units": "metric"}
    ).json()
    return current, forecast

@st.cache_data(ttl=600)
def fetch_weather_by_coords(lat, lon):
    """
    Fetch weather using coordinates instead of city name.
    Much more accurate — avoids returning wrong city when
    names are shared across countries (e.g. San Jose).
    """
    current = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={
            "lat":   lat,
            "lon":   lon,
            "appid": WEATHER_API_KEY,
            "units": "metric"
        }
    ).json()
    return current


# ─── Data transformation ───────────────────────────────────────

def transform_forecast(forecast, unit):
    rows = []
    for item in forecast["list"]:
        temp_c = round(item["main"]["temp"], 1)
        rows.append({
            "datetime":  datetime.fromtimestamp(item["dt"]),
            "temp_c":    temp_c,
            "temp_f":    c_to_f(temp_c),
            "humidity":  item["main"]["humidity"],
            "wind_kmh":  round(item["wind"]["speed"] * 3.6, 1),
            "condition": item["weather"][0]["main"],
            "desc":      item["weather"][0]["description"],
            "pressure":  item["main"]["pressure"],
        })
    df = pd.DataFrame(rows)
    # Add display column based on selected unit
    df["temp_display"] = df["temp_c"] if unit == "°C" else df["temp_f"]
    return df


# ─── Weather alerts ────────────────────────────────────────────

def show_alerts(current):
    temp     = current["main"]["temp"]
    humidity = current["main"]["humidity"]
    wind     = current["wind"]["speed"] * 3.6
    condition= current["weather"][0]["main"].lower()

    alerts = []

    # Temperature alerts
    if temp > 38:
        alerts.append(("error",   "Extreme heat warning — temperature above 38°C. Stay indoors and hydrated."))
    elif temp > 33:
        alerts.append(("warning", "Heat advisory — temperature above 33°C. Limit outdoor activity."))
    elif temp < 0:
        alerts.append(("error",   "Freezing conditions — below 0°C. Ice and frost likely."))
    elif temp < 5:
        alerts.append(("warning", "Cold advisory — below 5°C. Dress warmly."))

    # Humidity alerts
    if humidity > 90:
        alerts.append(("warning", "Very high humidity — above 90%. Feels significantly hotter."))

    # Wind alerts
    if wind > 80:
        alerts.append(("error",   "Severe wind warning — above 80 km/h. Avoid outdoor activities."))
    elif wind > 50:
        alerts.append(("warning", "Strong wind advisory — above 50 km/h. Secure loose objects."))

    # Rain/storm alerts
    if "thunderstorm" in condition:
        alerts.append(("error",   "Thunderstorm warning — seek shelter indoors."))
    elif "rain" in condition:
        alerts.append(("warning", "Rain expected — carry an umbrella."))
    elif "snow" in condition:
        alerts.append(("warning", "Snow conditions — roads may be slippery."))

    # Show alerts or all-clear
    if alerts:
        for alert_type, message in alerts:
            if alert_type == "error":
                st.error(message)
            else:
                st.warning(message)
    else:
        st.success("All clear — no weather alerts for this location.")


# ─── Mock AI insights ──────────────────────────────────────────
# Replace this function with real Claude API call when going public

def get_ai_insights(city, current, daily_df, unit):
    temp      = round(current["main"]["temp"], 1) if unit == "°C" else c_to_f(current["main"]["temp"])
    feels     = round(current["main"]["feels_like"], 1) if unit == "°C" else c_to_f(current["main"]["feels_like"])
    humidity  = current["main"]["humidity"]
    wind      = round(current["wind"]["speed"] * 3.6)
    condition = current["weather"][0]["description"]
    visibility= round(current.get("visibility", 0) / 1000, 1)

    # Comfort level
    if humidity > 80 and temp > 25:
        comfort = "muggy and uncomfortable — high humidity traps heat"
    elif temp < 5:
        comfort = "bitterly cold — dress in layers"
    elif temp > 35:
        comfort = "dangerously hot — stay hydrated and avoid the sun"
    else:
        comfort = "comfortable and pleasant"

    # Best time outside
    if temp > 32 or "thunderstorm" in condition:
        best_time = "Stay indoors if possible. Early morning before 8am is your safest window."
    elif temp < 2:
        best_time = "Midday (12pm–2pm) is warmest — best time to head outside."
    else:
        best_time = "Morning (8–11am) or evening (5–7pm) are the most comfortable windows."

    # Outfit
    if temp > 30:
        outfit = "Light breathable clothing. Sunscreen and a hat are essential."
    elif temp > 20:
        outfit = "T-shirt and light trousers. A light layer for the evening."
    elif temp > 10:
        outfit = "A jacket or hoodie. Comfortable trousers."
    else:
        outfit = "Heavy winter coat, gloves, hat, and thermal layers."

    # Umbrella
    rain_conditions = ["rain", "drizzle", "thunderstorm", "shower"]
    needs_umbrella  = any(r in condition.lower() for r in rain_conditions)
    umbrella_tip    = "Carry an umbrella — rain is likely." if needs_umbrella else "No umbrella needed today."

    # 5-day trend
    hi_col = f"High ({unit})"
    if hi_col in daily_df.columns and len(daily_df) >= 3:
        temps_ahead = daily_df[hi_col].tolist()
        diff        = temps_ahead[-1] - temps_ahead[0]
        if diff > 5:
            trend = f"Temperatures rising — warming up to {temps_ahead[-1]}{unit} by end of week."
        elif diff < -5:
            trend = f"Cooler spell coming — dropping to {temps_ahead[-1]}{unit} by end of week."
        else:
            trend = "Temperatures stay consistent — no major changes ahead."
    else:
        trend = "Check the 5-day table below for upcoming changes."

    # Activity
    if "clear" in condition and 15 <= temp <= 28:
        activity = "Perfect for a walk, run, or picnic in the park."
    elif "rain" in condition:
        activity = "Great day for a museum, café, or indoor plans."
    elif temp > 30:
        activity = "Head to an air-conditioned space — mall, cinema, or library."
    else:
        activity = "Good conditions for a casual stroll or outdoor errands."

    return f"""
**Current conditions in {city}**
It's {temp}{unit} (feels like {feels}{unit}) with {condition}.
Conditions feel {comfort}. Humidity is {humidity}%, wind at {wind} km/h, visibility {visibility} km.

**Best time to go outside**
{best_time}

**What to wear**
{outfit} {umbrella_tip}

**Coming up this week**
{trend}

**Activity suggestion**
{activity}
"""


# ─── Main app ──────────────────────────────────────────────────

# Initialize SQLite database
conn = init_db()

# Sidebar — search history and city comparison
with st.sidebar:
    st.header("Search history")
    history = get_search_history(conn)
    if history.empty:
        st.caption("No searches yet — search a city to get started.")
    else:
        st.dataframe(history, use_container_width=True, hide_index=True)
        csv = history.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download history as CSV",
            data=csv,
            file_name="weather_history.csv",
            mime="text/csv"
        )

    st.divider()

    # ── Compare cities (sidebar only) ─────────────────────────
    st.header("Compare cities")
    st.caption(f"Add cities to compare against your main search")

    # Initialize session state
    if "compare_cities"     not in st.session_state:
        st.session_state["compare_cities"]     = []
    if "compare_city_keys"  not in st.session_state:
        st.session_state["compare_city_keys"]  = []  # stores raw API query strings

    compare_input = st.text_input(
        "Search city",
        key="compare_input",
        placeholder="e.g. San Jose, Mumbai...",
        label_visibility="collapsed"
    )

    # ── Geocoding API search ───────────────────────────────────
    # Fetch real city suggestions from OpenWeatherMap Geocoding API
    # Returns up to 5 matches with city, state, country info
    @st.cache_data(ttl=300)
    def search_cities(query):
        """
        Calls OpenWeatherMap Geocoding API.
        Returns list of dicts with name, state, country, lat, lon.
        Cache for 5 minutes to avoid hammering the API while typing.
        """
        if not query or len(query) < 2:
            return []
        try:
            res = requests.get(
                "https://api.openweathermap.org/geo/1.0/direct",
                params={
                    "q":     query,
                    "limit": 5,          # max 5 suggestions
                    "appid": WEATHER_API_KEY
                }
            ).json()

            results = []
            for item in res:
                # Build display label: City, State, Country
                # State is not always returned (non-US cities often skip it)
                label_parts = [item["name"]]
                if item.get("state"):
                    label_parts.append(item["state"])
                label_parts.append(item["country"])
                label = ", ".join(label_parts)

                results.append({
                    "label": label,           # e.g. "San Jose, California, US"
                    "name":  item["name"],    # e.g. "San Jose"
                    "state": item.get("state", ""),
                    "country": item["country"],
                    "lat":   item["lat"],
                    "lon":   item["lon"],
                    # Query string to pass to weather API using coordinates
                    # Using lat/lon is more precise than city name alone
                    "query": f"{item['lat']},{item['lon']}"
                })
            return results
        except:
            return []

    # Show suggestions when user has typed 2+ characters
    if compare_input and len(compare_input) >= 2:
        suggestions = search_cities(compare_input)

        if suggestions:
            st.caption("Select a city to add:")
            for s in suggestions:
                # Skip cities already added
                if s["label"] in st.session_state["compare_cities"]:
                    continue
                if st.button(s["label"], key=f"suggest_{s['label']}"):
                    st.session_state["compare_cities"].append(s["label"])
                    # Store lat/lon query for accurate weather fetch
                    st.session_state["compare_city_keys"].append({
                        "label": s["label"],
                        "query": s["query"]
                    })
                    st.rerun()
        else:
            st.caption("No matches found — try a different spelling.")

    # Show added cities with remove buttons
    if st.session_state["compare_cities"]:
        st.caption("Added cities:")
        for c in list(st.session_state["compare_cities"]):
            col_a, col_b = st.columns([3, 1])
            col_a.write(f"• {c}")
            if col_b.button("✕", key=f"remove_{c}"):
                # Remove from both lists
                st.session_state["compare_cities"].remove(c)
                st.session_state["compare_city_keys"] = [
                    x for x in st.session_state["compare_city_keys"]
                    if x["label"] != c
                ]
                st.rerun()

        if st.button("Clear all", use_container_width=True):
            st.session_state["compare_cities"]    = []
            st.session_state["compare_city_keys"] = []
            st.rerun()
    else:
        st.caption("No cities added yet.")

    compare_cities     = st.session_state.get("compare_cities", [])
    compare_city_keys  = st.session_state.get("compare_city_keys", [])

# Main search input
city = st.text_input("Enter city name", "San Francisco")
unit = st.radio("Temperature unit", ["°C", "°F"], horizontal=True)

if city:
    try:
        current, forecast = fetch_weather(city)

        if current.get("cod") != 200:
            st.error(f"City not found: {current.get('message')}")
            st.stop()

        # Save every search to SQLite automatically
        save_search(conn, current["name"], current["sys"]["country"], current)

        df       = transform_forecast(forecast, unit)
        temp_col = "temp_c" if unit == "°C" else "temp_f"
        temp_now = round(current["main"]["temp"], 1) if unit == "°C" else c_to_f(current["main"]["temp"])
        feels    = round(current["main"]["feels_like"], 1) if unit == "°C" else c_to_f(current["main"]["feels_like"])
        emoji    = weather_emoji(current["weather"][0]["main"])

        st.subheader(f"{emoji} {current['name']}, {current['sys']['country']} — {current['weather'][0]['description'].title()}")

        # ── Metric cards ───────────────────────────────────────
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Temperature", f"{temp_now}{unit}", f"Feels like {feels}{unit}")
        c2.metric("Humidity",    f"{current['main']['humidity']}%")
        c3.metric("Wind",        f"{round(current['wind']['speed'] * 3.6)} km/h", wind_dir(current['wind'].get('deg', 0)))
        c4.metric("Pressure",    f"{current['main']['pressure']} hPa")
        c5.metric("Visibility",  f"{round(current.get('visibility', 0) / 1000, 1)} km")

        st.divider()

        # ── Weather alerts ─────────────────────────────────────
        st.subheader("Weather alerts")
        show_alerts(current)

        st.divider()

        # ── AI Insights ────────────────────────────────────────
        # Build daily summary first (needed for insights)
        daily = df.groupby(df["datetime"].dt.date).agg(
            High=(temp_col, "max"),
            Low=(temp_col, "min"),
            Humidity=("humidity", "mean"),
            Wind=("wind_kmh", "max"),
            Condition=("condition", "first")
        ).reset_index()
        daily.columns = ["Date", f"High ({unit})", f"Low ({unit})",
                         "Avg Humidity %", "Max Wind km/h", "Condition"]
        daily["Avg Humidity %"] = daily["Avg Humidity %"].round(1)

        st.subheader("AI weather insights")
        st.caption("Mock insights — swap get_ai_insights() for Claude API when going public")

        with st.spinner("Analyzing weather..."):
            insight_key = f"insights_{city}_{unit}"
            if insight_key not in st.session_state:
                st.session_state[insight_key] = get_ai_insights(city, current, daily, unit)

        st.info(st.session_state[insight_key])

        st.divider()

        # ── Plotly charts ──────────────────────────────────────
        hourly         = df.head(8).copy()
        hourly["hour"] = hourly["datetime"].dt.strftime("%H:%M")

        # Temperature line chart
        st.subheader("Hourly temperature — next 24h")
        fig_temp = px.line(
            hourly, x="hour", y="temp_display",
            markers=True,
            labels={"temp_display": f"Temp ({unit})", "hour": "Time"},
        )
        fig_temp.update_traces(line_color="#378ADD", marker=dict(size=6))
        fig_temp.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            height=250
        )
        st.plotly_chart(fig_temp, use_container_width=True)

        # Humidity and wind side by side
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Humidity % — next 24h")
            fig_humid = px.bar(
                hourly, x="hour", y="humidity",
                labels={"humidity": "Humidity %", "hour": "Time"},
                color_discrete_sequence=["#1D9E75"]
            )
            fig_humid.update_layout(margin=dict(l=0,r=0,t=10,b=0), height=220)
            st.plotly_chart(fig_humid, use_container_width=True)

        with col2:
            st.subheader("Wind speed — next 24h")
            fig_wind = px.line(
                hourly, x="hour", y="wind_kmh",
                markers=True,
                labels={"wind_kmh": "Wind (km/h)", "hour": "Time"},
                color_discrete_sequence=["#EF9F27"]
            )
            fig_wind.update_layout(margin=dict(l=0,r=0,t=10,b=0), height=220)
            st.plotly_chart(fig_wind, use_container_width=True)

        st.divider()

        # ── 5-day forecast ─────────────────────────────────────
        st.subheader("5-day forecast")

        # Plotly grouped bar — high vs low per day
        fig_forecast = go.Figure(data=[
            go.Bar(name=f"High ({unit})", x=daily["Date"].astype(str),
                   y=daily[f"High ({unit})"], marker_color="#378ADD"),
            go.Bar(name=f"Low ({unit})",  x=daily["Date"].astype(str),
                   y=daily[f"Low ({unit})"],  marker_color="#B5D4F4")
        ])
        fig_forecast.update_layout(
            barmode="group",
            height=280,
            margin=dict(l=0,r=0,t=10,b=0)
        )
        st.plotly_chart(fig_forecast, use_container_width=True)

        # Forecast table below chart
        st.dataframe(daily, use_container_width=True, hide_index=True)

        # CSV export of current forecast
        st.subheader("Export forecast data")
        csv_forecast = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"Download {city} forecast as CSV",
            data=csv_forecast,
            file_name=f"{city.lower().replace(' ','_')}_forecast.csv",
            mime="text/csv"
        )

        st.divider()

        # ── City stats from SQLite ─────────────────────────────
        stats = get_city_stats(conn, current["name"])
        if not stats.empty and stats["total_searches"].iloc[0] > 1:
            st.subheader(f"Your search stats for {current['name']}")
            s1, s2, s3, s4, s5 = st.columns(5)
            s1.metric("Times searched",  stats["total_searches"].iloc[0])
            s2.metric("Avg temperature", f"{stats['avg_temp'].iloc[0]}{unit}")
            s3.metric("Highest recorded",f"{stats['max_temp'].iloc[0]}{unit}")
            s4.metric("Lowest recorded", f"{stats['min_temp'].iloc[0]}{unit}")
            s5.metric("Avg humidity",    f"{stats['avg_humidity'].iloc[0]}%")
            st.divider()

        # ── Raw data ───────────────────────────────────────────
        with st.expander("View raw transformed data"):
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Something went wrong: {e}")


# ── City comparison (from sidebar selection) ───────────────────
# Always include the main searched city + sidebar cities

if compare_cities and len(compare_cities) >= 1:
    # Combine main city with sidebar cities for comparison
    all_compare = [city] + compare_cities  # main city is always first
    all_compare_keys = [{"label": city, "query": city}] + compare_city_keys

    st.divider()
    st.subheader(f"Comparing {city} vs {', '.join(compare_cities)}")
    compare_data = []

    for city_key in all_compare_keys:
        try:
            # If it has lat,lon format use coords — otherwise use city name
            query = city_key["query"]
            if "," in str(query) and any(c.isdigit() for c in str(query)):
                lat, lon = query.split(",")
                cur = fetch_weather_by_coords(float(lat), float(lon))
            else:
                # Main city — fetch by name as usual
                cur, _ = fetch_weather(query)

            if cur.get("cod") == 200:
                t = round(cur["main"]["temp"], 1) if unit == "°C" else c_to_f(cur["main"]["temp"])
                compare_data.append({
                    "City":           city_key["label"],
                    f"Temp ({unit})": t,
                    "Humidity %":     round(cur["main"]["humidity"]),
                    "Wind km/h":      round(cur["wind"]["speed"] * 3.6),
                    "Pressure hPa":   cur["main"]["pressure"],
                    "Condition":      cur["weather"][0]["main"],
                    "Emoji":          weather_emoji(cur["weather"][0]["main"])
                })
        except Exception as e:
            st.warning(f"Could not fetch data for {city_key['label']}: {e}")

    if compare_data:
        cdf = pd.DataFrame(compare_data)

        # Metric cards — main city highlighted, rest normal
        cols = st.columns(len(compare_data))
        for i, row in cdf.iterrows():
            with cols[i]:
                # Highlight the main city card with a caption
                if i == 0:
                    st.caption("Main city")
                else:
                    st.caption("Comparing")
                st.metric(
                    f"{row['Emoji']} {row['City']}",
                    f"{row[f'Temp ({unit})']}{unit}",
                    f"{row['Condition']}"
                )
                st.caption(
                    f"Humidity: {row['Humidity %']}% · "
                    f"Wind: {row['Wind km/h']} km/h"
                )

        # Two charts side by side — temperature and humidity
        ch1, ch2 = st.columns(2)

        with ch1:
            fig_temp = px.bar(
                cdf, x="City", y=f"Temp ({unit})",
                color="City",
                color_discrete_sequence=["#378ADD","#1D9E75","#EF9F27","#D85A30","#7F77DD"],
                title=f"Temperature ({unit})"
            )
            fig_temp.update_layout(
                showlegend=False, height=300,
                margin=dict(l=0, r=0, t=40, b=80),
                xaxis_tickangle=-20
            )
            st.plotly_chart(fig_temp, use_container_width=True)

        with ch2:
            fig_humid = px.bar(
                cdf, x="City", y="Humidity %",
                color="City",
                color_discrete_sequence=["#378ADD","#1D9E75","#EF9F27","#D85A30","#7F77DD"],
                title="Humidity (%)"
            )
            fig_humid.update_layout(
                showlegend=False, height=300,
                margin=dict(l=0, r=0, t=40, b=80),
                xaxis_tickangle=-20
            )
            st.plotly_chart(fig_humid, use_container_width=True)

        # Wind chart full width
        fig_wind = px.bar(
            cdf, x="City", y="Wind km/h",
            color="City",
            color_discrete_sequence=["#378ADD","#1D9E75","#EF9F27","#D85A30","#7F77DD"],
            title="Wind Speed (km/h)"
        )
        fig_wind.update_layout(
            showlegend=False, height=280,
            margin=dict(l=0, r=0, t=40, b=80),
            xaxis_tickangle=-20
        )
        st.plotly_chart(fig_wind, use_container_width=True)

        # Summary table — drop emoji column for clean display
        st.dataframe(
            cdf.drop(columns=["Emoji"]),
            use_container_width=True,
            hide_index=True
        )

elif compare_cities and len(compare_cities) < 1:
    st.info("Add at least 1 city in the sidebar to compare against your main search.")