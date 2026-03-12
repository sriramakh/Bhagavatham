#!/usr/bin/env python3
"""
Regenerate lessons using actual verse-by-verse text from the English PDF.
Fixes: truncated translations, hallucinated Sanskrit, incomplete word breakdowns.

The English PDF has complete translations per verse but no Devanagari.
We extract all verses per chapter and feed them to GPT-4o-mini with strict instructions.
"""
import os, sys, json, time, re, fitz
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

SCRIPT_DIR = os.path.dirname(__file__)
CACHE_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'generated-lessons')
PDF_PATH = os.path.join(SCRIPT_DIR, '..', '..', 'srimad-bhagavata-mahapurana-english-translations.pdf')

client = OpenAI()
os.makedirs(CACHE_DIR, exist_ok=True)


def extract_chapter_verses(doc, skandha, chapter):
    """Extract all individual verse translations for a chapter from the PDF."""
    full_text = ""
    target = f"SB {skandha}.{chapter}:"
    next_ch = f"SB {skandha}.{chapter+1}:"
    next_sk = f"SB {skandha+1}.1:"

    capturing = False
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        if target in text:
            capturing = True
        if capturing:
            full_text += text + "\n"
            if len(full_text) > 500 and (next_ch in full_text[len(target):] or next_sk in full_text[len(target):]):
                break
        if len(full_text) > 15000:
            break

    # Trim to chapter boundaries
    start = full_text.find(target)
    if start > 0:
        full_text = full_text[start:]

    for marker in [next_ch, next_sk]:
        end = full_text.find(marker, len(target))
        if end > 0:
            full_text = full_text[:end]

    # Extract chapter title
    title_match = re.search(r'SB \d+\.\d+:\s*(.+?)(?:\n|$)', full_text)
    title = title_match.group(1).strip() if title_match else ""

    # Extract individual verses
    verses = []
    # Match verse numbers at start of line or after newline
    parts = re.split(r'\n(\d+)[:\s]', full_text)

    # parts[0] is header, then alternating [verse_num, verse_text, ...]
    for i in range(1, len(parts)-1, 2):
        verse_num = parts[i].strip()
        verse_text = parts[i+1].strip()
        # Clean up
        verse_text = ' '.join(verse_text.split())
        if len(verse_text) > 20:  # skip noise
            verses.append({"num": int(verse_num), "text": verse_text})

    return title, verses, full_text[:8000]


PROMPT = """You are a Sanskrit scholar creating educational content for a Srimad Bhagavatam learning app.

SKANDHA {skandha}, CHAPTER {chapter}: "{title}"

ACTUAL VERSE TRANSLATIONS FROM THE AUTHORITATIVE TEXT:
{verse_texts}

FULL CHAPTER TEXT:
{chapter_text}

Generate a COMPLETE lesson using the actual verse content above. Choose the MOST IMPORTANT verse from this chapter as the key verse.

Output VALID JSON:
{{
  "id": "{skandha}-{chapter}",
  "skandha": {skandha},
  "num": {chapter},
  "title": "{title}",
  "desc": "One engaging sentence (from the actual content above, not generic)",
  "characters": ["suta", "shaunaka"],
  "story": [
    // 5-6 beats. Use ACTUAL events and dialogue from the verses above.
    // Do NOT make up events that aren't in the chapter.
    {{"type": "narration", "text": "..."}},
    {{"type": "dialogue", "speaker": "Character", "text": "..."}}
  ],
  "verse": {{
    "ref": "Srimad Bhagavatam {skandha}.{chapter}.N",
    "sanskrit": "ACCURATE Devanagari of the chosen key verse. Use the well-known standard text.",
    "transliteration": "Accurate IAST transliteration matching the Devanagari",
    "translation": "USE THE EXACT COMPLETE TRANSLATION FROM THE PDF TEXT ABOVE. Do NOT summarize or truncate. Copy it faithfully.",
    "syllables": ["each", "Devanagari", "syllable"],
    "words": [
      // EVERY Sanskrit word from the verse. Each MUST have all 4 fields:
      {{"san": "देवनागरी", "trans": "IAST", "mean": "2-3 word meaning", "full": "1-2 sentence contextual explanation"}}
    ]
  }},
  "madhvaTeaching": "3-4 sentences on Madhvacharya's Dvaita interpretation. Reference: jīva-Brahma bheda, viṣṇu-sarvottamatva, pañca-bheda. Use Sanskrit terms with translations in parentheses.",
  "sanskritWords": [
    // ALL words from verse.words PLUS 3-5 additional important terms from the chapter.
    // Each MUST have all 5 fields:
    {{"san": "देवनागरी", "trans": "IAST", "mean": "meaning", "full": "Detailed explanation with etymology", "example": "usage from the verse"}}
  ],
  "quiz": [
    // 5 questions testing vocabulary AND comprehension of the actual chapter content
    {{"type": "mcq", "question": "...", "options": ["A","B","C","D"], "correct": 0, "explanation": "..."}},
    {{"type": "fill", "question": "The word ___ means...", "answer": "word", "options": ["4","choices","here","too"], "explanation": "..."}},
    {{"type": "match", "question": "Match:", "pairs": [["term1","meaning1"],["term2","meaning2"],["term3","meaning3"]], "explanation": "..."}}
  ],
  "boss": [
    // 4 harder questions on Madhva's philosophy and deeper Sanskrit
    {{"type": "mcq", "question": "...", "options": ["A","B","C","D"], "correct": 0, "explanation": "..."}}
  ]
}}

CRITICAL:
1. The verse.translation MUST be the COMPLETE text from the PDF — never truncate with "..."
2. Use ACCURATE well-known Devanagari for the Sanskrit (this is Srimad Bhagavatam, the shlokas are well-established)
3. Every word in verse.words AND sanskritWords must have non-empty "full" field
4. Story must reflect ACTUAL chapter events from the text above, not generic filler
5. Quiz questions must test content from THIS specific chapter"""


def regenerate_chapter(skandha, chapter, title, verses, chapter_text):
    """Regenerate a single chapter with actual PDF content."""
    # Format verse texts
    verse_texts = "\n".join([
        f"Verse {v['num']}: {v['text'][:500]}" for v in verses[:15]
    ])

    prompt = PROMPT.format(
        skandha=skandha, chapter=chapter, title=title,
        verse_texts=verse_texts[:4000],
        chapter_text=chapter_text[:3000]
    )

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are a Sanskrit scholar. Output ONLY valid JSON. No markdown fences. Ensure ALL text fields are complete — never truncate translations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=8192,
                temperature=0.4,
            )

            text = response.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if "```" in text:
                    text = text[:text.rfind("```")].strip()

            lesson = json.loads(text)

            # Post-process: ensure sanskritWords have full field
            for w in lesson.get('sanskritWords', []):
                if not w.get('full', '').strip():
                    w['full'] = w.get('mean', '')

            # Ensure verse words have full field
            for w in lesson.get('verse', {}).get('words', []):
                if not w.get('full', '').strip():
                    w['full'] = w.get('mean', '')

            # Promote verse words to sanskritWords if missing
            sw_sans = {w.get('san', '') for w in lesson.get('sanskritWords', [])}
            for vw in lesson.get('verse', {}).get('words', []):
                if vw.get('san', '') and vw['san'] not in sw_sans:
                    lesson.setdefault('sanskritWords', []).append({
                        'san': vw['san'], 'trans': vw.get('trans', ''),
                        'mean': vw.get('mean', ''), 'full': vw.get('full', vw.get('mean', '')),
                        'example': f"{vw['san']} — from the key verse"
                    })

            return lesson

        except json.JSONDecodeError as e:
            print(f"      JSON error attempt {attempt+1}: {e}")
            if attempt == 2:
                return None
            time.sleep(2)
        except Exception as e:
            print(f"      API error attempt {attempt+1}: {e}")
            if attempt == 2:
                return None
            time.sleep(3)

    return None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    force = "--force" in sys.argv

    # Optional: specific skandha/chapter
    target_sk = None
    target_ch = None
    if mode.count('-') == 1:
        parts = mode.split('-')
        target_sk, target_ch = int(parts[0]), int(parts[1])
        mode = "single"
    elif mode.isdigit():
        target_sk = int(mode)
        mode = "skandha"

    print("Loading PDF...")
    doc = fitz.open(PDF_PATH)

    # Find all chapters in PDF
    full_text = ""
    for i in range(min(len(doc), 20)):
        full_text += doc[i].get_text()

    sb_pattern = re.compile(r'SB\s+(\d+)\.(\d+):\s*(.+?)(?:\n|$)')
    all_chapters = []
    for match in sb_pattern.finditer(full_text):
        # Just collect chapter references from early pages
        pass

    # For full coverage, scan all pages for chapter headers
    print("Scanning PDF for chapter headers...")
    chapters_found = []
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        for match in sb_pattern.finditer(text):
            sk, ch = int(match.group(1)), int(match.group(2))
            title = match.group(3).strip()
            key = f"{sk}-{ch}"
            if not any(c['key'] == key for c in chapters_found):
                chapters_found.append({'key': key, 'skandha': sk, 'chapter': ch, 'title': title})

    print(f"Found {len(chapters_found)} chapters in PDF")

    # Filter based on mode
    if mode == "single":
        chapters_found = [c for c in chapters_found if c['skandha'] == target_sk and c['chapter'] == target_ch]
    elif mode == "skandha":
        chapters_found = [c for c in chapters_found if c['skandha'] == target_sk]

    generated = 0
    skipped = 0
    failed = 0

    for i, ch_info in enumerate(chapters_found):
        sk, ch = ch_info['skandha'], ch_info['chapter']
        ch_id = f"{sk}-{ch}"
        cache_path = os.path.join(CACHE_DIR, f"{ch_id}.json")

        if os.path.exists(cache_path) and not force:
            skipped += 1
            continue

        title, verses, chapter_text = extract_chapter_verses(doc, sk, ch)
        if not title:
            title = ch_info['title']

        if not verses:
            print(f"  [{i+1}/{len(chapters_found)}] {ch_id} '{title[:40]}' — no verses found, skipping")
            failed += 1
            continue

        print(f"  [{i+1}/{len(chapters_found)}] {ch_id} '{title[:40]}' — {len(verses)} verses, generating...")

        lesson = regenerate_chapter(sk, ch, title, verses, chapter_text)
        if not lesson:
            print(f"    ✗ Failed")
            failed += 1
            continue

        with open(cache_path, 'w') as f:
            json.dump(lesson, f, ensure_ascii=False, indent=2)

        v = lesson.get('verse', {})
        sw = lesson.get('sanskritWords', [])
        print(f"    ✓ {len(v.get('words',[]))} verse words, {len(sw)} lesson words, {len(lesson.get('quiz',[]))} quiz Qs")
        generated += 1
        time.sleep(delay)

    doc.close()

    print(f"\n{'='*60}")
    print(f"DONE: {generated} generated, {skipped} skipped (cached), {failed} failed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
