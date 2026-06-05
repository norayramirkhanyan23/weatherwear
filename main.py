import streamlit as st
import requests
from datetime import datetime
import google.generativeai as genai
from PIL import Image
from bs4 import BeautifulSoup
import json
import sqlite3
import bcrypt
import pandas as pd
import time

# =====================
# CONFIG
# =====================
API_KEY = st.secrets["API_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
HF_TOKEN = st.secrets["HF_TOKEN"]

genai.configure(api_key=GEMINI_API_KEY)

# =====================
# PAGE SETUP
# =====================
st.set_page_config(
    page_title="AI Personal Stylist | WeatherWear",
    page_icon="⛅",
    layout="wide"
)

# =====================
# SESSION STATE INIT
# =====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "styling_data" not in st.session_state:
    st.session_state.styling_data = None
if "travel_data" not in st.session_state:
    st.session_state.travel_data = None

# =====================
# DATABASE ENGINE
# =====================
def init_db():
    conn = sqlite3.connect("weatherwear.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, cold_pref TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS wardrobe
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT, name TEXT, type TEXT, color TEXT, fabric TEXT, formality TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT, date TEXT, location TEXT, temp INTEGER, condition TEXT,
                 outfit_details TEXT, match_score INTEGER, comfort_score INTEGER,
                 weather_score INTEGER, style_score INTEGER)''')
    conn.commit()
    conn.close()


def create_user(username, password):
    conn = sqlite3.connect("weatherwear.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    if c.fetchone():
        conn.close()
        return False
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    c.execute("INSERT INTO users (username, password, cold_pref) VALUES (?, ?, ?)",
              (username, hashed.decode('utf-8'), "Balanced"))
    conn.commit()
    conn.close()
    return True


def verify_login(username, password):
    conn = sqlite3.connect("weatherwear.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    if result and bcrypt.checkpw(password.encode('utf-8'), result[0].encode('utf-8')):
        return True
    return False


def get_user_wardrobe(username):
    conn = sqlite3.connect("weatherwear.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT name, type, color, fabric, formality FROM wardrobe WHERE username=?", (username,))
    clothes = [{"name": row["name"], "type": row["type"], "color": row["color"],
                "fabric": row["fabric"], "formality": row["formality"]} for row in c.fetchall()]
    conn.close()
    return clothes


def add_clothing_to_db(username, name, clothing_type, color, fabric, formality):
    conn = sqlite3.connect("weatherwear.db")
    c = conn.cursor()
    c.execute("INSERT INTO wardrobe (username, name, type, color, fabric, formality) VALUES (?, ?, ?, ?, ?, ?)",
              (username, name, clothing_type, color, fabric, formality))
    conn.commit()
    conn.close()


def clear_user_wardrobe(username):
    conn = sqlite3.connect("weatherwear.db")
    c = conn.cursor()
    c.execute("DELETE FROM wardrobe WHERE username=?", (username,))
    conn.commit()
    conn.close()


def update_user_pref(username, pref):
    conn = sqlite3.connect("weatherwear.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cold_pref=? WHERE username=?", (pref, username))
    conn.commit()
    conn.close()


def get_user_pref(username):
    conn = sqlite3.connect("weatherwear.db")
    c = conn.cursor()
    c.execute("SELECT cold_pref FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "Balanced"


def save_outfit_history(username, location, temp, condition, outfit, scores):
    conn = sqlite3.connect("weatherwear.db")
    c = conn.cursor()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    outfit_str = ", ".join(outfit)
    c.execute("""INSERT INTO history
                 (username, date, location, temp, condition, outfit_details, match_score, comfort_score, weather_score, style_score)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (username, date_str, location, temp, condition, outfit_str,
               scores.get("match", 0), scores.get("comfort", 0), scores.get("weather", 0), scores.get("style", 0)))
    conn.commit()
    conn.close()


def get_user_history(username):
    conn = sqlite3.connect("weatherwear.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM history WHERE username=? ORDER BY id DESC", (username,))
    history = [dict(row) for row in c.fetchall()]
    conn.close()
    return history


init_db()
# Ensure Guest account exists
try:
    conn = sqlite3.connect("weatherwear.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", ("Guest",))
    if not c.fetchone():
        hashed = bcrypt.hashpw("guest_pass_ww".encode('utf-8'), bcrypt.gensalt())
        c.execute("INSERT INTO users (username, password, cold_pref) VALUES (?, ?, ?)",
                  ("Guest", hashed.decode('utf-8'), "Balanced"))
        conn.commit()
    conn.close()
except Exception:
    pass

# =====================
# DYNAMIC CSS ENGINE
# =====================
def get_weather_css(condition):
    cond = condition.lower()
    if "clear" in cond or "sun" in cond:
        return "radial-gradient(circle at top left, #3d240e, #09090b) !important;"
    elif "rain" in cond or "drizzle" in cond or "thunder" in cond:
        return "radial-gradient(circle at top left, #0e1b2b, #09090b) !important;"
    elif "snow" in cond:
        return "radial-gradient(circle at top left, #1a2a3a, #09090b) !important;"
    else:
        return "radial-gradient(circle at top left, #1c1c1f, #09090b) !important;"


# =====================
# STYLE
# =====================
st.markdown("""
<style>
.stApp {
    background-color: #09090b;
    color: #fafafa;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    transition: background 0.5s ease;
}
section[data-testid="stSidebar"] {
    background-color: #0f0f13;
    border-right: 1px solid #27272a;
}
footer { visibility: hidden; }
header { visibility: hidden; }
.stButton>button {
    background-color: #fafafa;
    color: #09090b;
    border-radius: 18px;
    border: none;
    padding: 14px 24px;
    font-size: 16px;
    font-weight: 600;
    width: 100%;
}
.stButton>button:hover { background-color: #e4e4e7; }
.huge-temp { font-size: 120px; font-weight: 700; line-height: 1; letter-spacing: -6px; }
.hook { font-size: 28px; font-weight: 600; margin-top: 10px; }
.vibe { font-size: 20px; color: #a1a1aa; margin-top: 10px; }
.forecast { font-size: 16px; color: #71717a; margin-top: 16px; }
.outfit-card {
    background-color: rgba(17, 24, 39, 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid #27272a;
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 14px;
    font-size: 22px;
    font-weight: 600;
}
.forecast-card {
    background-color: rgba(17, 24, 39, 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid #27272a;
    border-radius: 18px;
    padding: 18px;
    text-align: center;
    min-height: 170px;
    margin-bottom: 18px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.forecast-highlight-best { border: 2px solid #4ade80 !important; background-color: rgba(74, 222, 128, 0.1) !important; }
.forecast-highlight-worst { border: 2px solid #f87171 !important; background-color: rgba(248, 113, 113, 0.1) !important; }
.forecast-highlight-rain { border: 2px solid #60a5fa !important; background-color: rgba(96, 165, 250, 0.1) !important; }
.forecast-day { font-size: 18px; font-weight: 600; margin-bottom: 10px; }
.forecast-temp { font-size: 32px; font-weight: 700; }
.forecast-min-temp { font-size: 16px; color: #71717a; }
.forecast-condition { color: #a1a1aa; margin-top: 10px; }
.travel-box {
    background-color: rgba(17, 24, 39, 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid #27272a;
    border-radius: 20px;
    padding: 28px;
    margin-top: 20px;
}
.small-label { color: #71717a; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
.auth-box {
    background-color: #111827;
    padding: 40px;
    border-radius: 20px;
    border: 1px solid #27272a;
    max-width: 420px;
    margin: 0 auto;
    margin-top: 10vh;
}
.tag-pill {
    display: inline-block; background-color: #27272a; color: #d4d4d8;
    font-size: 12px; padding: 2px 8px; border-radius: 10px; margin-right: 6px; margin-top: 6px;
}
.metric-label { font-size: 14px; color: #a1a1aa; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
.metric-value { font-size: 32px; font-weight: 700; margin-bottom: 8px; }
img { border-radius: 14px; }
</style>
""", unsafe_allow_html=True)

# =====================
# AUTHENTICATION UI
# =====================
if not st.session_state.logged_in:
    st.markdown("<div class='auth-box'>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>⛅ WeatherWear</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#a1a1aa;'>AI Personal Stylist powered by Weather Intelligence</p>",
                unsafe_allow_html=True)

    auth_tab1, auth_tab2 = st.tabs(["Log In", "Sign Up"])

    with auth_tab1:
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In"):
            if verify_login(login_user, login_pass):
                st.session_state.logged_in = True
                st.session_state.username = login_user
                st.session_state.styling_data = None
                st.session_state.travel_data = None
                st.rerun()
            else:
                st.error("Incorrect username or password.")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Continue as Guest"):
            st.session_state.logged_in = True
            st.session_state.username = "Guest"
            st.session_state.styling_data = None
            st.session_state.travel_data = None
            st.rerun()

    with auth_tab2:
        reg_user = st.text_input("Choose Username", key="reg_user")
        reg_pass = st.text_input("Choose Password", type="password", key="reg_pass")
        if st.button("Sign Up"):
            if reg_user and len(reg_pass) >= 4:
                if create_user(reg_user, reg_pass):
                    st.success("Account created! You can now log in.")
                else:
                    st.error("Username already exists.")
            else:
                st.error("Please enter a username and a password (min 4 chars).")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# =====================
# LOAD USER DATA
# =====================
current_user = st.session_state.username
user_wardrobe = get_user_wardrobe(current_user)
saved_pref = get_user_pref(current_user)


# =====================
# WEATHER ENGINE
# =====================
@st.cache_data(ttl=600)
def get_lazy_weather(city):
    try:
        geo = requests.get(
            "http://api.openweathermap.org/geo/1.0/direct",
            params={"q": city, "limit": 1, "appid": API_KEY}
        ).json()
        if not geo or (isinstance(geo, dict) and "message" in geo):
            return None
        lat, lon = geo[0]["lat"], geo[0]["lon"]
        current = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"}
        ).json()
        feels = int(current["main"]["feels_like"])
        try:
            past = requests.get(
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&past_days=1&hourly=temperature_2m"
            ).json()
            hour = datetime.utcnow().hour
            yesterday = past["hourly"]["temperature_2m"][hour]
        except Exception:
            yesterday = feels - 2
        return {
            "temp": feels, "diff": round(feels - yesterday, 1),
            "condition": current["weather"][0]["main"],
            "humidity": current["main"]["humidity"],
            "wind": current["wind"]["speed"],
            "rainy": "Rain" in current["weather"][0]["main"],
            "snowy": "Snow" in current["weather"][0]["main"],
            "windy": current["wind"]["speed"] > 6,
            "lat": lat, "lon": lon
        }
    except Exception:
        return None


def tomorrow_vibe(lat, lon):
    try:
        data = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"lat": lat, "lon": lon, "appid": API_KEY, "units": "metric"}
        ).json()
        temps = [x["main"]["temp"] for x in data["list"][:8]]
        today = temps[0]
        tomorrow = sum(temps[1:]) / len(temps[1:])
        if tomorrow > today + 2:
            return "Tomorrow feels warmer — consider lighter layers."
        elif tomorrow < today - 2:
            return "Tomorrow feels colder — keep a layer handy."
        else:
            return "Tomorrow feels similar to today."
    except Exception:
        return None


@st.cache_data(ttl=1800)
def get_forecast(lat, lon):
    try:
        data = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,weathercode,precipitation_probability_max",
                "forecast_days": 15, "timezone": "auto"
            }
        ).json()
        dates = data["daily"]["time"]
        temps_max = data["daily"]["temperature_2m_max"]
        temps_min = data["daily"]["temperature_2m_min"]
        codes = data["daily"]["weathercode"]
        precip = data["daily"]["precipitation_probability_max"]
        forecast = []
        for i in range(len(dates)):
            code = codes[i]
            if code == 0:
                condition = "Clear"
            elif code in [1, 2, 3]:
                condition = "Cloudy"
            elif code in [61, 63, 65, 80, 81, 82]:
                condition = "Rain"
            elif code in [71, 73, 75]:
                condition = "Snow"
            else:
                condition = "Mixed"
            forecast.append({
                "day": datetime.strptime(dates[i], "%Y-%m-%d").strftime("%a"),
                "date_raw": dates[i],
                "temp_max": int(temps_max[i]),
                "temp_min": int(temps_min[i]),
                "condition": condition,
                "precip": precip[i]
            })
        return forecast
    except Exception:
        return []


# =====================
# AI HELPERS
# =====================
def _clean_json(text):
    """Strip markdown fences and return clean JSON text."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[-1] if text.count("```") >= 2 else text
        text = text.lstrip("json").strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return text


def _call_gemini_with_retry(prompt, retries=3, model_name="gemini-1.5-flash"):
    model = genai.GenerativeModel(model_name)
    last_err = None
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            raw = _clean_json(response.text)
            return json.loads(raw)
        except json.JSONDecodeError as e:
            last_err = e
            time.sleep(1)
        except Exception as e:
            last_err = e
            time.sleep(1.5)
    raise last_err


# =====================
# AI WARDROBE ENGINES
# =====================
@st.cache_resource
def load_fashion_model():
    """Load the local RandomForest fashion classifier."""
    import pickle
    try:
        with open("fashion_classifier.pkl", "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def _local_classify_image(img: Image.Image):
    """
    Run the local ML model to predict clothing type, color, and formality.
    Returns a dict with type, color, formality — or None if model unavailable.
    """
    try:
        import sys, os
        # Allow importing helper modules from same directory
        bundle = load_fashion_model()
        if bundle is None:
            return None

        from fashion_model import extract_image_features
        from color_detector import detect_dominant_color

        features = extract_image_features(img).reshape(1, -1)

        clothing_type = bundle["type_encoder"].inverse_transform(
            bundle["type_clf"].predict(features)
        )[0]
        formality = bundle["formality_encoder"].inverse_transform(
            bundle["formality_clf"].predict(features)
        )[0]
        color = detect_dominant_color(img)

        return {"type": clothing_type, "color": color, "formality": formality}
    except Exception:
        return None


def analyze_clothing_image(uploaded_file):
    try:
        img = Image.open(uploaded_file)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((512, 512))

        # Step 1: Run local ML model for type, color, formality
        local_result = _local_classify_image(img)

        if local_result:
            # Step 2: Ask Gemini only for fabric + name (what local ML can't do)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"""A local fashion classifier has already detected:
- Clothing type: {local_result['type']}
- Dominant color: {local_result['color']}
- Formality level: {local_result['formality']}

Your job: Look at this clothing image and provide ONLY the two missing fields.
Return ONLY a valid JSON object (no markdown, no backticks) with exactly these two keys:
- "name": A short stylish product name combining the color and type (e.g., "{local_result['color']} {local_result['type']}")
- "fabric": The most likely material (e.g., "Cotton", "Wool", "Denim", "Leather", "Polyester", "Linen")"""

            response = model.generate_content([prompt, img])
            gemini_result = json.loads(_clean_json(response.text))

            return {
                "name": gemini_result.get("name", f"{local_result['color']} {local_result['type']}"),
                "type": local_result["type"],
                "color": local_result["color"],
                "fabric": gemini_result.get("fabric", "Unknown"),
                "formality": local_result["formality"],
            }
        else:
            # Full Gemini fallback if model file not found
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = """Analyze this clothing item. Return ONLY a valid JSON object (no markdown, no backticks) with:
- "name": Short stylish name
- "type": One of: T-Shirt, Hoodie, Jacket, Jeans, Shorts, Coat, Sweater, Shirt, Trousers, Accessories
- "color": Dominant color
- "fabric": Likely material
- "formality": One of: Casual, Smart-Casual, Business, Formal"""
            response = model.generate_content([prompt, img])
            return json.loads(_clean_json(response.text))

    except Exception as e:
        st.error(f"Could not analyze the image: {str(e)}")
        return None


def analyze_clothing_link(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        page = requests.get(url, headers=headers, timeout=6)
        soup = BeautifulSoup(page.content, "html.parser")
        title = soup.title.string if soup.title else "Unknown Item"
        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc = meta_desc["content"] if meta_desc else ""
        scraped_text = f"Title: {title}\nDescription: {desc}"
        prompt = f"""Analyze this clothing product webpage data. Return ONLY a valid JSON object (no markdown, no backticks) with these exact keys:
- "name": Clean short name (e.g., "Zara Puffer Coat")
- "type": One of: T-Shirt, Hoodie, Jacket, Jeans, Shorts, Coat, Sweater, Shirt, Trousers, Accessories
- "color": Dominant color
- "fabric": Primary material (e.g., "Cotton", "Wool", "Blend")
- "formality": One of: Casual, Smart-Casual, Business, Formal

Data to analyze:
{scraped_text}"""
        return _call_gemini_with_retry(prompt)
    except Exception as e:
        st.error(f"Could not scrape or analyze that link: {str(e)}")
        return None


def weather_ai(weather, cold_level, wardrobe, activity_formality, style_preference):
    if cold_level >= 9:
        preference = "Runs hot — prefers lighter clothes even in cool weather"
    elif cold_level <= 1:
        preference = "Runs cold — needs extra layers, gets chilly easily"
    else:
        preference = "Balanced — standard temperature preference"

    if wardrobe:
        wardrobe_text = "\n".join([
            f"- '{item['name']}' (Color: {item['color']}, Fabric: {item['fabric']}, "
            f"Type: {item['type']}, Formality: {item['formality']})"
            for item in wardrobe
        ])
    else:
        wardrobe_text = "No clothes uploaded yet. Suggest general clothing types appropriate for the weather."

    prompt = f"""You are an elite AI personal stylist with deep knowledge of layering theory, fabric science, and climate dressing.

Current Live Weather:
- Temperature (feels like): {weather['temp']}°C
- Condition: {weather['condition']}
- Wind Speed: {weather['wind']} m/s
- Raining: {weather['rainy']}
- Snowing: {weather['snowy']}
- Temp difference from yesterday: {weather['diff']}°C

User Profile:
- Body Temperature Preference: {preference}
- Style Identity: {style_preference}
- Target Formality: {activity_formality}

User's Wardrobe:
{wardrobe_text}

Task: Select the best outfit using layering logic. Factor in fabric warmth, breathability, and target formality. If the wardrobe is empty, suggest ideal generic pieces.

Return ONLY a valid JSON object (no markdown, no backticks) with these exact keys:
- "hook": A punchy 3–6 word headline comparing today's feel to yesterday (e.g., "Crisper than yesterday's warmth")
- "vibe": A friendly 2–3 sentence paragraph explaining your outfit choice and why it works for this weather
- "outfit": A list of strings — the names of the selected items (from wardrobe or generic suggestions)
- "scores": A dict with four integer keys (0–100): "match", "comfort", "weather", "style"
"""
    try:
        data = _call_gemini_with_retry(prompt)
        return (
            data.get("hook", "Weather analyzed."),
            data.get("vibe", "Dress comfortably for the conditions!"),
            data.get("outfit", ["Base Layer", "Pants", "Outerwear"]),
            data.get("scores", {"match": 80, "comfort": 80, "weather": 80, "style": 80})
        )
    except Exception:
        return (
            "Weather analyzed.",
            "Look at the temperature and dress comfortably for your day!",
            ["Base Layer", "Pants", "Outerwear"],
            {"match": 0, "comfort": 0, "weather": 0, "style": 0}
        )


def travel_ai(weather, cold_level, wardrobe, dest, days, activities, style_preference):
    preference = "Runs hot" if cold_level >= 9 else "Runs cold" if cold_level <= 1 else "Balanced"
    wardrobe_text = "\n".join([
        f"- '{item['name']}' (Color: {item['color']}, Fabric: {item['fabric']}, "
        f"Type: {item['type']}, Formality: {item['formality']})"
        for item in wardrobe
    ]) if wardrobe else "Empty closet."

    activities_str = ", ".join(activities) if activities else "General sightseeing"

    prompt = f"""You are an elite AI travel stylist.

Trip Details:
- Destination: {dest}
- Duration: {days} days
- Planned Activities: {activities_str}

Destination Weather:
- Temperature: {weather['temp']}°C
- Condition: {weather['condition']}
- Wind: {weather['wind']} m/s
- Raining: {weather['rainy']}

User Profile:
- Thermal Preference: {preference}
- Style Identity: {style_preference}

User's Wardrobe:
{wardrobe_text}

Task: Create a packing list using items FROM their wardrobe. Identify missing essentials they should acquire.

Return ONLY a valid JSON object (no markdown, no backticks) with these exact keys:
- "hook": A short punchy headline for the trip (e.g., "Tokyo in the Rain: Layered & Ready")
- "packing_list": List of strings referencing wardrobe items to pack
- "missing_items": List of strings for essentials not in their wardrobe (e.g., "No waterproof jacket for rainy conditions")
- "readiness_score": Integer 0–100 indicating closet readiness for this trip
- "score_explanation": 1–2 sentence explanation of the readiness score
- "activity_tips": List of 2–3 short styling tips for their specific activities
"""
    try:
        return _call_gemini_with_retry(prompt)
    except Exception:
        return {
            "hook": "Trip Blueprint Generated",
            "packing_list": ["Versatile Outfits", "Comfortable Shoes"],
            "missing_items": [],
            "readiness_score": 50,
            "score_explanation": "Unable to run deep analysis. Add items to your closet for better results.",
            "activity_tips": ["Layering is always a safe bet!", "Pack versatile neutral colors."]
        }


def analytics_ai(wardrobe):
    wardrobe_text = "\n".join([
        f"- '{item['name']}' (Type: {item['type']}, Fabric: {item['fabric']}, Formality: {item['formality']})"
        for item in wardrobe
    ]) if wardrobe else "Empty closet."

    prompt = f"""You are an AI wardrobe analyst specializing in capsule wardrobes and climate dressing.

User's Closet:
{wardrobe_text}

Task: Analyze this wardrobe for completeness across all seasons and occasions. Identify gaps and provide strategic advice.

Return ONLY a valid JSON object (no markdown, no backticks) with these exact keys:
- "seasonal_readiness": Integer 0–100 indicating overall seasonal preparedness
- "missing_essentials": List of 3–5 critical items missing (e.g., "Waterproof outer layer for rain", "Formal shoes for business events")
- "suggestions": A 2–3 sentence strategic paragraph on how to improve this wardrobe
"""
    try:
        return _call_gemini_with_retry(prompt)
    except Exception:
        return {
            "seasonal_readiness": 0,
            "missing_essentials": ["Unable to analyze — add items to your closet"],
            "suggestions": "Add more items to your closet to receive a personalized wardrobe analysis."
        }


# =====================
# SIDEBAR
# =====================
with st.sidebar:
    st.markdown("### 🌤️ WeatherWear")
    if current_user == "Guest":
        st.markdown("<small style='color:#71717a;'>Browsing as Guest</small>", unsafe_allow_html=True)
    else:
        st.markdown(f"<small style='color:#71717a;'>👋 {current_user}</small>", unsafe_allow_html=True)

    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.styling_data = None
        st.session_state.travel_data = None
        st.rerun()

    st.markdown("---")
    st.markdown("## Style Preferences")

    style_pref = st.selectbox("Style Identity", ["Menswear", "Womenswear", "Unisex / Androgynous"])
    cold_pref = st.select_slider("Body Temp Preference", options=["Warm", "Balanced", "Cold"], value=saved_pref)
    if cold_pref != saved_pref:
        update_user_pref(current_user, cold_pref)
    day_formality = st.selectbox("Target Formality", ["Casual", "Smart-Casual", "Business", "Formal"])

    st.markdown("---")
    st.markdown("## Manage Closet")

    if st.button("✨ Load AI Test Wardrobe"):
        demo_items = [
            ("Black Leather Jacket", "Jacket", "Black", "Leather", "Smart-Casual"),
            ("Classic Blue Jeans", "Jeans", "Blue", "Denim", "Casual"),
            ("White Linen Shirt", "Shirt", "White", "Linen", "Smart-Casual"),
            ("Grey Cashmere Sweater", "Sweater", "Grey", "Wool", "Business"),
            ("Dark Navy Suit Trousers", "Trousers", "Navy", "Wool", "Formal"),
            ("Yellow Puffer Coat", "Coat", "Yellow", "Polyester", "Casual"),
            ("Basic Black T-Shirt", "T-Shirt", "Black", "Cotton", "Casual"),
        ]
        clear_user_wardrobe(current_user)
        for item in demo_items:
            add_clothing_to_db(current_user, item[0], item[1], item[2], item[3], item[4])
        st.toast("✅ AI Test Wardrobe loaded!", icon="👕")
        st.rerun()

    img_tab, link_tab = st.tabs(["Upload Photo", "Paste Link"])

    with img_tab:
        uploaded_file = st.file_uploader("Upload clothes", type=["png", "jpg", "jpeg"])
        if uploaded_file and st.button("Add via Image"):
            with st.spinner("AI is analyzing fabric and color..."):
                ai_data = analyze_clothing_image(uploaded_file)
                if ai_data:
                    add_clothing_to_db(current_user, ai_data.get("name", "Item"), ai_data.get("type", "Misc"),
                                       ai_data.get("color", "Mixed"), ai_data.get("fabric", "Unknown"),
                                       ai_data.get("formality", "Casual"))
                    st.toast(f"👕 {ai_data.get('name', 'Item')} added to your closet!", icon="✅")
                    st.rerun()

    with link_tab:
        clothing_url = st.text_input("Paste store link (ASOS, Zara, etc.)")
        if clothing_url and st.button("Add via Link"):
            with st.spinner("AI is reading the website details..."):
                ai_data = analyze_clothing_link(clothing_url)
                if ai_data:
                    add_clothing_to_db(current_user, ai_data.get("name", "Item"), ai_data.get("type", "Misc"),
                                       ai_data.get("color", "Mixed"), ai_data.get("fabric", "Unknown"),
                                       ai_data.get("formality", "Casual"))
                    st.toast(f"👕 {ai_data.get('name', 'Item')} added to your closet!", icon="✅")
                    st.rerun()

    st.markdown("---")
    st.markdown("### Your Active Closet")
    if not user_wardrobe:
        st.info("Your closet is empty. Add items to enable weather matching!")
    else:
        for item in user_wardrobe:
            st.markdown(
                f"""<div style="background-color: #111827; padding: 12px; border-radius: 12px; margin-bottom: 8px; border: 1px solid #27272a;">
                    <strong>{item['name']}</strong><br>
                    <span class="tag-pill">{item['type']}</span>
                    <span class="tag-pill">{item['fabric']}</span>
                    <span class="tag-pill">{item['formality']}</span>
                </div>""",
                unsafe_allow_html=True
            )
        if st.button("Clear Closet"):
            clear_user_wardrobe(current_user)
            st.rerun()

cold_map = {"Warm": 9, "Balanced": 5, "Cold": 1}
cold_value = cold_map[cold_pref]

# =====================
# TABS
# =====================
tab1, tab2, tab3, tab4 = st.tabs([
    "⛅ Daily Stylist",
    "✈️ Travel Concierge",
    "📊 Wardrobe Analytics",
    "📖 Styling History"
])

# =====================================================
# DAILY STYLIST TAB
# =====================================================
with tab1:
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center;'>WeatherWear Studio</h1>", unsafe_allow_html=True)
        city = st.text_input("Where are you?", "Yerevan")

        if st.button("Generate Outfit Recommendation"):
            weather = get_lazy_weather(city)
            if weather:
                with st.status("🤖 Analyzing weather and assembling your outfit...", expanded=True) as status:
                    st.write("📡 Fetching live atmospheric data...")
                    st.write(f"👕 Cross-referencing {len(user_wardrobe)} closet items with current conditions...")
                    st.write("🧠 Applying layering logic and style constraints...")
                    hook, vibe, outfit, scores = weather_ai(weather, cold_value, user_wardrobe, day_formality, style_pref)
                    forecast_vibe = tomorrow_vibe(weather["lat"], weather["lon"])
                    forecast_data = get_forecast(weather["lat"], weather["lon"])
                    status.update(label="✅ Outfit Ready!", state="complete", expanded=False)

                st.session_state.styling_data = {
                    "weather": weather, "hook": hook, "vibe": vibe, "outfit": outfit,
                    "scores": scores, "forecast": forecast_vibe, "forecast_data": forecast_data,
                    "city": city
                }
                if outfit:
                    save_outfit_history(current_user, city, weather["temp"], weather["condition"], outfit, scores)
            else:
                st.error("Couldn't retrieve weather for that location. Please check the city name.")

    if st.session_state.styling_data:
        data = st.session_state.styling_data
        weather = data["weather"]
        scores = data["scores"]

        bg_css = get_weather_css(weather["condition"])
        st.markdown(f"<style>.stApp {{ background: {bg_css} }}</style>", unsafe_allow_html=True)

        icon = "☂" if weather["rainy"] else "❄" if weather["snowy"] else "☼" if weather["windy"] else "☀"

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<div class='huge-temp'>{icon} {weather['temp']}°</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='hook'>{data['hook']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='vibe'>{data['vibe']}</div>", unsafe_allow_html=True)
        if data["forecast"]:
            st.markdown(f"<div class='forecast'>{data['forecast']}</div>", unsafe_allow_html=True)
        st.markdown("<br><hr>", unsafe_allow_html=True)

        st.markdown("### Weather Suitability & Style Metrics")
        sc1, sc2, sc3, sc4 = st.columns(4)
        metric_defs = [("Outfit Match", "match"), ("Comfort", "comfort"), ("Weather Defense", "weather"), ("Style", "style")]
        for col, (title, key) in zip([sc1, sc2, sc3, sc4], metric_defs):
            with col:
                st.markdown(f"<div class='metric-label'>{title}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='metric-value'>{scores.get(key, 0)}/100</div>", unsafe_allow_html=True)
                st.progress(scores.get(key, 0) / 100)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### AI Recommended Layers")
        for item in data["outfit"]:
            st.markdown(f"<div class='outfit-card'>✧ {item}</div>", unsafe_allow_html=True)

        with st.popover("⚙️ Technical Weather Stats"):
            st.metric("Humidity", f"{weather['humidity']}%")
            st.metric("Wind Speed", f"{weather['wind']} m/s")
            st.metric("Temp Diff vs Yesterday", f"{weather['diff']}°C")

        with st.expander("📅 Extended Weather Forecast"):
            forecast_choice = st.selectbox("Forecast Length", ["7 Days", "15 Days"])
            days_to_show = 15 if forecast_choice == "15 Days" else 7
            f_data = data["forecast_data"]

            if f_data:
                valid_data = f_data[:days_to_show]
                best_day = min(valid_data, key=lambda x: abs(x["temp_max"] - 22) + x["precip"])
                worst_day = max(valid_data, key=lambda x: abs(x["temp_max"] - 22) + x["precip"])
                rainiest_day = max(valid_data, key=lambda x: x["precip"])

                for row_start in range(0, len(valid_data), 5):
                    cols = st.columns(5)
                    for i in range(5):
                        idx = row_start + i
                        if idx >= len(valid_data):
                            break
                        day = valid_data[idx]
                        day_icon = "☂" if day["condition"] == "Rain" else "❄" if day["condition"] == "Snow" else "☁" if day["condition"] == "Cloudy" else "☀"

                        c_class, badge = "forecast-card", ""
                        if day == best_day:
                            c_class, badge = "forecast-card forecast-highlight-best", "<div class='tag-pill' style='background: #4ade80; color: #000;'>Best Day</div>"
                        elif day == rainiest_day and day["precip"] > 20:
                            c_class, badge = "forecast-card forecast-highlight-rain", "<div class='tag-pill' style='background: #60a5fa; color: #000;'>Rainiest</div>"
                        elif day == worst_day:
                            c_class, badge = "forecast-card forecast-highlight-worst", "<div class='tag-pill' style='background: #f87171; color: #000;'>Extreme</div>"

                        with cols[i]:
                            st.markdown(f"""
<div class="{c_class}">
{badge}
<div class="forecast-day" style="margin-top:8px;">{day['day']}</div>
<div class="forecast-temp">{day['temp_max']}°</div>
<div class="forecast-min-temp">Min {day['temp_min']}°</div>
<div style="font-size:40px; margin-top:10px;">{day_icon}</div>
<div class="forecast-condition">{day['condition']}</div>
</div>
""", unsafe_allow_html=True)
            else:
                st.info("Forecast data unavailable.")

# =====================================================
# TRAVEL CONCIERGE TAB
# =====================================================
with tab2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>Travel Concierge</h1>", unsafe_allow_html=True)

    c_tr1, c_tr2, c_tr3 = st.columns(3)
    with c_tr1:
        start_city = st.text_input("Starting point", "Yerevan", key="travel_start")
    with c_tr2:
        destination = st.text_input("Destination", "Tokyo", key="travel_dest")
    with c_tr3:
        trip_days = st.slider("Trip length (days)", 1, 30, 5)

    activities = st.multiselect(
        "What will you do?",
        ["Walking", "Business", "Nightlife", "Hiking", "Beach", "Photography", "Fine Dining", "Shopping"]
    )

    if st.button("Analyze Trip & Generate Packing List"):
        home_weather = get_lazy_weather(start_city)
        travel_weather = get_lazy_weather(destination)
        if travel_weather and home_weather:
            with st.status("🧳 Analyzing destination weather and your closet...", expanded=True) as t_status:
                st.write(f"🌍 Fetching weather for {destination}...")
                st.write(f"👗 Matching {len(user_wardrobe)} wardrobe items to your trip...")
                st.write("📋 Generating packing list and gap analysis...")
                t_res = travel_ai(travel_weather, cold_value, user_wardrobe, destination, trip_days, activities, style_pref)
                t_status.update(label="✅ Packing List Ready!", state="complete", expanded=False)
            st.session_state.travel_data = {"res": t_res, "weather": travel_weather}
        else:
            st.error("Couldn't retrieve weather for this trip. Please check city names.")

    if st.session_state.travel_data:
        t_res = st.session_state.travel_data["res"]
        t_weather = st.session_state.travel_data["weather"]

        bg_css = get_weather_css(t_weather["condition"])
        st.markdown(f"<style>.stApp {{ background: {bg_css} }}</style>", unsafe_allow_html=True)

        st.markdown("<br><div class='travel-box'>", unsafe_allow_html=True)
        top_col1, top_col2 = st.columns([3, 1])
        with top_col1:
            st.markdown(f"<div class='small-label'>{destination.upper()} • {trip_days} DAYS</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='hook'>{t_res.get('hook', 'Your Trip Blueprint')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='vibe'>{t_res.get('score_explanation', '')}</div>", unsafe_allow_html=True)
        with top_col2:
            score = t_res.get("readiness_score", 0)
            st.markdown("<div class='metric-label'>Packing Readiness</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='huge-temp' style='font-size:48px;'>{score}/100</div>", unsafe_allow_html=True)
            st.progress(score / 100)

        st.markdown("<br>", unsafe_allow_html=True)
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            st.markdown("### 🧳 Pack From Your Closet")
            for item in t_res.get("packing_list", []):
                st.markdown(f"<div class='outfit-card'>✓ {item}</div>", unsafe_allow_html=True)
        with p_col2:
            st.markdown("### 🛒 Missing Essentials")
            if not t_res.get("missing_items"):
                st.success("Your closet is perfectly equipped for this trip!")
            else:
                for item in t_res.get("missing_items", []):
                    st.markdown(f"<div class='outfit-card' style='border-color: #ef4444; color: #fca5a5;'>✗ {item}</div>", unsafe_allow_html=True)

        if t_res.get("activity_tips"):
            with st.popover("💡 Activity & Style Notes"):
                for tip in t_res.get("activity_tips", []):
                    st.markdown(f"<div class='vibe'>• {tip}</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# WARDROBE ANALYTICS TAB
# =====================================================
with tab3:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>Wardrobe Intelligence</h1>", unsafe_allow_html=True)

    if not user_wardrobe:
        st.info("Upload items to your closet to view analytics.")
    else:
        df = pd.DataFrame(user_wardrobe)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Items", len(df))
        m2.metric("Most Common Type", df["type"].mode()[0] if not df.empty else "N/A")
        m3.metric("Dominant Color", df["color"].mode()[0] if not df.empty else "N/A")
        m4.metric("Primary Fabric", df["fabric"].mode()[0] if not df.empty else "N/A")

        st.markdown("<br><hr><br>", unsafe_allow_html=True)

        chart1, chart2 = st.columns(2)
        with chart1:
            st.markdown("### Category Breakdown")
            st.bar_chart(df["type"].value_counts())
        with chart2:
            st.markdown("### Formality Spectrum")
            st.bar_chart(df["formality"].value_counts())

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### AI Closet Gap Analysis")

        with st.spinner("Running deep closet inspection..."):
            analytics_data = analytics_ai(user_wardrobe)

        g1, g2 = st.columns([1, 2])
        with g1:
            st.markdown("<div class='travel-box' style='text-align:center;'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Seasonal Readiness Score</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='huge-temp' style='font-size:72px;'>{analytics_data.get('seasonal_readiness', 0)}</div>",
                unsafe_allow_html=True
            )
            st.progress(analytics_data.get("seasonal_readiness", 0) / 100)
            st.markdown("</div>", unsafe_allow_html=True)
        with g2:
            st.markdown("<div class='travel-box'>", unsafe_allow_html=True)
            st.markdown("#### 🎯 Stylist Suggestions")
            st.markdown(f"<div class='vibe'>{analytics_data.get('suggestions', '')}</div>", unsafe_allow_html=True)
            st.markdown("<br>")
            st.markdown("#### 🛒 Missing Essentials")
            for item in analytics_data.get("missing_essentials", []):
                st.markdown(f"- {item}")
            st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# STYLING HISTORY TAB
# =====================================================
with tab4:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>Styling Archive</h1>", unsafe_allow_html=True)

    user_history = get_user_history(current_user)

    if not user_history:
        st.info("No styling history found. Generate outfits in the Daily Stylist tab to build your archive.")
    else:
        for entry in user_history:
            with st.expander(f"🗓️ {entry['date']} • {entry['location']} ({entry['temp']}°C, {entry['condition']})"):
                h_col1, h_col2 = st.columns([2, 1])
                with h_col1:
                    st.markdown("**Outfit Selected:**")
                    outfit_list = entry["outfit_details"].split(", ")
                    for item in outfit_list:
                        st.markdown(f"✧ {item}")
                with h_col2:
                    st.markdown("**Outfit Performance:**")
                    st.markdown(f"Match: **{entry['match_score']}/100**")
                    st.markdown(f"Comfort: **{entry['comfort_score']}/100**")
                    st.markdown(f"Weather Defense: **{entry['weather_score']}/100**")
                    st.markdown(f"Style: **{entry['style_score']}/100**")
