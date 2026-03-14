#!/usr/bin/env python3
"""
Extract Madhvacharya's commentary from Sri Bhagavata Tatparya Nirnaya PDF.

Two-phase approach:
1. Gemini Vision OCR: Extract raw Sanskrit text + English understanding from PDF pages
2. GPT-4.1: Match extracted commentary to specific Bhagavatam chapters using lesson context

Saves to data/tatparya-cache/{skandha}-{chapter}.json

Usage:
    python scripts/extract-tatparya-v2.py                 # All skandhas
    python scripts/extract-tatparya-v2.py --skandha 1     # Just skandha 1
    python scripts/extract-tatparya-v2.py --phase 1       # Only OCR phase
    python scripts/extract-tatparya-v2.py --phase 2       # Only matching phase
    python scripts/extract-tatparya-v2.py --force          # Re-extract
"""
import os, sys, json, time, re, base64, hashlib
import fitz
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(SCRIPT_DIR, '..', '.env.local'))

PDF_PATH = os.path.join(SCRIPT_DIR, '..', '..', 'Sri Bhagavata Tatparya Nirnaya.pdf')
CACHE_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'tatparya-cache')
RAW_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'tatparya-raw')
LESSON_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'generated-lessons')

GEMINI_KEY = os.environ.get('GOOGLE_GENERATIVE_AI_API_KEY', '')
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'

OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '')

# PDF page ranges per skandha (0-indexed PDF pages)
SKANDHA_PDF_RANGES = {
    1: (19, 82),
    2: (83, 153),
    3: (154, 292),
    4: (293, 377),
    5: (378, 413),
    6: (414, 447),
    7: (448, 516),
    8: (517, 579),
    9: (580, 649),
    10: (650, 769),
    11: (770, 839),
    12: (840, 862),
}

SKANDHA_CHAPTERS = {
    1: 19, 2: 10, 3: 33, 4: 31, 5: 26, 6: 19,
    7: 15, 8: 24, 9: 24, 10: 90, 11: 31, 12: 13,
}


def call_gemini(images_b64, prompt, max_retries=3):
    """Call Gemini API with images and text prompt."""
    import urllib.request, urllib.error

    parts = [{"inline_data": {"mime_type": "image/png", "data": img}} for img in images_b64]
    parts.append({"text": prompt})

    payload = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
    }).encode('utf-8')

    url = f"{GEMINI_URL}?key={GEMINI_KEY}"

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            candidates = data.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                return ' '.join(p.get('text', '') for p in parts).strip()
            return None
        except urllib.error.HTTPError as e:
            e.read()
            if e.code == 429:
                time.sleep(30 * (attempt + 1))
            elif attempt == max_retries - 1:
                return None
            else:
                time.sleep(5)
        except Exception:
            if attempt == max_retries - 1:
                return None
            time.sleep(5)
    return None


def call_openai(prompt, system="You are a scholar of Madhvacharya's Dvaita Vedanta philosophy.", max_retries=3):
    """Call OpenAI GPT-4.1 API."""
    import urllib.request, urllib.error

    payload = json.dumps({
        "model": "gpt-4.1",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }).encode('utf-8')

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {OPENAI_KEY}'
                }
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return data['choices'][0]['message']['content'].strip()
        except Exception as e:
            if attempt == max_retries - 1:
                print(f'      OpenAI error: {e}')
                return None
            time.sleep(5)
    return None


# ── PHASE 1: OCR with Gemini ──

def phase1_extract_raw(doc, skandha, force=False):
    """Extract raw commentary text from PDF pages using Gemini Vision."""
    pdf_start, pdf_end = SKANDHA_PDF_RANGES[skandha]
    batch_size = 6  # pages per batch

    raw_path = os.path.join(RAW_DIR, f'skandha-{skandha}.json')
    if os.path.exists(raw_path) and not force:
        print(f'  Skandha {skandha}: raw cache exists, skipping OCR')
        with open(raw_path) as f:
            return json.load(f)

    print(f'  Skandha {skandha}: OCR scanning PDF pages {pdf_start}-{pdf_end}...')
    all_sections = []

    for batch_start in range(pdf_start, pdf_end + 1, batch_size):
        batch_end = min(batch_start + batch_size, pdf_end + 1)
        images = []
        for pg in range(batch_start, batch_end):
            if pg < len(doc):
                page = doc[pg]
                pix = page.get_pixmap(dpi=200)
                images.append(base64.b64encode(pix.tobytes('png')).decode('utf-8'))

        if not images:
            continue

        print(f'    Pages {batch_start}-{batch_end - 1}...', end=' ', flush=True)

        prompt = f"""These are pages from Sri Bhagavata Tatparya Nirnaya by Madhvacharya (Skandha {skandha}).
The text is in Sanskrit (Devanagari script). PDF pages {batch_start} to {batch_end - 1}.

Please:
1. OCR all the Sanskrit text visible on these pages
2. Identify any chapter boundary markers (like "...अध्यायः" or "इति श्रीमद्भागवततात्पर्यनिर्णये...")
3. Note any verse references (like "{skandha}.X.Y")
4. Provide an English understanding of the key philosophical points discussed

Output as plain text with clear section markers. Format:

---PAGE {batch_start}---
[OCR text and chapter markers visible on this page]

---ENGLISH UNDERSTANDING---
[English summary of philosophical content in these pages, noting which chapter(s) are being discussed]
[Note any specific verse references like {skandha}.X.Y that help identify the chapter]"""

        response = call_gemini(images, prompt)
        if response:
            all_sections.append({
                'pdf_pages': [batch_start, batch_end - 1],
                'content': response
            })
            # Count approximate words
            words = len(response.split())
            print(f'{words} words')
        else:
            print(f'failed')

        time.sleep(4)

    # Save raw data
    raw_data = {
        'skandha': skandha,
        'pdf_range': [pdf_start, pdf_end],
        'sections': all_sections
    }
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    print(f'  Skandha {skandha}: {len(all_sections)} sections extracted')
    return raw_data


# ── PHASE 2: Match to chapters with GPT-4.1 ──

def phase2_match_chapters(raw_data, skandha, force=False):
    """Use GPT-4.1 to create chapter-specific teachings from raw commentary."""
    num_chapters = SKANDHA_CHAPTERS[skandha]
    sections = raw_data.get('sections', [])

    if not sections:
        print(f'  Skandha {skandha}: no raw data, skipping')
        return

    # All raw text sections
    all_sections = sections
    total_chars = sum(len(s['content']) for s in all_sections)
    print(f'  Skandha {skandha}: matching {num_chapters} chapters ({total_chars} chars of raw text, {len(all_sections)} sections)')

    # Process chapters in batches of 5 to reduce API calls
    batch_size = 5
    for ch_start in range(1, num_chapters + 1, batch_size):
        ch_end = min(ch_start + batch_size, num_chapters + 1)
        chapters_to_process = []

        for ch in range(ch_start, ch_end):
            cache_path = os.path.join(CACHE_DIR, f'{skandha}-{ch}.json')
            if os.path.exists(cache_path) and not force:
                with open(cache_path) as f:
                    data = json.load(f)
                if data.get('found', False) and len(data.get('key_teachings', [])) >= 2:
                    continue
            chapters_to_process.append(ch)

        if not chapters_to_process:
            continue

        # Select relevant portion of raw text based on chapter position
        # Chapters appear sequentially, so use proportional section selection
        frac_start = max(0, (ch_start - 1) / num_chapters - 0.1)
        frac_end = min(1, ch_end / num_chapters + 0.1)
        sec_start = int(frac_start * len(all_sections))
        sec_end = min(int(frac_end * len(all_sections)) + 1, len(all_sections))
        relevant_text = '\n\n'.join(s['content'] for s in all_sections[sec_start:sec_end])
        # Cap at 40k chars to avoid overwhelming GPT
        if len(relevant_text) > 40000:
            relevant_text = relevant_text[:40000] + '\n[... truncated ...]'

        # Load chapter titles and descriptions from lessons
        chapter_info = []
        for ch in chapters_to_process:
            lesson_path = os.path.join(LESSON_DIR, f'{skandha}-{ch}.json')
            title = f"Chapter {ch}"
            desc = ""
            if os.path.exists(lesson_path):
                with open(lesson_path) as f:
                    lesson = json.load(f)
                title = lesson.get('title', title)
                desc = lesson.get('desc', '')
                story = lesson.get('story', '')
                if story:
                    desc += f" Story: {story[:200]}"
            chapter_info.append(f"Chapter {ch}: \"{title}\" — {desc[:300]}")

        chapters_list = '\n'.join(chapter_info)
        ch_nums = [str(c) for c in chapters_to_process]

        prompt = f"""Below is OCR'd text from Sri Bhagavata Tatparya Nirnaya by Madhvacharya — his commentary on Skandha {skandha} of the Srimad Bhagavatam.

IMPORTANT: The text uses abbreviations for chapter references:
- "आ. ता. {skandha}-X" or "आ. ता. X" means "Adhyaya Tatparya X" = Chapter X commentary
- "इति श्री...तात्पर्यनिर्णये...अध्यायः" marks chapter endings
- Verse numbers like "॥ NN ॥" appear throughout
- The Tatparya Nirnaya discusses the same topics as each Bhagavatam chapter (the descriptions below tell you what each chapter covers)

=== RAW TATPARYA NIRNAYA TEXT (Skandha {skandha}, sections {sec_start+1}-{sec_end} of {len(all_sections)}) ===
{relevant_text}
=== END RAW TEXT ===

I need you to extract Madhvacharya's SPECIFIC teachings for these Bhagavatam chapters:
{chapters_list}

Use the chapter descriptions above to match content from the raw text. The Tatparya Nirnaya follows the same chapter order as the Bhagavatam, so content appears sequentially.

For EACH chapter ({', '.join(ch_nums)}), output a JSON object. Even if exact chapter markers aren't visible, use the sequential ordering and topic matching to identify the relevant commentary.

Output a JSON array. IMPORTANT: Do NOT include raw Sanskrit/Devanagari in the JSON values — use only English and IAST transliteration (Latin script) to avoid encoding issues.

[
  {{
    "chapter": <number>,
    "found": true,
    "key_teachings": [
      "Each specific philosophical point Madhvacharya makes about THIS chapter's topics (3-5 points). Use IAST for Sanskrit terms."
    ],
    "dvaita_concepts": ["Dvaita concepts: Sanskrit term in IAST (translation) — brief explanation"],
    "english_summary": "3-4 sentence summary SPECIFIC to this chapter. Mention characters, events, verses. Use IAST transliteration for Sanskrit terms with English in parentheses."
  }}
]

CRITICAL RULES:
- The commentary follows the Bhagavatam chapter order — use sequential position to match
- Each teaching must be SPECIFIC to that chapter — mention actual content, characters, events
- Set found=true for every chapter where you can provide Madhva's teachings
- Do NOT output generic Dvaita philosophy — ground everything in the source text and chapter content
- Use ONLY English and IAST Latin transliteration in JSON values (NO Devanagari script)
- Output ONLY the JSON array, no other text"""

        print(f'    Chapters {ch_nums}...', end=' ', flush=True)

        response = call_openai(prompt)
        if not response:
            print('failed')
            continue

        # Parse response
        try:
            text = response.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1]
                if '```' in text:
                    text = text[:text.rfind('```')].strip()
            results = json.loads(text)
            if not isinstance(results, list):
                results = [results]
        except json.JSONDecodeError:
            # Try to fix common JSON issues from GPT output with Sanskrit
            cleaned = text
            # Remove repeated avagraha characters (common OCR artifact)
            cleaned = re.sub(r'ऽ{5,}', 'ऽ...', cleaned)
            # Try parsing again
            try:
                match = re.search(r'\[.*\]', cleaned, re.DOTALL)
                if match:
                    results = json.loads(match.group(0))
                else:
                    raise json.JSONDecodeError('', '', 0)
            except json.JSONDecodeError:
                # Last resort: extract individual JSON objects
                results = []
                for obj_match in re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned):
                    try:
                        obj = json.loads(obj_match.group(0))
                        if 'chapter' in obj:
                            results.append(obj)
                    except json.JSONDecodeError:
                        continue
                if not results:
                    print(f'parse error')
                    print(f'      Response preview: {text[:200]}...')
                    continue

        saved = 0
        for entry in results:
            ch = entry.get('chapter')
            if ch and ch in chapters_to_process:
                entry['skandha'] = skandha
                entry.setdefault('sanskrit_excerpts', [])
                entry.setdefault('found', True)
                cache_path = os.path.join(CACHE_DIR, f'{skandha}-{ch}.json')
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(entry, f, ensure_ascii=False, indent=2)
                saved += 1

        print(f'{saved} saved')
        time.sleep(1)


def main():
    if not GEMINI_KEY:
        print('ERROR: GOOGLE_GENERATIVE_AI_API_KEY not found', file=sys.stderr)
        sys.exit(1)

    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

    target_sk = None
    force = '--force' in sys.argv
    phase = 0  # 0 = both

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--skandha' and i < len(sys.argv) - 1:
            target_sk = int(sys.argv[i + 1])
        if arg == '--phase' and i < len(sys.argv) - 1:
            phase = int(sys.argv[i + 1])

    doc = fitz.open(PDF_PATH)
    print(f'Tatparya Nirnaya Extraction v2 ({len(doc)} pages)')
    print(f'  Phase 1: Gemini Vision OCR → raw text')
    print(f'  Phase 2: GPT-4.1 → chapter-specific teachings')

    for skandha in sorted(SKANDHA_PDF_RANGES.keys()):
        if target_sk and skandha != target_sk:
            continue

        print(f'\n{"="*60}')
        print(f'SKANDHA {skandha} ({SKANDHA_CHAPTERS[skandha]} chapters)')
        print(f'{"="*60}')

        if phase in (0, 1):
            raw_data = phase1_extract_raw(doc, skandha, force=force)
        else:
            raw_path = os.path.join(RAW_DIR, f'skandha-{skandha}.json')
            if os.path.exists(raw_path):
                with open(raw_path) as f:
                    raw_data = json.load(f)
            else:
                print(f'  No raw data for Skandha {skandha}, run phase 1 first')
                continue

        if phase in (0, 2):
            phase2_match_chapters(raw_data, skandha, force=force)

    doc.close()

    # Summary
    total = sum(SKANDHA_CHAPTERS.values())
    found = 0
    for sk in SKANDHA_CHAPTERS:
        for ch in range(1, SKANDHA_CHAPTERS[sk] + 1):
            path = os.path.join(CACHE_DIR, f'{sk}-{ch}.json')
            if os.path.exists(path):
                with open(path) as f:
                    d = json.load(f)
                if d.get('found', False):
                    found += 1

    print(f'\n{"="*60}')
    print(f'TOTAL: {found}/{total} chapters with Madhva teachings')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
