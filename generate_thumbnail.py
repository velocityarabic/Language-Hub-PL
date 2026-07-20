import os, io, base64, random, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")

SCENIC_STYLES = [
    "stunning Polish woman in traditional folk dress, Warsaw Old Town, colorful townhouses, sunny day",
    "elegant Polish woman in traditional costume, Kraków Main Square, St. Mary's Basilica, morning light",
    "beautiful Polish woman in modern attire, Gdańsk waterfront, Motława river, sunset glow",
    "Polish girl at white sand beach, Baltic Sea coast, crystal clear water, turquoise sea",
    "gorgeous Polish woman in traditional folk dress, Tatra Mountains, Morskie Oko lake, golden hour",
    "beautiful Polish woman with horses, Białowieża Forest, soft morning light",
    "Polish woman in traditional attire, Warsaw Old Town Market, colorful buildings, vibrant atmosphere",
    "elegant Polish woman, Malbork Castle, serene courtyard, peaceful blue hour",
]


def generate_scenic_image(category_english: str, category_polish: str, output_path: str):
    if POLLINATIONS_API_KEY:
        import time as ttime
        session = requests.Session()
        session.timeout = 300
        for attempt in range(4):
            style = random.choice(SCENIC_STYLES)
            prompt = (
                f"Professional YouTube thumbnail for Polish language learning video. "
                f"{style}. "
                f"16:9 landscape 1920x1080 exact. High contrast, vibrant, click-worthy. "
                f"Important: The image MUST contain the following text rendered in bold clear font: "
                f"At top: '120 POLISH PHRASES'. In center: '{category_english}'. "
                f"At bottom: 'VELOCITY POLISH'. Also: '10 MINUTE LESSON' badge."
            )
            try:
                resp = session.post("https://gen.pollinations.ai/v1/images/generations", json={
                    "model": "gpt-image-2",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1792x1024",
                }, headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"}, timeout=300)
                if resp.status_code == 200 and resp.json().get("data"):
                    raw = base64.b64decode(resp.json()["data"][0]["b64_json"])
                    if raw:
                        from PIL import Image
                        img = Image.open(io.BytesIO(raw)).convert("RGB")
                        img = img.resize((1920, 1080), Image.LANCZOS)
                        thumb_bytes = io.BytesIO()
                        quality = 85
                        img.save(thumb_bytes, format="JPEG", quality=quality)
                        while thumb_bytes.tell() > 2097152 and quality > 10:
                            quality -= 10
                            thumb_bytes = io.BytesIO()
                            img.save(thumb_bytes, format="JPEG", quality=quality)
                        thumb_bytes.seek(0)
                        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, "wb") as f:
                            f.write(thumb_bytes.read())
                        print(f"[thumbnail] gpt-image-2 thumbnail saved")
                        return output_path
            except Exception as e:
                print(f"[thumbnail] Attempt {attempt+1} failed ({str(e)[:60]}), retrying..." if attempt < 3 else f"[thumbnail] Fallback after {attempt+1} attempts")
                if attempt < 3:
                    ttime.sleep(10 * (attempt + 1))

    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (1920, 1080), (45, 35, 65))
    draw = ImageDraw.Draw(img)

    for y in range(1080):
        ratio = y / 1080
        if ratio < 0.5:
            r, g, b = 65, 50, 95
        else:
            r = int(65 + (45 - 65) * ((ratio - 0.5) * 2))
            g = int(50 + (35 - 50) * ((ratio - 0.5) * 2))
            b = int(95 + (65 - 95) * ((ratio - 0.5) * 2))
        draw.rectangle([(0, y), (1920, y + 1)], fill=(r, g, b))

    en_fonts = [str(Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"),
                "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    lang_fonts = [str(Path(__file__).parent / "fonts" / "DejaVuSans-Bold.ttf"),
                  "C:/Windows/Fonts/arialbd.ttf"]

    def load_font(paths, size):
        for p in paths:
            if Path(p).exists():
                try: return ImageFont.truetype(p, size)
                except: continue
        return ImageFont.load_default()

    f_big = load_font(en_fonts, 130)
    f_cat = load_font(lang_fonts, 90)
    f_sub = load_font(en_fonts, 55)
    f_brand = load_font(en_fonts, 45)

    draw.text((960, 180), "120 POLISH PHRASES", fill=(255, 210, 0), font=f_big, anchor="mm")

    cat_text = category_english
    bb = draw.textbbox((0, 0), cat_text, font=f_cat)
    cw = bb[2] - bb[0]
    cx = (1920 - cw) // 2
    draw.rounded_rectangle([(cx - 30, 350), (cx + cw + 30, 500)], radius=20, fill=(120, 40, 200, 230))
    draw.text((960, 425), cat_text, fill=(255, 255, 255), font=f_cat, anchor="mm")

    draw.rounded_rectangle([(960 - 200, 580), (960 + 200, 670)], radius=15, fill=(0, 0, 0, 180))
    draw.text((960, 625), "10 MINUTE LESSON", fill=(255, 210, 0), font=f_sub, anchor="mm")

    brand_text = "VELOCITY POLISH"
    bb = draw.textbbox((0, 0), brand_text, font=f_brand)
    draw.text(((1920 - (bb[2] - bb[0])) // 2, 950), brand_text, fill=(200, 200, 200), font=f_brand)

    thumb_bytes = io.BytesIO()
    quality = 85
    img.save(thumb_bytes, format="JPEG", quality=quality)
    while thumb_bytes.tell() > 2097152 and quality > 10:
        quality -= 10
        thumb_bytes = io.BytesIO()
        img.save(thumb_bytes, format="JPEG", quality=quality)
    thumb_bytes.seek(0)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(thumb_bytes.read())
    print(f"[thumbnail] Fallback thumbnail saved (AI unavailable)")
    return output_path
