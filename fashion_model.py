"""
WeatherWear Fashion Classifier
================================
Trains a local ML model to classify clothing items by:
  - Type (T-Shirt, Jacket, Jeans, etc.)
  - Formality (Casual, Smart-Casual, Business, Formal)

Features extracted from image:
  - Color histogram (HSV bins)
  - Brightness / saturation stats
  - Texture contrast (pixel variance)
  - Aspect ratio

Run this file once to generate: fashion_classifier.pkl
"""

import numpy as np
import pickle
import os
from PIL import Image, ImageStat
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# =====================
# FEATURE EXTRACTION
# =====================
def extract_image_features(img: Image.Image) -> np.ndarray:
    """
    Extract a numeric feature vector from a PIL image.
    Used both during training and inference.
    """
    img = img.convert("RGB")
    img_resized = img.resize((64, 64))

    # --- Color histogram in HSV space ---
    img_hsv = img_resized.convert("HSV") if hasattr(img_resized, "convert") else img_resized
    try:
        img_hsv = img_resized.convert("HSV")
    except Exception:
        img_hsv = img_resized

    pixels = np.array(img_resized).reshape(-1, 3)

    # Hue, Saturation, Value bins
    r, g, b = pixels[:, 0], pixels[:, 1], pixels[:, 2]

    # Normalize
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    # Color histograms (8 bins each)
    r_hist, _ = np.histogram(r_norm, bins=8, range=(0, 1))
    g_hist, _ = np.histogram(g_norm, bins=8, range=(0, 1))
    b_hist, _ = np.histogram(b_norm, bins=8, range=(0, 1))

    # Normalize histograms
    r_hist = r_hist / r_hist.sum()
    g_hist = g_hist / g_hist.sum()
    b_hist = b_hist / b_hist.sum()

    # --- Brightness & contrast stats ---
    stat = ImageStat.Stat(img_resized)
    mean_brightness = np.mean(stat.mean) / 255.0
    stddev = np.mean(stat.stddev) / 255.0

    # --- Texture: pixel variance in grayscale ---
    gray = np.array(img_resized.convert("L")) / 255.0
    texture_var = float(np.var(gray))
    texture_mean = float(np.mean(gray))

    # --- Aspect ratio ---
    w, h = img.size
    aspect_ratio = w / h if h > 0 else 1.0

    # --- Dominant color saturation (how colorful vs neutral) ---
    max_rgb = pixels.max(axis=1) / 255.0
    min_rgb = pixels.min(axis=1) / 255.0
    saturation = np.mean(max_rgb - min_rgb)

    # --- Dark / light bias ---
    dark_ratio = float(np.mean(gray < 0.3))
    light_ratio = float(np.mean(gray > 0.7))

    feature_vector = np.concatenate([
        r_hist, g_hist, b_hist,
        [mean_brightness, stddev, texture_var, texture_mean,
         aspect_ratio, saturation, dark_ratio, light_ratio]
    ])

    return feature_vector


# =====================
# SYNTHETIC TRAINING DATA
# =====================
def generate_training_data():
    """
    Generate synthetic training samples with realistic color/texture
    profiles for each clothing type and formality level.

    Each sample is (feature_vector, type_label, formality_label).
    Real-world deployment would replace this with labeled image data.
    """
    np.random.seed(42)
    samples = []

    def make_sample(
        r_mean, g_mean, b_mean,
        brightness, contrast, texture,
        aspect, saturation, dark, light,
        clothing_type, formality,
        n=40
    ):
        for _ in range(n):
            noise = np.random.normal(0, 0.04, 35)
            base = np.array([
                *np.random.dirichlet(np.ones(8) * (r_mean * 8 + 0.1)),
                *np.random.dirichlet(np.ones(8) * (g_mean * 8 + 0.1)),
                *np.random.dirichlet(np.ones(8) * (b_mean * 8 + 0.1)),
                brightness + np.random.normal(0, 0.05),
                contrast + np.random.normal(0, 0.03),
                texture + np.random.normal(0, 0.01),
                brightness * 0.9 + np.random.normal(0, 0.03),
                aspect + np.random.normal(0, 0.1),
                saturation + np.random.normal(0, 0.05),
                dark + np.random.normal(0, 0.04),
                light + np.random.normal(0, 0.04),
            ])
            base = np.clip(base + noise[:len(base)], 0, 1)
            samples.append((base, clothing_type, formality))

    # T-Shirts: bright, colorful, high contrast, portrait ratio
    make_sample(0.7, 0.4, 0.4, 0.65, 0.18, 0.02, 0.75, 0.45, 0.05, 0.35, "T-Shirt", "Casual")
    make_sample(0.3, 0.3, 0.7, 0.45, 0.20, 0.02, 0.75, 0.40, 0.15, 0.20, "T-Shirt", "Casual")
    make_sample(0.8, 0.8, 0.8, 0.80, 0.10, 0.01, 0.75, 0.10, 0.02, 0.60, "T-Shirt", "Casual")

    # Hoodies: medium brightness, low saturation, soft texture
    make_sample(0.4, 0.4, 0.5, 0.45, 0.12, 0.015, 0.80, 0.15, 0.20, 0.10, "Hoodie", "Casual")
    make_sample(0.5, 0.3, 0.3, 0.40, 0.14, 0.015, 0.80, 0.20, 0.25, 0.08, "Hoodie", "Casual")

    # Jackets: structured, medium-dark, higher texture
    make_sample(0.2, 0.2, 0.2, 0.25, 0.22, 0.04, 0.65, 0.08, 0.55, 0.02, "Jacket", "Smart-Casual")
    make_sample(0.5, 0.4, 0.2, 0.40, 0.25, 0.04, 0.65, 0.30, 0.20, 0.08, "Jacket", "Smart-Casual")
    make_sample(0.15, 0.15, 0.25, 0.20, 0.20, 0.05, 0.65, 0.10, 0.60, 0.01, "Jacket", "Business")

    # Jeans: blue-dominant, medium brightness, wide aspect
    make_sample(0.2, 0.3, 0.7, 0.40, 0.18, 0.03, 1.20, 0.40, 0.20, 0.08, "Jeans", "Casual")
    make_sample(0.1, 0.15, 0.5, 0.30, 0.20, 0.03, 1.20, 0.35, 0.35, 0.03, "Jeans", "Casual")

    # Shorts: bright, wide aspect ratio, high light ratio
    make_sample(0.6, 0.5, 0.3, 0.60, 0.15, 0.02, 1.40, 0.35, 0.05, 0.40, "Shorts", "Casual")
    make_sample(0.3, 0.6, 0.4, 0.55, 0.15, 0.02, 1.40, 0.30, 0.05, 0.35, "Shorts", "Casual")

    # Coats: dark, heavy texture, portrait ratio
    make_sample(0.15, 0.12, 0.10, 0.18, 0.25, 0.06, 0.55, 0.06, 0.65, 0.01, "Coat", "Casual")
    make_sample(0.10, 0.10, 0.10, 0.12, 0.22, 0.07, 0.55, 0.04, 0.75, 0.01, "Coat", "Formal")
    make_sample(0.25, 0.20, 0.15, 0.22, 0.24, 0.06, 0.55, 0.10, 0.55, 0.02, "Coat", "Business")

    # Sweaters: warm tones, soft texture, medium brightness
    make_sample(0.7, 0.5, 0.3, 0.55, 0.12, 0.015, 0.80, 0.35, 0.05, 0.25, "Sweater", "Smart-Casual")
    make_sample(0.5, 0.5, 0.5, 0.50, 0.10, 0.012, 0.80, 0.10, 0.10, 0.20, "Sweater", "Business")

    # Shirts: clean, light, structured
    make_sample(0.9, 0.9, 0.9, 0.88, 0.08, 0.01, 0.70, 0.05, 0.01, 0.75, "Shirt", "Business")
    make_sample(0.6, 0.75, 0.85, 0.72, 0.12, 0.01, 0.70, 0.25, 0.02, 0.45, "Shirt", "Smart-Casual")
    make_sample(0.85, 0.85, 0.6, 0.78, 0.10, 0.01, 0.70, 0.20, 0.01, 0.55, "Shirt", "Formal")

    # Trousers: dark neutral, structured, portrait
    make_sample(0.2, 0.2, 0.2, 0.22, 0.18, 0.03, 0.50, 0.05, 0.60, 0.01, "Trousers", "Business")
    make_sample(0.3, 0.25, 0.2, 0.28, 0.16, 0.03, 0.50, 0.08, 0.45, 0.02, "Trousers", "Formal")
    make_sample(0.4, 0.35, 0.3, 0.38, 0.14, 0.025, 0.50, 0.10, 0.30, 0.05, "Trousers", "Smart-Casual")

    # Accessories: small, high contrast, varied colors
    make_sample(0.6, 0.3, 0.1, 0.45, 0.30, 0.08, 1.0, 0.50, 0.10, 0.20, "Accessories", "Casual")
    make_sample(0.1, 0.1, 0.1, 0.15, 0.35, 0.10, 1.0, 0.05, 0.70, 0.01, "Accessories", "Formal")

    return samples


# =====================
# TRAIN & SAVE
# =====================
def train_and_save(output_path="fashion_classifier.pkl"):
    print("🧠 Generating training data...")
    data = generate_training_data()

    X = np.array([s[0] for s in data])
    y_type = np.array([s[1] for s in data])
    y_formality = np.array([s[2] for s in data])

    # Encode labels
    type_encoder = LabelEncoder()
    formality_encoder = LabelEncoder()
    y_type_enc = type_encoder.fit_transform(y_type)
    y_formality_enc = formality_encoder.fit_transform(y_formality)

    # Split
    X_train, X_test, yt_train, yt_test, yf_train, yf_test = train_test_split(
        X, y_type_enc, y_formality_enc, test_size=0.2, random_state=42
    )

    # Train type classifier
    print("🏋️ Training clothing type classifier...")
    type_clf = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42)
    type_clf.fit(X_train, yt_train)

    # Train formality classifier
    print("🏋️ Training formality classifier...")
    formality_clf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
    formality_clf.fit(X_train, yf_train)

    # Evaluate
    print("\n📊 Type Classifier Report:")
    print(classification_report(yt_test, type_clf.predict(X_test),
                                 target_names=type_encoder.classes_))

    print("\n📊 Formality Classifier Report:")
    print(classification_report(yf_test, formality_clf.predict(X_test),
                                 target_names=formality_encoder.classes_))

    # Save
    model_bundle = {
        "type_clf": type_clf,
        "formality_clf": formality_clf,
        "type_encoder": type_encoder,
        "formality_encoder": formality_encoder,
        "feature_extractor_version": "1.0",
    }
    with open(output_path, "wb") as f:
        pickle.dump(model_bundle, f)

    print(f"\n✅ Model saved to {output_path}")
    return model_bundle


if __name__ == "__main__":
    train_and_save()
