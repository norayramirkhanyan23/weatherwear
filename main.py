import requests
import tkinter as tk
from tkinter import Toplevel
from datetime import datetime

# =====================
# CONFIG
# =====================
API_KEY = "4081561b551e7b5509232ca9a0579774"

CITIES = [
    "Yerevan", "Gyumri", "Vanadzor", "Vagharshapat",
    "Hrazdan", "Abovyan", "Kapan", "Armavir",
    "Artashat", "Gavar", "Ijevan", "Dilijan",
    "Charentsavan", "Masis", "Sevan", "Ashtarak"
]

# =====================
# WEATHER
# =====================
def get_weather(city):
    try:
        geo_url = "http://api.openweathermap.org/geo/1.0/direct"
        geo_params = {"q": city + ",AM", "limit": 1, "appid": API_KEY}
        geo_data = requests.get(geo_url, params=geo_params).json()

        if not geo_data:
            return None

        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]

        weather_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY,
            "units": "metric"
        }

        data = requests.get(weather_url, params=params).json()

        temp = data["main"]["feels_like"]
        condition = data["weather"][0]["main"]

        return temp, condition

    except:
        return None


# =====================
# ICON LOGIC
# =====================
def get_icon(condition):
    if "Rain" in condition:
        return "🌧️"
    elif "Cloud" in condition:
        return "☁️"
    elif "Snow" in condition:
        return "❄️"
    else:
        return "☀️"


# =====================
# AI TEXT
# =====================
def generate_text(temp, yesterday, condition):
    now = datetime.now().strftime("%H:%M")

    if temp > yesterday:
        trend = "warmer than yesterday"
    elif temp < yesterday:
        trend = "colder than yesterday"
    else:
        trend = "same as yesterday"

    icon = get_icon(condition)

    return f"{icon} {round(temp)}°C\n{trend}\nNow: {now}"


# =====================
# OUTFIT (IMPROVED)
# =====================
def get_outfit(temp, preference=0):
    temp += preference  # personalization

    if temp >= 25:
        return ["T-shirt", "Shorts"]
    elif 20 <= temp < 25:
        return ["T-shirt", "Light pants"]
    elif 15 <= temp < 20:
        return ["T-shirt", "Jacket"]
    elif 10 <= temp < 15:
        return ["Hoodie", "Jacket"]
    elif 0 <= temp < 10:
        return ["Warm jacket", "Layers"]
    else:
        return ["Heavy coat", "Scarf"]


# =====================
# DROPDOWN
# =====================
def update_list(event):
    typed = entry.get().lower()
    listbox.delete(0, tk.END)

    for city in CITIES:
        if typed in city.lower():
            listbox.insert(tk.END, city)


def select_city(event):
    selected = listbox.get(listbox.curselection())
    entry.delete(0, tk.END)
    entry.insert(0, selected)
    listbox.delete(0, tk.END)


# =====================
# MAIN
# =====================
def run():
    city = entry.get()

    data = get_weather(city)

    if data is None:
        result.set("Offline mode\n20°C\nNow")
        current_temp[0] = 20
        current_condition[0] = "Clear"
        return

    temp, condition = data
    yesterday = temp - 2

    current_temp[0] = temp
    current_condition[0] = condition

    result.set(generate_text(temp, yesterday, condition))


# =====================
# OUTFIT WINDOW
# =====================
def show_outfit():
    if current_temp[0] is None:
        return

    win = Toplevel(root)
    win.title("Outfit")
    win.geometry("320x300")
    win.configure(bg="white")

    pref = [0]

    def update():
        outfit = get_outfit(current_temp[0], pref[0])
        text.set("\n".join(outfit))

    text = tk.StringVar()
    update()

    tk.Label(win, text="What to Wear",
             font=("Helvetica Neue", 16, "bold"),
             bg="white").pack(pady=10)

    tk.Label(win, textvariable=text,
             font=("Helvetica Neue", 14),
             bg="white").pack(pady=10)

    # CUSTOMIZE (AI FEELING)
    def colder():
        pref[0] -= 2
        update()

    def warmer():
        pref[0] += 2
        update()

    tk.Label(win, text="Customize",
             font=("Helvetica Neue", 12),
             bg="white").pack(pady=10)

    tk.Button(win, text="I feel cold",
              command=colder,
              bg="black", fg="white").pack(pady=5)

    tk.Button(win, text="I feel warm",
              command=warmer,
              bg="black", fg="white").pack(pady=5)


# =====================
# UI
# =====================
root = tk.Tk()
root.title("WeatherWear")
root.geometry("360x500")
root.configure(bg="black")

FONT_TITLE = ("Helvetica Neue", 26, "bold")
FONT_MAIN = ("Helvetica Neue", 18)
FONT_SMALL = ("Helvetica Neue", 12)

tk.Label(root, text="WeatherWear",
         font=FONT_TITLE,
         bg="black", fg="white").pack(pady=20)

entry = tk.Entry(root,
                 font=FONT_SMALL,
                 justify="center",
                 bd=0,
                 width=25)
entry.pack(pady=5, ipady=6)

entry.bind("<KeyRelease>", update_list)

listbox = tk.Listbox(root,
                     font=FONT_SMALL,
                     height=5)
listbox.pack(pady=5)

listbox.bind("<<ListboxSelect>>", select_city)

tk.Button(root, text="Check",
          command=run,
          font=FONT_SMALL,
          bg="white", fg="black",
          bd=0, padx=20, pady=6).pack(pady=10)

result = tk.StringVar()

tk.Label(root,
         textvariable=result,
         font=FONT_MAIN,
         bg="black",
         fg="white",
         justify="center").pack(pady=30)

tk.Button(root, text="What to wear",
          command=show_outfit,
          font=FONT_SMALL,
          bg="white", fg="black",
          bd=0, padx=20, pady=6).pack()

current_temp = [None]
current_condition = [None]

root.mainloop()