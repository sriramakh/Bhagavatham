#!/usr/bin/env python3
"""
Build complete lesson content for all Skandhas by:
1. Extracting chapter info from the English PDF
2. Generating lesson content via GPT-4o-mini for each chapter
3. Assembling into the final verses.json

This produces STATIC content shared by ALL users.
"""
import fitz
import json
import os
import re
import time
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))
client = OpenAI()

PDF_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'srimad-bhagavata-mahapurana-english-translations.pdf')
VERSES_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'verses.json')
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'generated-lessons')
CHARACTERS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'characters.json')

# Bhagavatam structure: 12 Skandhas, 335 chapters total
SKANDHA_INFO = {
    1: {"name": "Creation", "nameDevanagari": "सृष्टि", "desc": "The first canto introduces the purpose of the Bhagavatam and the fundamental questions of existence."},
    2: {"name": "The Cosmic Manifestation", "nameDevanagari": "विश्वरचना", "desc": "Describes the cosmic form of the Lord, creation, and the science of God-realization."},
    3: {"name": "The Status Quo", "nameDevanagari": "यथास्थिति", "desc": "Vidura's pilgrimage, creation by Vishnu, the appearance of Lord Kapila, and His teachings to Devahuti."},
    4: {"name": "The Creation of the Fourth Order", "nameDevanagari": "चतुर्थ सृष्टि", "desc": "Stories of Dhruva, Prithu, Daksha, and the importance of devotion over ritual."},
    5: {"name": "The Creative Impetus", "nameDevanagari": "सृष्टि प्रेरणा", "desc": "Description of the universe's structure, the story of Rishabhadeva and King Bharata."},
    6: {"name": "Prescribed Duties", "nameDevanagari": "विहित कर्म", "desc": "The story of Ajamila, Daksha's prayers, Indra vs Vritrasura, and the power of the holy name."},
    7: {"name": "The Science of God", "nameDevanagari": "ईश्वर विज्ञान", "desc": "The story of Prahlada and Narasimha, and detailed teachings on devotional service."},
    8: {"name": "Withdrawal of the Cosmic Creations", "nameDevanagari": "सृष्टि प्रत्याहार", "desc": "The Gajendra-moksha, churning of the ocean, Vamana avatar, and the Manu dynasties."},
    9: {"name": "Liberation", "nameDevanagari": "मुक्ति", "desc": "The dynasties of the Sun and Moon, stories of Lord Ramachandra and other incarnations."},
    10: {"name": "The Summum Bonum", "nameDevanagari": "परम तत्त्व", "desc": "The complete pastimes of Lord Krishna — His birth, childhood, youth, and divine activities."},
    11: {"name": "General History", "nameDevanagari": "सामान्य इतिहास", "desc": "Krishna's final teachings (Uddhava Gita), the destruction of the Yadu dynasty, and the Lord's departure."},
    12: {"name": "The Age of Deterioration", "nameDevanagari": "कलियुग", "desc": "The age of Kali, the future avatars, the essence of all Puranas, and the glory of the Bhagavatam."},
}


def extract_chapters_from_pdf():
    """Extract chapter titles and first verse text from the English PDF."""
    doc = fitz.open(PDF_PATH)
    full_text = ""
    for i in range(len(doc)):
        full_text += doc[i].get_text() + "\n"

    chapters = []
    # Pattern: "SB X.Y: Chapter Title" or "SB X.Y.Z: ..."
    # Also: "Canto N:" headers
    sb_pattern = re.compile(r'SB\s+(\d+)\.(\d+):\s*(.+?)(?:\n|$)')

    for match in sb_pattern.finditer(full_text):
        skandha = int(match.group(1))
        chapter = int(match.group(2))
        title = match.group(3).strip()

        # Get some text after this match for context (first ~1000 chars)
        start = match.end()
        sample_text = full_text[start:start+1500].strip()
        # Clean up
        sample_text = re.sub(r'\n+', ' ', sample_text)
        sample_text = sample_text[:1000]

        chapters.append({
            "skandha": skandha,
            "chapter": chapter,
            "title": title,
            "sample_text": sample_text
        })

    return chapters


def generate_lesson(skandha, chapter, title, sample_text):
    """Generate full lesson content using GPT-4o-mini."""
    cache_file = os.path.join(CACHE_DIR, f'{skandha}-{chapter}.json')
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Load character list
    with open(CHARACTERS_PATH, 'r') as f:
        char_data = json.load(f)
    char_names = [c['id'] for c in char_data['characters']]

    prompt = f"""Generate a complete lesson for a gamified Bhagavatam learning app.

Skandha {skandha}, Chapter {chapter}: "{title}"

Sample verse text from this chapter:
{sample_text}

OUTPUT VALID JSON with this EXACT structure:
{{
  "id": "{skandha}-{chapter}",
  "skandha": {skandha},
  "num": {chapter},
  "title": "{title}",
  "desc": "One sentence description",
  "characters": ["character_ids from: {', '.join(char_names)}"],
  "story": [
    {{"type": "narration", "text": "Engaging narrative text..."}},
    {{"type": "dialogue", "speaker": "Character Name", "text": "Dialogue..."}},
    // 5-6 story beats total, make it vivid and engaging
  ],
  "verse": {{
    "ref": "Srimad Bhagavatam {skandha}.{chapter}.X",
    "sanskrit": "The most important verse from this chapter in Devanagari",
    "transliteration": "IAST transliteration",
    "translation": "English translation",
    "syllables": ["each", "Devanagari", "syllable"],
    "words": [
      // EVERY word from the verse - include ALL of them
      {{"san": "देवनागरी", "trans": "transliteration", "mean": "meaning", "full": "detailed explanation"}}
    ]
  }},
  "madhvaTeaching": "Madhvacharya's Dvaita interpretation (2-3 sentences, reference specific Sanskrit terms, explain how Dvaita differs from Advaita on this verse)",
  "sanskritWords": [
    // Same words with example field
    {{"san": "देवनागरी", "trans": "transliteration", "mean": "meaning", "example": "usage in verse"}}
  ],
  "quiz": [
    // 5 questions: mix of mcq, fill, match
    {{"type": "mcq", "question": "...", "options": ["A","B","C","D"], "correct": 0, "explanation": "..."}},
    {{"type": "fill", "question": "sentence with ___", "answer": "Sanskrit word", "options": ["4 choices in Devanagari"], "explanation": "..."}},
    {{"type": "match", "question": "Match:", "pairs": [["संस्कृत","English"],["संस्कृत","English"],["संस्कृत","English"]], "explanation": "..."}}
  ],
  "boss": [
    // 4 harder comprehensive questions testing deeper understanding
    {{"type": "mcq", "question": "...", "options": ["A","B","C","D"], "correct": 0, "explanation": "..."}}
  ]
}}

RULES:
- The key verse MUST be in actual Devanagari script, not transliteration
- Include EVERY Sanskrit word from the verse, not just important ones
- Story should be vivid narrative, not dry summary
- Madhva's teaching must specifically highlight Dvaita philosophy
- Quiz must test both story comprehension AND Sanskrit vocabulary
- All Sanskrit in quiz options should be in Devanagari"""

    sys_msg = 'You are a Sanskrit scholar creating educational content about the Srimad Bhagavatam from Madhvacharya Dvaita perspective. Output ONLY valid JSON. No markdown fences, no explanations.'
    msgs = [
        {'role': 'system', 'content': sys_msg},
        {'role': 'user', 'content': prompt}
    ]
    response = client.chat.completions.create(
        model='gpt-4.1',
        messages=msgs,
        max_tokens=8192,
        temperature=0.5,
    )

    text = response.choices[0].message.content.strip()
    # Remove markdown fences if present
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
    if text.endswith('```'):
        text = text.rsplit('```', 1)[0]
    if text.startswith('json\n'):
        text = text[5:]

    try:
        lesson = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"    JSON parse error for {skandha}-{chapter}: {e}")
        print(f"    Raw text (first 200): {text[:200]}")
        return None

    # Cache
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(lesson, f, ensure_ascii=False, indent=2)

    return lesson


def build_verses_json(chapters_from_pdf, generated_lessons):
    """Assemble the final verses.json with all content."""
    # Load existing verses.json to preserve manually curated chapters
    existing = {}
    if os.path.exists(VERSES_PATH):
        with open(VERSES_PATH, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            for sk in existing_data.get('skandhas', []):
                for ch in sk.get('chapters', []):
                    if ch.get('verse') and ch.get('story'):  # Has real content
                        existing[ch['id']] = ch

    skandhas = []
    for sk_num in range(1, 13):
        info = SKANDHA_INFO[sk_num]
        sk_chapters = [c for c in chapters_from_pdf if c['skandha'] == sk_num]
        sk_chapters.sort(key=lambda c: c['chapter'])

        chapter_data = []
        for ch_info in sk_chapters:
            ch_id = f"{sk_num}-{ch_info['chapter']}"

            # Prefer existing manually curated content
            if ch_id in existing:
                chapter_data.append(existing[ch_id])
                continue

            # Use generated content
            if ch_id in generated_lessons and generated_lessons[ch_id]:
                lesson = generated_lessons[ch_id]
                chapter_data.append(lesson)
            else:
                # Stub
                chapter_data.append({
                    "id": ch_id,
                    "skandha": sk_num,
                    "num": ch_info['chapter'],
                    "title": ch_info['title'],
                    "desc": f"Chapter {ch_info['chapter']} of Skandha {sk_num}.",
                    "status": "coming_soon"
                })

        skandhas.append({
            "number": sk_num,
            "name": info["name"],
            "nameDevanagari": info["nameDevanagari"],
            "description": info["desc"],
            "chapters": chapter_data
        })

    result = {"skandhas": skandhas}

    with open(VERSES_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Build all lesson content')
    parser.add_argument('--skandha', type=int, help='Generate only this skandha (1-12)')
    parser.add_argument('--dry-run', action='store_true', help='Extract chapters but don\'t generate')
    parser.add_argument('--max-chapters', type=int, default=999, help='Max chapters to generate per skandha')
    parser.add_argument('--delay', type=float, default=1.5, help='Delay between API calls (seconds)')
    args = parser.parse_args()

    print("Step 1: Extracting chapters from English PDF...")
    chapters = extract_chapters_from_pdf()
    print(f"  Found {len(chapters)} chapters across all skandhas")

    # Summary by skandha
    for sk in range(1, 13):
        count = len([c for c in chapters if c['skandha'] == sk])
        if count > 0:
            print(f"  Skandha {sk:2d}: {count} chapters")

    if args.dry_run:
        print("\nDry run — not generating lessons.")
        # Still build verses.json with stubs
        build_verses_json(chapters, {})
        print(f"Wrote stub verses.json to {VERSES_PATH}")
        return

    # Filter by skandha if specified
    if args.skandha:
        chapters = [c for c in chapters if c['skandha'] == args.skandha]
        print(f"\nFiltered to Skandha {args.skandha}: {len(chapters)} chapters")

    print(f"\nStep 2: Generating lesson content ({len(chapters)} chapters)...")
    generated = {}
    for i, ch in enumerate(chapters):
        if i >= args.max_chapters and args.skandha:
            break

        ch_id = f"{ch['skandha']}-{ch['chapter']}"
        cache_file = os.path.join(CACHE_DIR, f'{ch_id}.json')

        if os.path.exists(cache_file):
            print(f"  [{i+1}/{len(chapters)}] {ch_id} '{ch['title']}' — cached ✓")
            with open(cache_file, 'r', encoding='utf-8') as f:
                generated[ch_id] = json.load(f)
            continue

        print(f"  [{i+1}/{len(chapters)}] {ch_id} '{ch['title']}' — generating...")

        try:
            lesson = generate_lesson(ch['skandha'], ch['chapter'], ch['title'], ch['sample_text'])
            if lesson:
                generated[ch_id] = lesson
                print(f"    ✓ {len(lesson.get('sanskritWords', []))} words, {len(lesson.get('quiz', []))} quiz Qs")
            else:
                print(f"    ✗ Generation failed")
        except Exception as e:
            print(f"    ✗ Error: {e}")

        time.sleep(args.delay)

    print(f"\nStep 3: Assembling verses.json...")
    # Load ALL cached lessons (including from previous runs)
    os.makedirs(CACHE_DIR, exist_ok=True)
    for f in os.listdir(CACHE_DIR):
        if f.endswith('.json'):
            ch_id = f.replace('.json', '')
            if ch_id not in generated:
                with open(os.path.join(CACHE_DIR, f), 'r', encoding='utf-8') as fh:
                    try:
                        generated[ch_id] = json.load(fh)
                    except:
                        pass

    result = build_verses_json(chapters, generated)

    # Final stats
    total_ready = 0
    total_stub = 0
    for sk in result['skandhas']:
        for ch in sk['chapters']:
            if ch.get('status') == 'coming_soon':
                total_stub += 1
            else:
                total_ready += 1

    print(f"\nDone!")
    print(f"  Ready: {total_ready} chapters")
    print(f"  Stubs: {total_stub} chapters")
    print(f"  Total: {total_ready + total_stub} chapters")
    print(f"  Saved to: {VERSES_PATH}")


if __name__ == '__main__':
    main()
