# 🌦️ WeatherWear AI

WeatherWear AI is an intelligent fashion assistant that combines real-time weather forecasting, wardrobe management, machine learning, and generative AI to help users choose the right outfit for any situation.

## 🚀 Features

### 👕 Smart Outfit Recommendations

* Weather-aware clothing suggestions
* Outfit recommendations based on temperature and conditions
* Personalized style preferences

### 🤖 AI-Powered Fashion Assistant

* Clothing image analysis
* Clothing classification using machine learning
* AI-generated styling advice
* Wardrobe insights and recommendations

### 🌍 Travel Planning

* Multi-day weather forecasts
* Packing recommendations
* Travel outfit planning
* Destination weather analysis

### 📊 Wardrobe Analytics

* Closet statistics
* Clothing usage tracking
* Wardrobe diversity insights
* Fashion trend analysis

### 📚 Outfit History

* Save previous outfit recommendations
* Track styling decisions
* Review historical weather and outfit data

### 👤 User Management

* User authentication
* Personal wardrobe storage
* Preference management
* Guest mode support

## 🛠️ Technologies Used

### Frontend

* Streamlit

### Backend

* Python

### Database

* SQLite

### AI & Machine Learning

* Google Gemini 1.5 Flash
* Scikit-learn
* Custom Fashion Classification Model

### APIs

* OpenWeather API
* Google Gemini API

### Data Processing

* Pandas
* NumPy
* BeautifulSoup

## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/norayramirkhanyan23/weatherwear.git
cd weatherwear
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create Streamlit secrets:

```toml
OPENWEATHER_API_KEY="your_api_key"
GEMINI_API_KEY="your_api_key"
HF_TOKEN="your_token"
```

Run the application:

```bash
streamlit run main.py
```

## 📁 Project Structure

```text
weatherwear/
│
├── main.py
├── color_detector.py
├── fashion_model.py
├── fashion_classifier.pkl
├── weatherwear.db
├── uploads/
├── .streamlit/
│   └── secrets.toml
├── requirements.txt
└── README.md
```

## 🎯 Future Improvements

* Advanced outfit recommendation engine
* Expanded clothing recognition
* Social wardrobe sharing
* Calendar integration
* Mobile application version
* Enhanced machine learning models

## 👨‍💻 Author

Norayr Amirkhanyan 

Developed as an AI-powered fashion and weather intelligence platform combining machine learning, generative AI, and real-time weather forecasting.
