# 🌤 HorizonCast

A live weather dashboard built with **Python + Streamlit** that fetches real-time weather data, transforms it, and displays interactive charts, alerts, AI-powered insights, and city comparisons — all in a clean browser UI.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.56+-red?logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-lightblue?logo=sqlite&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-Charts-darkblue?logo=plotly&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---![License](https://img.shields.io/badge/License-MIT-green)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-username-weather-dashboard.streamlit.app)

---

## 🚀 Live Demo

👉 **[Click here to open the app](https://your-username-weather-dashboard.streamlit.app)**

---

## Features

- **Live weather data** — current conditions and 5-day forecast for any city worldwide
- **Data transformation** — raw API JSON converted into clean, structured tables using pandas
- **Interactive charts** — hourly temperature, humidity, wind speed, and 5-day high/low via Plotly
- **Weather alerts** — automatic warnings for extreme heat, cold, wind, rain, and storms
- **AI weather insights** — plain-English summary explaining what the weather means for you
- **City comparison** — search and compare weather across multiple cities side by side
- **Search history** — every search saved to SQLite with stats (avg/min/max temperature)
- **CSV export** — download forecast data or full search history
- **Unit toggle** — switch between °C and °F instantly
- **Worldwide city search** — powered by OpenWeatherMap Geocoding API (200,000+ cities)

---

## Screenshots

> Search any city → get live conditions, charts, alerts, insights, and comparisons instantly.

---

## Tech Stack

| Technology | Purpose |
|---|---|
| [Streamlit](https://streamlit.io) | Web UI framework |
| [OpenWeatherMap API](https://openweathermap.org/api) | Live weather + geocoding data |
| [Pandas](https://pandas.pydata.org) | Data transformation |
| [Plotly](https://plotly.com/python/) | Interactive charts |
| [SQLite](https://www.sqlite.org) | Local search history storage |
| [Python-dotenv](https://pypi.org/project/python-dotenv/) | Secure API key management |
| [Requests](https://requests.readthedocs.io) | HTTP API calls |

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- A free [OpenWeatherMap API key](https://openweathermap.org/api)

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/aishwarya0805/Weather_Dashboard.git
cd weather-dashboard
```

**2. Create and activate a virtual environment**
```bash
# Mac/Linux
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up your API key**

Create a `.env` file in the project root:
```
WEATHER_API_KEY=your_openweathermap_api_key_here
```

> Get your free API key at [openweathermap.org](https://openweathermap.org/api). New keys activate within 10–30 minutes.

**5. Run the app**
```bash
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`

---

## Project Structure

```
weather-dashboard/
├── app.py              # Main Streamlit application
├── .env                # API keys (never commit this)
├── .gitignore          # Excludes .env, venv, __pycache__
├── requirements.txt    # Python dependencies
├── weather.db          # SQLite database (auto-created on first run)
└── README.md           # This file
```

---

## How It Works

### Data Flow

```
OpenWeatherMap API
        ↓
  Python (requests)         ← fetches current + forecast JSON
        ↓
  Pandas (transform)        ← cleans, renames, converts units
        ↓
  SQLite (save_search)      ← stores every search automatically
        ↓
  Plotly + Streamlit        ← renders charts and UI
```

### Key Transformations

- Wind speed: `m/s → km/h` (multiply by 3.6)
- Temperature: `Celsius → Fahrenheit` (× 9/5 + 32)
- Visibility: `meters → kilometres` (divide by 1000)
- Wind degrees: `0–360° → compass direction` (N, NE, E...)
- Forecast slots: `40 × 3-hour intervals → 5 daily high/low summaries`

---

## API Usage

This app uses two OpenWeatherMap endpoints:

| Endpoint | Purpose | Free tier limit |
|---|---|---|
| `/data/2.5/weather` | Current conditions | 1,000 calls/day |
| `/data/2.5/forecast` | 5-day forecast | 1,000 calls/day |
| `/geo/1.0/direct` | City search suggestions | 1,000 calls/day |

> Results are cached for 10 minutes using `@st.cache_data` to minimize API usage.

---

## Requirements

```
streamlit>=1.56.0
requests
pandas
plotly
python-dotenv
```

Generate with:
```bash
pip freeze > requirements.txt
```

---

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `WEATHER_API_KEY` | OpenWeatherMap API key | Yes |

---

## Roadmap

- [ ] Switch mock AI insights to real Claude API
- [ ] Deploy to Streamlit Cloud
- [ ] Replace SQLite with PostgreSQL for cloud persistence
- [ ] Add user authentication
- [ ] Add UV index and air quality index
- [ ] Add email alerts for severe weather

---

## Contributing

Pull requests are welcome! For major changes please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- [OpenWeatherMap](https://openweathermap.org) for the free weather API
- [Streamlit](https://streamlit.io) for making Python web apps effortless
- [Plotly](https://plotly.com) for beautiful interactive charts