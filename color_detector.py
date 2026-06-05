"""
WeatherWear Color Detector
===========================
Detects the dominant color of a clothing item from an image
using pixel clustering — no external AI needed.

Returns a human-readable color name like "Navy Blue", "Olive Green", etc.
"""

import numpy as np
from PIL import Image


# Full color map: (R, G, B) -> human name
COLOR_MAP = [
    ((0,   0,   0),   "Black"),
    ((255, 255, 255),  "White"),
    ((128, 128, 128),  "Grey"),
    ((192, 192, 192),  "Light Grey"),
    ((64,  64,  64),   "Charcoal"),
    ((255, 0,   0),    "Red"),
    ((180, 0,   0),    "Dark Red"),
    ((255, 100, 100),  "Light Red"),
    ((255, 165, 0),    "Orange"),
    ((255, 200, 0),    "Yellow"),
    ((255, 255, 0),    "Bright Yellow"),
    ((0,   128, 0),    "Green"),
    ((0,   200, 0),    "Bright Green"),
    ((0,   80,  0),    "Dark Green"),
    ((107, 142, 35),   "Olive Green"),
    ((0,   0,   255),  "Blue"),
    ((0,   0,   180),  "Dark Blue"),
    ((0,   0,   128),  "Navy Blue"),
    ((100, 149, 237),  "Cornflower Blue"),
    ((135, 206, 235),  "Sky Blue"),
    ((75,  0,   130),  "Purple"),
    ((148, 0,   211),  "Violet"),
    ((255, 0,   255),  "Magenta"),
    ((255, 182, 193),  "Pink"),
    ((255, 105, 180),  "Hot Pink"),
    ((139, 69,  19),   "Brown"),
    ((160, 82,  45),   "Sienna"),
    ((210, 180, 140),  "Tan"),
    ((245, 222, 179),  "Wheat"),
    ((255, 228, 196),  "Beige"),
    ((245, 245, 220),  "Cream"),
    ((0,   128, 128),  "Teal"),
    ((0,   255, 255),  "Cyan"),
    ((64,  224, 208),  "Turquoise"),
    ((128, 0,   0),    "Maroon"),
    ((128, 128, 0),    "Khaki"),
    ((70,  130, 180),  "Steel Blue"),
    ((176, 196, 222),  "Light Blue"),
]


def _color_distance(c1, c2):
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def _nearest_color_name(rgb):
    return min(COLOR_MAP, key=lambda x: _color_distance(rgb, x[0]))[1]


def detect_dominant_color(img: Image.Image, top_n: int = 3) -> str:
    """
    Find the dominant color of a clothing item.

    Steps:
    1. Resize image to speed up processing
    2. Remove background-ish pixels (very light/dark borders)
    3. Sample pixel colors
    4. Find the most common color cluster
    5. Map to nearest human-readable name
    """
    img = img.convert("RGB")
    img = img.resize((100, 100))
    pixels = np.array(img).reshape(-1, 3)

    # Filter out near-white backgrounds and near-black shadows
    mask = ~(
        ((pixels[:, 0] > 230) & (pixels[:, 1] > 230) & (pixels[:, 2] > 230)) |
        ((pixels[:, 0] < 20)  & (pixels[:, 1] < 20)  & (pixels[:, 2] < 20))
    )
    filtered = pixels[mask]

    if len(filtered) == 0:
        filtered = pixels  # fallback if everything got filtered

    # Simple binning: quantize to 32-step buckets and find most common
    quantized = (filtered // 32) * 32
    rows = [tuple(r) for r in quantized]

    from collections import Counter
    counts = Counter(rows)
    top_colors = [color for color, _ in counts.most_common(top_n)]

    # Average the top N dominant colors for stability
    avg = np.mean(top_colors, axis=0).astype(int)
    return _nearest_color_name(tuple(avg))


if __name__ == "__main__":
    # Quick test
    from PIL import Image as PILImage
    import requests
    from io import BytesIO

    test_url = "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=200"
    try:
        response = requests.get(test_url, timeout=5)
        img = PILImage.open(BytesIO(response.content))
        color = detect_dominant_color(img)
        print(f"Detected color: {color}")
    except Exception as e:
        print(f"Test failed (no network): {e}")
        # Offline test with a solid color image
        solid = PILImage.new("RGB", (100, 100), (0, 0, 128))
        print(f"Navy test: {detect_dominant_color(solid)}")
