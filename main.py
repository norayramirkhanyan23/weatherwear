import streamlit as st
import requests
from datetime import datetime

# =====================
# CONFIG
# =====================
# Safely pull the API key from Streamlit Secrets
API_KEY = st.secrets["API_KEY"]

CITIES = [
    "Yerevan", "Gyumri", "Vanadzor", "Vagharshapat",
    "Hrazdan", "Abovyan", "Kapan", "Armavir",
    "Artashat", "Gavar", "Ijevan", "Dilijan",
    "Charentsavan", "Masis", "Sevan", "Ashtarak"
]

# =====================
# STYLE (LAZY & SHARP)
# =====================
st.set_page_config(page_title="WeatherWear", layout="centered")

st.markdown("""
<style>
/* Base */
.stApp {
    background-color: #09090b;
    color: #fafafa;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Sidebar hidden away */
section[data-testid="stSidebar"] {
    background-color: #09090b;
    border-right: 1px solid #27272a;
}

/* Big Button */
.stButton>button {
    background-color: #fafafa;
    color: #09090b;
    border-radius: 30px;
    border: none;
    padding: 12px 24px;
    font-size: 18px;
    font-weight: 600;
    width: 100%;
    margin-top: 10px;
    transition: 0.2s;
}
.stButton>button:active {
    transform: scale(0.98);
}

/* Hide clutter */
footer {visibility: hidden;}
header {visibility: hidden;}

/* Typography */
.huge-temp {
    font-size: 110px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -5px;
    margin-bottom: 10px;
}
.hook-text {
    font-size: 20px;
    font-weight: 600;
    color: #d4d4d8;
    margin-bottom: 4px;
}
.vibe-text {
    font-size: 20px;
    font-weight: 400;
    color: #71717a;
    margin-bottom: 20px;
}
.clothing-item {
    font-size: 32px;
    font-weight: 600;
    letter-spacing: -1px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)


# =====================
# ENGINE
# =====================
@st.cache_data(ttl=600, show_spinner=False)
def get_lazy_weather(city):
    try:
        # 1. Get Coordinates & Current Weather via OWM
        geo = requests.get(
            "http://api.openweathermap.org/geo/1.0/direct",
            params={"q": city + ",AM", "limit": 1, "appid": API_KEY},
            timeout=5
        ).json()

        lat, lon = geo[0]["lat"], geo[0]["lon"]

        current_data = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"},
            timeout=5
        ).json()

        current_feels = int(current_data["main"]["feels_like"])

        # 2. Get Yesterday's Temp via Open-Meteo (Free, no key needed)
        try:
            past_data = requests.get(
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&past_days=1&hourly=temperature_2m",
                timeout=5
            ).json()

            current_hour = datetime.utcnow().hour
            yesterday_temp = past_data["hourly"]["temperature_2m"][current_hour]
        except Exception:
            # Fallback if Open-Meteo fails so the app doesn't break
            yesterday_temp = current_feels - 2

        temp_diff = current_feels - yesterday_temp

        return {
            "feels": current_feels,
            "diff": temp_diff,
            "windy": current_data["wind"]["speed"] > 6,
            "rainy": "Rain" in current_data["weather"][0]["main"],
            "snowy": "Snow" in current_data["weather"][0]["main"]
        }
    except Exception:
        return None


def sharp_translation(weather, cold_level):
    score = weather["feels"] - (cold_level * 0.5)
    diff = weather["diff"]

    # 1. THE HOOK (Comparison)
    if diff <= -5:
        hook = "Noticeably colder than yesterday."
    elif diff <= -2:
        hook = "Colder than yesterday."
    elif diff >= 5:
        hook = "Way warmer than yesterday."
    elif diff >= 2:
        hook = "Warmer than yesterday."
    else:
        hook = "About the same as yesterday."

    # 2. THE VIBE (Human Context - Balanced Tone)
    if score >= 30:
        vibe = "It's very hot outside. Stay cool."
    elif 20 <= score < 30:
        vibe = "It feels pretty much perfect."
    elif 12 <= score < 20:
        vibe = "Crisp and pleasant out."
    elif 5 <= score < 12:
        vibe = "Definitely on the chilly side."
    elif 0 <= score < 5:
        vibe = "It's cold out there. Bundle up."
    else:
        vibe = "It's extremely cold."

    # Add-ons
    if weather["rainy"]:
        vibe += " Also, it's wet out there."
    elif weather["windy"]:
        vibe += " Watch out for the wind."
    elif weather["snowy"]:
        vibe += " Snowing too."

    # 3. OUTFIT DECISION
    if score >= 25:
        outfit = ["T-shirt", "Shorts"]
    elif 18 <= score < 25:
        outfit = ["T-shirt", "Light pants"]
    elif 10 <= score < 18:
        outfit = ["Hoodie", "Jeans"]
    else:
        outfit = ["Heavy Coat", "Warm Layers", "Jeans"]

    if weather["windy"] and score < 20: outfit.append("Windbreaker")
    if weather["rainy"]: outfit.append("Umbrella")
    if weather["snowy"]: outfit.extend(["Beanie", "Gloves"])

    return hook, vibe, outfit


# =====================
# SIDEBAR
# =====================
with st.sidebar:
    st.markdown("### Settings")
    cold_level = st.radio("I get cold...", ["Rarely", "Normally", "Easily"], index=1)

cold_map = {"Rarely": 1, "Normally": 5, "Easily": 9}
cold_value = cold_map[cold_level]

# =====================
# MAIN UI
# =====================
st.markdown("<br><br>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    city = st.selectbox("Where are you?", CITIES, label_visibility="collapsed")
    if st.button("What should I wear?"):
        weather = get_lazy_weather(city)

        if weather:
            hook, vibe, outfit = sharp_translation(weather, cold_value)

            st.markdown("<br>", unsafe_allow_html=True)

            # The readout
            st.markdown(f"<div class='huge-temp'>{weather['feels']}°</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='hook-text'>{hook}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='vibe-text'>{vibe}</div>", unsafe_allow_html=True)

            # Visual separator before outfit
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<hr style='border: 1px solid #27272a; margin-bottom: 25px;'>", unsafe_allow_html=True)

            # The outfit
            for item in outfit:
                st.markdown(f"<div class='clothing-item'>+ {item}</div>", unsafe_allow_html=True)
        else:
            st.error("Couldn't look out the window. Try again.")