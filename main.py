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

# =====================
# CONFIG
# =====================
API_KEY = st.secrets["API_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)

# =====================
# PAGE
# =====================
st.set_page_config(
    page_title="AI Personal Stylist | WeatherWear",
    layout="wide"
)


# =====================
# DATABASE ENGINE
# =====================
def init_db():
    """Creates the necessary tables if they don't exist."""
    conn = sqlite3.connect("weatherwear.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, cold_pref TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS wardrobe
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 username TEXT, name TEXT, type TEXT, color TEXT, fabric TEXT, formality TEXT)''')
    # NEW: History table for tracking past outfits
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
    clothes = [{"name": row["name"], "type": row["type"], "color": row["color"], "fabric": row["fabric"],
                "formality": row["formality"]} for row in c.fetchall()]
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
footer {visibility: hidden;}
header {visibility: hidden;}
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
    max-width: 400px;
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
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.markdown("<div class='auth-box'>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>WeatherWear</h1>", unsafe_allow_html=True)
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
                st.rerun()
            else:
                st.error("Incorrect username or password.")

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
        except:
            yesterday = feels - 2
        return {
            "temp": feels, "diff": feels - yesterday, "condition": current["weather"][0]["main"],
            "humidity": current["main"]["humidity"], "wind": current["wind"]["speed"],
            "rainy": "Rain" in current["weather"][0]["main"], "snowy": "Snow" in current["weather"][0]["main"],
            "windy": current["wind"]["speed"] > 6, "lat": lat, "lon": lon
        }
    except:
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
            return "Tomorrow feels warmer."
        elif tomorrow < today - 2:
            return "Tomorrow feels colder."
        else:
            return "Tomorrow feels similar."
    except:
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
    except:
        return []


# =====================
# AI WARDROBE ENGINES
# =====================
def analyze_clothing_image(uploaded_file):
    try:
        img = Image.open(uploaded_file)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """
        Analyze this clothing item in deep detail. Return ONLY a valid JSON object (no markdown tags or formatting) with these exact keys:
        - "name": A short, stylish name (e.g., "Vintage Denim Jacket" or "Red Graphic T-Shirt")
        - "type": Choose strictly ONE from this list: ["T-Shirt", "Hoodie", "Jacket", "Jeans", "Shorts", "Coat", "Sweater", "Shirt", "Trousers", "Accessories"]
        - "color": The dominant color (e.g., "Navy Blue", "Olive Green")
        - "fabric": The likely material (e.g., "Cotton", "Wool", "Denim", "Leather", "Polyester")
        - "formality": Choose ONE: ["Casual", "Smart-Casual", "Business", "Formal"]
        """
        response = model.generate_content([prompt, img])
        clean_response = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_response)
    except Exception as e:
        st.error("Could not analyze the image.")
        return None


def analyze_clothing_link(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        page = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(page.content, 'html.parser')
        title = soup.title.string if soup.title else "Unknown Item"
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        desc = meta_desc['content'] if meta_desc else ""
        scraped_text = f"Title: {title}\nDescription: {desc}"
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Analyze this clothing product webpage data in deep detail. Return ONLY a valid JSON object (no markdown tags) with these exact keys:
        - "name": A clean, short name based on the title (e.g., "Zara Puffer Coat")
        - "type": Choose strictly ONE from this list: ["T-Shirt", "Hoodie", "Jacket", "Jeans", "Shorts", "Coat", "Sweater", "Shirt", "Trousers", "Accessories"]
        - "color": The dominant color
        - "fabric": Primary material mentioned (e.g., "Cotton", "Wool", "Blend")
        - "formality": Choose ONE: ["Casual", "Smart-Casual", "Business", "Formal"]
        Data to analyze:
        {scraped_text}
        """
        response = model.generate_content(prompt)
        clean_response = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_response)
    except Exception as e:
        st.error("Could not scrape or analyze that link. Ensure it's a valid URL.")
        return None


def weather_ai(weather, cold_level, wardrobe, activity_formality):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        if cold_level >= 9:
            preference = "Runs hot (prefers lighter clothes even when it's cool)"
        elif cold_level <= 1:
            preference = "Runs cold (needs extra layers, gets chilly easily)"
        else:
            preference = "Balanced (standard temperature preference)"

        if wardrobe:
            wardrobe_text = "\n".join([
                                          f"- '{item['name']}' (Color: {item['color']}, Fabric: {item['fabric']}, Type: {item['type']}, Formality: {item['formality']})"
                                          for item in wardrobe])
        else:
            wardrobe_text = "No clothes uploaded yet. Suggest general generic clothing types."

        prompt = f"""
        You are an elite AI personal stylist. 
        Current Live Weather:
        - Temperature: {weather['temp']}°C (Feels like)
        - Condition: {weather['condition']}
        - Wind Speed: {weather['wind']} m/s
        - Is it Raining?: {weather['rainy']}
        - Is it Snowing?: {weather['snowy']}
        - Temp difference from yesterday: {weather['diff']}°C

        User's Body Temperature Preference: {preference}
        Target Event Formality: {activity_formality}

        User's Available Closet/Wardrobe: 
        {wardrobe_text}

        Task: Pick the absolute best outfit from their closet for today's weather using LAYERING LOGIC. Factor in fabric warmth and target formality.
        Return ONLY a valid JSON object (no markdown, no backticks) with these exact keys:
        - "hook": A short 3-6 word headline comparing today to yesterday.
        - "vibe": A friendly, natural paragraph (2-3 sentences) explaining WHY you chose this specific combination.
        - "outfit": A list of strings containing ONLY the names of the items you selected.
        - "scores": A dictionary containing four integer values between 0 and 100 representing how good the outfit is: "match", "comfort", "weather", and "style".
        """
        response = model.generate_content(prompt)
        clean_response = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_response)
        return data.get("hook"), data.get("vibe"), data.get("outfit", []), data.get("scores",
                                                                                    {"match": 80, "comfort": 80,
                                                                                     "weather": 80, "style": 80})
    except Exception as e:
        return (
        "Weather analyzed.", "Look at the temperature and dress comfortably!", ["Base Layer", "Pants", "Outerwear"],
        {"match": 0, "comfort": 0, "weather": 0, "style": 0})


def travel_ai(weather, cold_level, wardrobe, dest, days, activities):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        if cold_level >= 9:
            preference = "Runs hot"
        elif cold_level <= 1:
            preference = "Runs cold"
        else:
            preference = "Balanced"

        wardrobe_text = "\n".join([
                                      f"- '{item['name']}' (Color: {item['color']}, Fabric: {item['fabric']}, Type: {item['type']}, Formality: {item['formality']})"
                                      for item in wardrobe]) if wardrobe else "Empty closet."

        prompt = f"""
        You are an elite AI travel stylist.
        Destination: {dest} | Days: {days} | Planned Activities: {', '.join(activities)}
        Destination Weather: Temp: {weather['temp']}°C, Condition: {weather['condition']}, Wind: {weather['wind']} m/s.
        User Prefs: {preference}
        User's Closet:
        {wardrobe_text}

        Task: Create a highly specific packing list utilizing items FROM THEIR CLOSET. Identify specific "missing items" they need to consider acquiring.
        Return ONLY a valid JSON object (no markdown, no backticks) with these keys:
        - "hook": Short headline for the trip.
        - "packing_list": List of strings referencing items from their closet.
        - "missing_items": List of strings referencing missing essentials (e.g., "No formal shoes found for your fine dining activity").
        - "readiness_score": Integer 0-100 indicating how well their closet supports this trip.
        - "score_explanation": 1-2 sentence explanation of the readiness score.
        - "activity_tips": List of 2-3 short styling tips for their specific activities.
        """
        response = model.generate_content(prompt)
        clean_response = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_response)
    except Exception as e:
        return {"hook": "Trip Analyzed", "packing_list": ["Comfortable clothes"], "missing_items": [],
                "readiness_score": 50, "score_explanation": "Unable to run deep analysis.",
                "activity_tips": ["Have a great trip!"]}


def analytics_ai(wardrobe):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        wardrobe_text = "\n".join(
            [f"- '{item['name']}' (Type: {item['type']}, Fabric: {item['fabric']}, Formality: {item['formality']})" for
             item in wardrobe]) if wardrobe else "Empty closet."
        prompt = f"""
        You are an AI wardrobe analyst. Review this closet:
        {wardrobe_text}

        Task: Identify critical missing essentials to build a complete capsule wardrobe (e.g., waterproof jacket, formal wear, winter coat). Provide a seasonal readiness score.
        Return ONLY a valid JSON object (no markdown, no backticks) with these keys:
        - "seasonal_readiness": Integer 0-100.
        - "missing_essentials": List of 3-5 critical items missing from their closet.
        - "suggestions": A 2-3 sentence paragraph of strategic wardrobe improvement advice.
        """
        response = model.generate_content(prompt)
        clean_response = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_response)
    except Exception as e:
        return {"seasonal_readiness": 0, "missing_essentials": ["Unable to analyze"],
                "suggestions": "Add more items to your closet."}


# =====================
# SIDEBAR
# =====================
with st.sidebar:
    st.markdown(f"### 👋 Welcome, {current_user}!")
    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    st.markdown("---")
    st.markdown("## Stylist Preferences")
    cold_pref = st.select_slider("Body Temp Preference", options=["Warm", "Balanced", "Cold"], value=saved_pref)
    if cold_pref != saved_pref:
        update_user_pref(current_user, cold_pref)

    day_formality = st.selectbox("Target Formality", ["Casual", "Smart-Casual", "Business", "Formal"])

    st.markdown("---")
    st.markdown("## Manage Closet")

    img_tab, link_tab = st.tabs(["Upload Photo", "Paste Link"])

    with img_tab:
        uploaded_file = st.file_uploader("Upload clothes", type=["png", "jpg", "jpeg"])
        if uploaded_file and st.button("Add via Image"):
            with st.spinner("AI is analyzing fabric and color..."):
                ai_data = analyze_clothing_image(uploaded_file)
                if ai_data:
                    add_clothing_to_db(current_user, ai_data.get('name', 'Item'), ai_data.get('type', 'Misc'),
                                       ai_data.get('color', 'Mixed'), ai_data.get('fabric', 'Unknown'),
                                       ai_data.get('formality', 'Casual'))
                    st.success(f"Added {ai_data['name']}!")
                    st.rerun()

    with link_tab:
        clothing_url = st.text_input("Paste store link (ASOS, Zara, etc.)")
        if clothing_url and st.button("Add via Link"):
            with st.spinner("AI is reading the website details..."):
                ai_data = analyze_clothing_link(clothing_url)
                if ai_data:
                    add_clothing_to_db(current_user, ai_data.get('name', 'Item'), ai_data.get('type', 'Misc'),
                                       ai_data.get('color', 'Mixed'), ai_data.get('fabric', 'Unknown'),
                                       ai_data.get('formality', 'Casual'))
                    st.success(f"Added {ai_data['name']}!")
                    st.rerun()

    st.markdown("---")
    st.markdown("### Your Closet")
    if not user_wardrobe:
        st.info("Your closet is empty. Add some clothes!")
    else:
        for item in user_wardrobe:
            st.markdown(
                f"""
                <div style="background-color: #111827; padding: 12px; border-radius: 12px; margin-bottom: 8px; border: 1px solid #27272a;">
                    <strong>{item['name']}</strong><br>
                    <span class="tag-pill">{item['type']}</span>
                    <span class="tag-pill">{item['fabric']}</span>
                    <span class="tag-pill">{item['formality']}</span>
                </div>
                """,
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
tab1, tab2, tab3, tab4 = st.tabs(["Daily Stylist", "Travel Concierge", "Wardrobe Analytics", "Styling History"])

# =====================================================
# DAILY STYLIST (WEATHER) TAB
# =====================================================
with tab1:
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center;'>WeatherWear Studio</h1>", unsafe_allow_html=True)
        city = st.text_input("Where are you?", "Yerevan")

        if st.button("Generate Styling"):
            weather = get_lazy_weather(city)

            if weather:
                bg_css = get_weather_css(weather["condition"])
                st.markdown(f"<style>.stApp {{ background: {bg_css} }}</style>", unsafe_allow_html=True)

                hook, vibe, outfit, scores = weather_ai(weather, cold_value, user_wardrobe, day_formality)
                forecast = tomorrow_vibe(weather["lat"], weather["lon"])
                forecast_data = get_forecast(weather["lat"], weather["lon"])

                # Save to history
                if outfit:
                    save_outfit_history(current_user, city, weather['temp'], weather['condition'], outfit, scores)

                icon = "☀"
                if weather["rainy"]:
                    icon = "☂"
                elif weather["snowy"]:
                    icon = "❄"
                elif weather["windy"]:
                    icon = "☼"

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"<div class='huge-temp'>{icon} {weather['temp']}°</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='hook'>{hook}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='vibe'>{vibe}</div>", unsafe_allow_html=True)
                if forecast: st.markdown(f"<div class='forecast'>{forecast}</div>", unsafe_allow_html=True)
                st.markdown("<br><hr>", unsafe_allow_html=True)

                # SCORES DISPLAY
                st.markdown("### Styling Metrics")
                sc1, sc2, sc3, sc4 = st.columns(4)
                with sc1:
                    st.markdown("<div class='metric-label'>Outfit Match</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='metric-value'>{scores.get('match', 0)}/100</div>", unsafe_allow_html=True)
                    st.progress(scores.get('match', 0) / 100)
                with sc2:
                    st.markdown("<div class='metric-label'>Comfort</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='metric-value'>{scores.get('comfort', 0)}/100</div>",
                                unsafe_allow_html=True)
                    st.progress(scores.get('comfort', 0) / 100)
                with sc3:
                    st.markdown("<div class='metric-label'>Weather</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='metric-value'>{scores.get('weather', 0)}/100</div>",
                                unsafe_allow_html=True)
                    st.progress(scores.get('weather', 0) / 100)
                with sc4:
                    st.markdown("<div class='metric-label'>Style</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='metric-value'>{scores.get('style', 0)}/100</div>", unsafe_allow_html=True)
                    st.progress(scores.get('style', 0) / 100)

                st.markdown("<br>", unsafe_allow_html=True)

                st.markdown("### Recommended Pieces")
                for item in outfit:
                    st.markdown(f"<div class='outfit-card'>✧ {item}</div>", unsafe_allow_html=True)

                with st.popover("⚙️ View Technical Weather Stats"):
                    st.markdown("**Live Readings:**")
                    st.metric("Humidity", f"{weather['humidity']}%")
                    st.metric("Wind Speed", f"{weather['wind']} m/s")
                    st.metric("Temp Diff", f"{weather['diff']}°C vs yesterday")

                st.markdown("<br>", unsafe_allow_html=True)

                with st.expander("📅 View Extended Weather Intelligence"):
                    forecast_choice = st.selectbox("Forecast Length", ["7 Days", "15 Days"])
                    days_to_show = 15 if forecast_choice == "15 Days" else 7

                    # Analytics for highlighting
                    best_day = min(forecast_data[:days_to_show], key=lambda x: abs(x['temp_max'] - 22) + x['precip'])
                    worst_day = max(forecast_data[:days_to_show], key=lambda x: abs(x['temp_max'] - 22) + x['precip'])
                    rainiest_day = max(forecast_data[:days_to_show], key=lambda x: x['precip'])

                    for row_start in range(0, days_to_show, 5):
                        cols = st.columns(5)
                        for i in range(5):
                            idx = row_start + i
                            if idx >= days_to_show: break

                            day = forecast_data[idx]
                            icon = "☀"
                            if day["condition"] == "Rain":
                                icon = "☂"
                            elif day["condition"] == "Snow":
                                icon = "❄"
                            elif day["condition"] == "Cloudy":
                                icon = "☁"

                            # Highlighting logic
                            card_class = "forecast-card"
                            badge_html = ""
                            if day == best_day:
                                card_class += " forecast-highlight-best"
                                badge_html = "<div class='tag-pill' style='background: #4ade80; color: #000;'>Best Day</div>"
                            elif day == rainiest_day and day['precip'] > 20:
                                card_class += " forecast-highlight-rain"
                                badge_html = "<div class='tag-pill' style='background: #60a5fa; color: #000;'>Rainiest</div>"
                            elif day == worst_day:
                                card_class += " forecast-highlight-worst"
                                badge_html = "<div class='tag-pill' style='background: #f87171; color: #000;'>Extreme</div>"

                            with cols[i]:
                                st.markdown(
                                    f"""
                                    <div class="{card_class}">
                                        {badge_html}
                                        <div class="forecast-day" style="margin-top:8px;">{day['day']}</div>
                                        <div class="forecast-temp">{day['temp_max']}°</div>
                                        <div class="forecast-min-temp">Min {day['temp_min']}°</div>
                                        <div style="font-size:40px; margin-top:10px;">{icon}</div>
                                        <div class="forecast-condition">{day['condition']}</div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
            else:
                st.error("Couldn't understand the weather there.")

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
        trip_days = st.slider("Trip length", 1, 30, 5)

    activities = st.multiselect(
        "What will you do?",
        ["Walking", "Business", "Nightlife", "Hiking", "Beach", "Photography", "Fine Dining", "Shopping"]
    )

    if st.button("Analyze Trip & Generate Packing List"):
        home_weather = get_lazy_weather(start_city)
        travel_weather = get_lazy_weather(destination)

        if travel_weather and home_weather:
            bg_css = get_weather_css(travel_weather["condition"])
            st.markdown(f"<style>.stApp {{ background: {bg_css} }}</style>", unsafe_allow_html=True)

            with st.spinner("AI is analyzing destination climatology and your closet..."):
                t_res = travel_ai(travel_weather, cold_value, user_wardrobe, destination, trip_days, activities)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='travel-box'>", unsafe_allow_html=True)

            top_col1, top_col2 = st.columns([3, 1])
            with top_col1:
                st.markdown(f"<div class='small-label'>{destination.upper()} • {trip_days} DAYS</div>",
                            unsafe_allow_html=True)
                st.markdown(f"<div class='hook'>{t_res.get('hook', 'Your Trip Blueprint')}</div>",
                            unsafe_allow_html=True)
                st.markdown(f"<div class='vibe'>{t_res.get('score_explanation', '')}</div>", unsafe_allow_html=True)
            with top_col2:
                st.markdown("<div class='metric-label'>Packing Readiness</div>", unsafe_allow_html=True)
                score = t_res.get('readiness_score', 0)
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
                        st.markdown(
                            f"<div class='outfit-card' style='border-color: #ef4444; color: #fca5a5;'>✗ {item}</div>",
                            unsafe_allow_html=True)

            if t_res.get("activity_tips"):
                with st.popover("💡 View Stylist Activity Notes"):
                    for tip in t_res.get("activity_tips", []):
                        st.markdown(f"<div class='vibe'>• {tip}</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.error("Couldn't analyze this trip.")

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

        # High Level Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Items", len(df))
        m2.metric("Most Common Type", df['type'].mode()[0] if not df.empty else "N/A")
        m3.metric("Dominant Color", df['color'].mode()[0] if not df.empty else "N/A")
        m4.metric("Primary Fabric", df['fabric'].mode()[0] if not df.empty else "N/A")

        st.markdown("<br><hr><br>", unsafe_allow_html=True)

        chart1, chart2 = st.columns(2)
        with chart1:
            st.markdown("### Category Breakdown")
            st.bar_chart(df['type'].value_counts())
        with chart2:
            st.markdown("### Formality Spectrum")
            st.bar_chart(df['formality'].value_counts())

        st.markdown("<br>", unsafe_allow_html=True)

        # AI Gap Analysis
        st.markdown("### AI Closet Gap Analysis")
        with st.spinner("Running deep closet inspection..."):
            analytics_data = analytics_ai(user_wardrobe)

        g1, g2 = st.columns([1, 2])
        with g1:
            st.markdown("<div class='travel-box' style='text-align:center;'>", unsafe_allow_html=True)
            st.markdown("<div class='metric-label'>Seasonal Readiness Score</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='huge-temp' style='font-size:72px;'>{analytics_data.get('seasonal_readiness', 0)}</div>",
                unsafe_allow_html=True)
            st.progress(analytics_data.get('seasonal_readiness', 0) / 100)
            st.markdown("</div>", unsafe_allow_html=True)
        with g2:
            st.markdown("<div class='travel-box'>", unsafe_allow_html=True)
            st.markdown("#### 🎯 Stylist Suggestions")
            st.markdown(f"<div class='vibe'>{analytics_data.get('suggestions', '')}</div>", unsafe_allow_html=True)
            st.markdown("<br>#### 🛒 Missing Essentials", unsafe_allow_html=True)
            for item in analytics_data.get('missing_essentials', []):
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
                    outfit_list = entry['outfit_details'].split(", ")
                    for item in outfit_list:
                        st.markdown(f"✧ {item}")
                with h_col2:
                    st.markdown("**Outfit Performance:**")
                    st.markdown(f"Match: **{entry['match_score']}/100**")
                    st.markdown(f"Comfort: **{entry['comfort_score']}/100**")
                    st.markdown(f"Weather: **{entry['weather_score']}/100**")
                    st.markdown(f"Style: **{entry['style_score']}/100**")