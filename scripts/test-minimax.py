#!/usr/bin/env python3
"""Generate MiniMax sample images with condensed prompts (1500 char limit)."""
import os, json, base64, requests, time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
MINIMAX_TOKEN = os.environ['MINIMAX_API_TOKEN']
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'images', 'samples')
os.makedirs(OUT_DIR, exist_ok=True)

# Condensed prompts under 1500 chars for MiniMax
PROMPTS = {
    "ch1_minimax_style1_tanjore": """Traditional South Indian Tanjore painting of sages at Naimisharanya forest. Sacred fire burning in a clearing under ancient banyan trees. Golden sunlight filtering through canopy.

Main figure: Suta Goswami, middle-aged Indian sage with brown skin, saffron robes, shaved head with shikha tuft, sacred thread, sitting cross-legged teaching.
Opposite him: Shaunaka Rishi, elderly sage with white beard, bark-cloth garments, saffron shawl, rudraksha beads.
Behind: Vyasadeva, elderly sage with dark skin, grey matted hair, white garments, holding palm-leaf manuscripts.

Tanjore style: jewel-tone colors, gold leaf accents on halos and ornaments, ornamental borders with temple motifs, elongated almond eyes, flat perspective, sacred luminous atmosphere. Scene from Srimad Bhagavatam. No text.""",

    "ch1_minimax_style2_mughal": """Mughal miniature painting of Indian sages gathered around sacred fire in ancient forest. Fine detailed brushwork, vivid saturated colors, decorative floral border.

Suta Goswami teaching: brown skin, saffron robes, shaved head. Shaunaka: elderly, white beard, deerskin garments. Vyasadeva: dark skin, grey hair, white robes, manuscripts.

Multiple sages listening intently on grass mats. Banyan trees with individually painted leaves. Golden dawn light. Birds-eye perspective with multiple depth planes. Precious illuminated manuscript quality. Sacred spiritual scene from Srimad Bhagavatam. No text in image.""",

    "ch1_minimax_style3_ravi_varma": """Oil painting in Raja Ravi Varma style of Indian sages in Naimisharanya forest. Photorealistic skin, dramatic chiaroscuro lighting, Renaissance composition.

Central: Suta Goswami, brown skin, saffron robes, teaching gesture. Shaunaka: elderly, white beard, saffron shawl, listening. Vyasadeva: dark skin, grey hair, white garments, palm manuscripts.

Sacred fire between them. Rich silk garments with realistic folds. Misty forest background with ancient trees. Atmospheric perspective. Dignified, emotional expressions. Museum-quality fine art. Srimad Bhagavatam scene. No text.""",

    "ch1_minimax_style4_watercolor": """Ethereal watercolor illustration of Indian sages gathered in ancient forest around sacred fire. Soft luminous washes of saffron, gold, and deep blue. Delicate ink linework for faces over watercolor base.

Suta Goswami in saffron robes teaching. Shaunaka elderly sage listening. Vyasadeva with manuscripts. Gentle bleeding of pigments. White paper showing as divine light. Loose brushwork for garments, precise detail on faces. Meditative sacred mood. Srimad Bhagavatam. No text.""",

    "ch1_minimax_style5_digital": """Cinematic digital concept art of ancient Indian sages gathered around sacred fire in mystical forest. Epic scale. Dramatic god-rays through canopy. Volumetric lighting.

Suta Goswami: brown skin, saffron robes, sacred thread, teaching. Shaunaka: elderly, white beard, bark garments. Vyasadeva: dark skin, grey matted hair, manuscripts.

Detailed Indian ornaments and garments. Warm color grading, deep shadows, bright highlights. Professional fantasy illustration quality. Sacred awe-inspiring mood. Srimad Bhagavatam. No text.""",

    # Chapter 2 scenes (same characters for continuity testing)
    "ch2_minimax_style1_tanjore": """Traditional South Indian Tanjore painting. Suta Goswami continues teaching at Naimisharanya. Dawn breaks over the forest, sacred fire burning bright.

Suta Goswami: middle-aged, brown skin, saffron robes, shaved head with shikha, sacred thread, animated teaching pose with expressive hand mudras.
Shaunaka Rishi: elderly, white beard, bark-cloth and saffron shawl, rudraksha mala, rapt attention.
Other sages seated in semicircle on grass mats.

Tanjore style: jewel-tone colors, gold accents on halos and ornaments, ornamental temple borders, elongated almond eyes, sacred luminous atmosphere. Srimad Bhagavatam Chapter 2: Divinity and Divine Service. No text.""",

    "ch2_minimax_style5_digital": """Cinematic digital art of Suta Goswami teaching at dawn in Naimisharanya forest. Sacred fire glowing bright. God-rays through ancient trees.

Suta: brown skin, saffron robes, sacred thread, animated teaching. Shaunaka: elderly, white beard, bark garments, listening intently. Circle of sages.

Warm dawn colors. Volumetric lighting. Detailed Indian ornaments and garments. Professional concept art quality. Sacred awe-inspiring mood. Srimad Bhagavatam Chapter 2. No text.""",
}

def generate_minimax(prompt, filename):
    print(f"  Generating {filename}... ({len(prompt)} chars)")
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
        status = data.get("base_resp", {}).get("status_code", -1)
        if status != 0:
            print(f"    ✗ Error: {data.get('base_resp', {}).get('status_msg', 'unknown')}")
            return False
        images = data.get("data", {}).get("image_base64", [])
        if images:
            path = os.path.join(OUT_DIR, filename + ".png")
            with open(path, 'wb') as f:
                f.write(base64.b64decode(images[0]))
            print(f"    ✓ Saved ({os.path.getsize(path)//1024} KB)")
            return True
    except Exception as e:
        print(f"    ✗ Failed: {e}")
    return False

if __name__ == "__main__":
    print("Generating MiniMax images...\n")
    for name, prompt in PROMPTS.items():
        generate_minimax(prompt, name)
        time.sleep(2)

    print("\nDone!")
    files = sorted([f for f in os.listdir(OUT_DIR) if 'minimax' in f])
    print(f"MiniMax images: {len(files)}")
    for f in files:
        print(f"  {f} ({os.path.getsize(os.path.join(OUT_DIR, f))//1024} KB)")
