#!/usr/bin/env python3
"""Generate sample images in different styles for Chapter 1 & 2 using OpenAI and MiniMax."""
import os, json, base64, requests, time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

openai_client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
MINIMAX_TOKEN = os.environ['MINIMAX_API_TOKEN']

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'images', 'samples')
os.makedirs(OUT_DIR, exist_ok=True)

# Load character data
with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'characters.json')) as f:
    char_data = json.load(f)

def get_char_desc(char_id):
    for c in char_data['characters']:
        if c['id'] == char_id:
            return f"{c['name']}: {c['visualDescription']}"
    return ""

# Chapter 1 scene
CH1_SCENE = {
    "title": "Questions by the Sages",
    "verse": "oṁ namo bhagavate vāsudevāya",
    "translation": "O my Lord, Śrī Kṛṣṇa, son of Vasudeva, I offer my respectful obeisances unto You.",
    "characters": ["suta", "shaunaka", "vyasa"],
    "setting": "The sages of Naimishāranya forest are gathered around a sacred fire, asking Sūta Goswāmī about the Supreme Lord. Ancient banyan trees tower above, golden sunlight filters through the canopy."
}

# Chapter 2 scene
CH2_SCENE = {
    "title": "Divinity and Divine Service",
    "verse": "dharmaḥ projjhita-kaitavo 'tra",
    "translation": "Completely rejecting all religious activities which are materially motivated, this Bhāgavata Purāṇa propounds the highest truth.",
    "characters": ["suta", "shaunaka"],
    "setting": "Sūta Goswāmī continues his discourse to the assembled sages at Naimishāranya. The sacred fire burns bright as dawn breaks. The sages listen with rapt attention."
}

# ── 5 different style prompts for Chapter 1 ──

STYLES = {
    "style1_tanjore": {
        "name": "Traditional Tanjore Painting",
        "style": "Traditional South Indian Tanjore painting style. Rich jewel-tone colors with actual gold leaf accents on ornaments and halos. Intricate ornamental borders with temple motifs. Divine figures with serene expressions, elongated almond-shaped eyes, and idealized proportions. Warm golden divine light illuminating the scene. Flat perspective with layered composition typical of classical Indian temple art. Decorated architectural elements. Sacred, luminous, devotional atmosphere."
    },
    "style2_mughal": {
        "name": "Mughal Miniature",
        "style": "Indian Mughal miniature painting style. Extremely fine detailed brushwork, vivid saturated colors, delicate facial features with precise linework. Birds-eye perspective with multiple planes of depth. Lush garden and nature elements with individually painted leaves. Decorative floral borders. Figures shown in three-quarter profile with expressive gestures. Gold accents on textiles and architecture. The feeling of a precious illuminated manuscript page."
    },
    "style3_modern_indian": {
        "name": "Modern Indian Art (Raja Ravi Varma inspired)",
        "style": "Realistic Indian art in the style of Raja Ravi Varma — oil painting technique with Indian subjects. Photorealistic skin tones and fabric draping, dramatic chiaroscuro lighting, European Renaissance composition with authentic Indian costume and setting details. Rich silk garments with realistic folds and sheen. Atmospheric perspective with misty forest background. Emotional, dignified expressions. Museum-quality fine art painting."
    },
    "style4_watercolor": {
        "name": "Sacred Watercolor Illustration",
        "style": "Ethereal watercolor illustration with soft, luminous washes of color. Gentle bleeding of saffron, gold, and deep blue pigments. Delicate ink linework for facial features and ornament details over watercolor base. Spiritual, dreamlike atmosphere with areas of white paper showing through as divine light. Loose, flowing brushwork for garments and foliage, with precise detail only on faces and hands. Meditative, peaceful, and sacred mood."
    },
    "style5_digital_epic": {
        "name": "Epic Digital Art (Concept Art)",
        "style": "Cinematic digital concept art with epic scale. Dramatic volumetric lighting with god-rays breaking through ancient forest canopy. Highly detailed character designs with authentic Indian ornaments and garments. Rich atmospheric perspective with depth of field. Warm color grading with deep shadows and bright highlights. Professional illustration quality suitable for a high-end fantasy book cover or game art. Sacred and awe-inspiring mood."
    }
}


def build_prompt(scene, style_desc):
    chars = "\n".join([get_char_desc(c) for c in scene["characters"]])
    return f"""Create an illustration for this scene from the Srimad Bhagavatam.

SCENE: {scene['title']}
{scene['setting']}

VERSE: "{scene['translation']}"

CHARACTERS IN SCENE (match these descriptions EXACTLY for face, skin color, clothing, and attributes):
{chars}

ART STYLE: {style_desc}

CRITICAL RULES:
- Every character's skin tone, facial features, clothing, and held objects must match their description exactly
- The scene must feel sacred, spiritual, and devotional
- No text or writing in the image
- Single cohesive composition with all characters naturally placed in the scene"""


def generate_openai(prompt, filename, quality="low"):
    """Generate image using OpenAI gpt-image-1."""
    print(f"  [OpenAI] Generating {filename}...")
    try:
        response = openai_client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality=quality,
        )
        b64 = response.data[0].b64_json
        if b64:
            path = os.path.join(OUT_DIR, filename)
            with open(path, 'wb') as f:
                f.write(base64.b64decode(b64))
            print(f"    ✓ Saved: {path}")
            return True
    except Exception as e:
        print(f"    ✗ Failed: {e}")
    return False


def generate_minimax(prompt, filename):
    """Generate image using MiniMax image-01."""
    print(f"  [MiniMax] Generating {filename}...")
    try:
        resp = requests.post(
            "https://api.minimax.io/v1/image_generation",
            headers={
                "Authorization": f"Bearer {MINIMAX_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "model": "image-01",
                "prompt": prompt,
                "aspect_ratio": "1:1",
                "response_format": "base64",
                "n": 1,
                "prompt_optimizer": True
            },
            timeout=120
        )
        data = resp.json()
        if data.get("base_resp", {}).get("status_code", -1) != 0:
            print(f"    ✗ API error: {data.get('base_resp', {}).get('status_msg', 'unknown')}")
            return False
        images = data.get("data", {}).get("image_base64", [])
        if images:
            path = os.path.join(OUT_DIR, filename)
            with open(path, 'wb') as f:
                f.write(base64.b64decode(images[0]))
            print(f"    ✓ Saved: {path}")
            return True
        else:
            print(f"    ✗ No image data in response")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
    return False


if __name__ == "__main__":
    print("=" * 60)
    print("CHAPTER 1: Questions by the Sages")
    print("=" * 60)

    # Generate 5 OpenAI styles for Chapter 1
    for key, style in STYLES.items():
        print(f"\n── {style['name']} ──")
        prompt = build_prompt(CH1_SCENE, style["style"])
        generate_openai(prompt, f"ch1_openai_{key}.png")
        time.sleep(2)

    # Generate 5 MiniMax styles for Chapter 1
    for key, style in STYLES.items():
        print(f"\n── {style['name']} (MiniMax) ──")
        prompt = build_prompt(CH1_SCENE, style["style"])
        generate_minimax(prompt, f"ch1_minimax_{key}.png")
        time.sleep(2)

    print("\n" + "=" * 60)
    print("CHAPTER 2: Divinity and Divine Service")
    print("=" * 60)

    # Generate all 5 styles for Chapter 2 with both APIs (for continuity check)
    for key, style in STYLES.items():
        print(f"\n── {style['name']} ──")
        prompt = build_prompt(CH2_SCENE, style["style"])
        generate_openai(prompt, f"ch2_openai_{key}.png")
        time.sleep(2)
        generate_minimax(prompt, f"ch2_minimax_{key}.png")
        time.sleep(2)

    print("\n" + "=" * 60)
    print("DONE! Images saved to: " + OUT_DIR)
    print("=" * 60)

    # Summary
    files = [f for f in os.listdir(OUT_DIR) if f.endswith('.png')]
    print(f"\nTotal images generated: {len(files)}")
    for f in sorted(files):
        size_kb = os.path.getsize(os.path.join(OUT_DIR, f)) // 1024
        print(f"  {f} ({size_kb} KB)")
