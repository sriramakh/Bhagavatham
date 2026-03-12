#!/usr/bin/env python3
"""Generate Tanjore-style images for all chapters using MiniMax image-01."""
import os, json, base64, requests, time, sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
MINIMAX_TOKEN = os.environ['MINIMAX_API_TOKEN']

SCRIPT_DIR = os.path.dirname(__file__)
CACHE_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'generated-lessons')
CHAR_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'characters.json')
IMG_DIR = os.path.join(SCRIPT_DIR, '..', 'public', 'images', 'verses')
os.makedirs(IMG_DIR, exist_ok=True)

# Load character data
with open(CHAR_PATH) as f:
    char_data = json.load(f)

# Condensed character descriptions (MiniMax has 1500 char limit)
CHAR_SHORT = {
    "krishna": "Lord Krishna: young male deity with deep blue-black skin, lotus eyes, enigmatic smile, golden crown with peacock feather, yellow silk dhoti, garland of wildflowers, holding flute, tribhanga pose",
    "vishnu": "Lord Vishnu: majestic blue-black skin deity, four arms holding conch/discus/mace/lotus, elaborate golden crown, kaustubha gem on chest, yellow silk, seated on serpent Shesha",
    "brahma": "Lord Brahma: elderly deity with four faces, reddish-golden skin, white beard, four arms holding Vedas/water pot/rosary/lotus, white garments, seated on lotus",
    "shiva": "Lord Shiva: ash-smeared fair skin, matted dreadlocks with crescent moon, third eye, tiger skin, serpent ornaments, holding trident and damaru drum",
    "suta": "Suta Goswami: middle-aged sage, warm brown skin, saffron robes, shaved head with shikha tuft, sacred thread, gentle smile, teaching mudra",
    "shaunaka": "Shaunaka Rishi: elderly sage, brown skin, long white beard, bark-cloth with saffron shawl, rudraksha mala, dignified posture",
    "vyasa": "Vyasadeva: elderly sage, dark brown skin, long grey matted hair, grey beard, powerful build, white garments, palm-leaf manuscripts",
    "shukadeva": "Shukadeva Goswami: youth of 16, luminous fair skin, shaved head, only a loincloth, large innocent eyes, glowing with spiritual light",
    "parikshit": "King Parikshit: noble young king, fair golden-brown skin, simple white garments, strong regal features, sitting by the Ganges, devoted expression",
    "narada": "Narada Muni: eternally youthful, golden-fair skin, carrying veena, white garments, shikha on shaved head, ecstatic smile, slender",
    "madhvacharya": "Madhvacharya: powerfully built, dark brown skin, broad shoulders, shaved head with Vaishnava tilaka, saffron sannyasi robes, holding scriptures, commanding expression",
}

TANJORE_STYLE = "Traditional South Indian Tanjore painting style. Rich jewel-tone colors with gold leaf accents on ornaments, halos, and borders. Intricate ornamental temple-motif borders. Divine figures with serene expressions, elongated almond-shaped eyes. Warm golden divine light. Flat perspective, layered composition. Sacred, luminous, devotional atmosphere."


def build_prompt(chapter):
    """Build a condensed Tanjore prompt under 1500 chars."""
    title = chapter.get('title', 'Sacred Scene')
    desc = chapter.get('desc', '')

    # Get scene from story beats
    scene_parts = []
    for beat in chapter.get('story', [])[:2]:
        if beat.get('type') == 'narration':
            scene_parts.append(beat['text'][:150])
    scene = ' '.join(scene_parts)[:200] if scene_parts else desc[:200]

    # Get characters
    char_ids = chapter.get('characters', [])
    char_descs = []
    for cid in char_ids[:3]:  # Max 3 characters to stay under limit
        if cid in CHAR_SHORT:
            char_descs.append(CHAR_SHORT[cid])

    chars_text = '\n'.join(char_descs) if char_descs else "Indian sages in saffron robes gathered around sacred fire in ancient forest"

    # Get verse translation
    verse = chapter.get('verse', {})
    translation = verse.get('translation', '')[:120]

    prompt = f"""Tanjore painting of scene from Srimad Bhagavatam: "{title}"

Scene: {scene}
{f'Verse: "{translation}"' if translation else ''}

Characters (match exactly):
{chars_text}

Style: {TANJORE_STYLE}
No text or writing in the image."""

    # Truncate to 1500 if needed
    if len(prompt) > 1490:
        prompt = prompt[:1487] + "..."

    return prompt


def generate_image(prompt, filename):
    """Generate image via MiniMax API."""
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
            msg = data.get('base_resp', {}).get('status_msg', 'unknown')
            return False, f"API error: {msg}"

        images = data.get("data", {}).get("image_base64", [])
        if images:
            path = os.path.join(IMG_DIR, filename)
            with open(path, 'wb') as f:
                f.write(base64.b64decode(images[0]))
            size_kb = os.path.getsize(path) // 1024
            return True, f"{size_kb} KB"
        return False, "No image data"
    except Exception as e:
        return False, str(e)


def main():
    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0

    # Collect all available chapters from cache
    lesson_files = sorted(os.listdir(CACHE_DIR), key=lambda f: (
        int(f.replace('.json', '').split('-')[0]),
        int(f.replace('.json', '').split('-')[1])
    ))

    chapters = []
    for fname in lesson_files:
        if not fname.endswith('.json'):
            continue
        ch_id = fname.replace('.json', '')
        with open(os.path.join(CACHE_DIR, fname)) as f:
            ch = json.load(f)
        # Skip if it looks like a stub/failed generation
        if ch.get('status') == 'coming_soon' or not ch.get('story'):
            continue
        chapters.append((ch_id, ch))

    print(f"Found {len(chapters)} chapters with content")
    print(f"Image output: {IMG_DIR}")
    print(f"Delay between calls: {delay}s")
    print("=" * 60)

    generated = 0
    skipped = 0
    failed = 0
    failed_list = []

    for i, (ch_id, chapter) in enumerate(chapters):
        # Check if image already exists
        filename = f"chapter_{ch_id}.png"
        filepath = os.path.join(IMG_DIR, filename)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            print(f"  [{i+1}/{len(chapters)}] {ch_id} '{chapter.get('title', '')[:40]}' — cached")
            skipped += 1
            continue

        prompt = build_prompt(chapter)
        print(f"  [{i+1}/{len(chapters)}] {ch_id} '{chapter.get('title', '')[:40]}' — generating... ({len(prompt)} chars)")

        ok, msg = generate_image(prompt, filename)
        if ok:
            print(f"    ✓ {msg}")
            generated += 1
        else:
            print(f"    ✗ {msg}")
            failed += 1
            failed_list.append(ch_id)

        time.sleep(delay)

    print("\n" + "=" * 60)
    print(f"DONE: {generated} generated, {skipped} cached, {failed} failed")
    if failed_list:
        print(f"Failed chapters: {', '.join(failed_list)}")
    print(f"Total images in {IMG_DIR}: {len([f for f in os.listdir(IMG_DIR) if f.endswith('.png')])}")


if __name__ == "__main__":
    main()
