#!/usr/bin/env python3
"""
Extract Madhvacharya's commentary from Sri Bhagavata Tatparya Nirnaya PDF
using Google Gemini vision for OCR + understanding.

Strategy: Sequential scan — process each skandha's pages in batches of 8,
asking Gemini to extract ALL chapter commentaries visible in each batch.
This avoids the need for accurate per-chapter page estimates.

Saves to data/tatparya-cache/{skandha}-{chapter}.json

Usage:
    python scripts/extract-tatparya.py                 # All skandhas
    python scripts/extract-tatparya.py --skandha 1     # Just skandha 1
    python scripts/extract-tatparya.py --force          # Re-extract cached
    python scripts/extract-tatparya.py --retry-missing  # Only retry not-found
"""
import os, sys, json, time, re, base64
import fitz
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(SCRIPT_DIR, '..', '.env.local'))

PDF_PATH = os.path.join(SCRIPT_DIR, '..', '..', 'Sri Bhagavata Tatparya Nirnaya.pdf')
CACHE_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'tatparya-cache')
LESSON_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'generated-lessons')

GEMINI_KEY = os.environ.get('GOOGLE_GENERATIVE_AI_API_KEY', '')
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'

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

# Bhagavatam structure
SKANDHA_CHAPTERS = {
    1: 19, 2: 10, 3: 33, 4: 31, 5: 26, 6: 19,
    7: 15, 8: 24, 9: 24, 10: 90, 11: 31, 12: 13,
}


def page_to_base64(doc, pdf_page, dpi=200):
    """Render a PDF page to base64-encoded PNG."""
    page = doc[pdf_page]
    pix = page.get_pixmap(dpi=dpi)
    return base64.b64encode(pix.tobytes("png")).decode('utf-8')


def call_gemini(images_b64, prompt, max_retries=3):
    """Call Gemini API with images and text prompt."""
    import urllib.request
    import urllib.error

    parts = []
    for img_b64 in images_b64:
        parts.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": img_b64
            }
        })
    parts.append({"text": prompt})

    payload = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,
        }
    }).encode('utf-8')

    url = f"{GEMINI_URL}?key={GEMINI_KEY}"

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            # Extract text from response
            candidates = data.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                text = ' '.join(p.get('text', '') for p in parts)
                return text.strip()
            return None

        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')[:200]
            if e.code == 429:
                wait = 30 * (attempt + 1)
                print(f'      Rate limited, waiting {wait}s...')
                time.sleep(wait)
            elif attempt == max_retries - 1:
                print(f'      Gemini error {e.code}: {body}')
                return None
            else:
                time.sleep(5)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f'      Error: {e}')
                return None
            time.sleep(5)

    return None


def parse_json_response(response):
    """Parse JSON from Gemini response, handling markdown fences."""
    if not response:
        return None
    text = response.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1]
        if '```' in text:
            text = text[:text.rfind('```')].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(0))
                return [result] if isinstance(result, dict) else result
            except json.JSONDecodeError:
                pass
    return None


def extract_batch(doc, skandha, pdf_start, pdf_end):
    """Extract all chapter commentaries visible in a batch of pages."""
    images = []
    for pg in range(pdf_start, min(pdf_end, len(doc))):
        images.append(page_to_base64(doc, pg))

    if not images:
        return []

    prompt = f"""These are pages from Sri Bhagavata Tatparya Nirnaya by Madhvacharya — his commentary on Skandha {skandha} of the Srimad Bhagavatam.

The text is in Sanskrit (Devanagari script). These are PDF pages {pdf_start} to {pdf_end - 1}.

TASK: Identify ALL chapter commentaries visible on these pages. Chapter boundaries are marked by text like "प्रथमोऽध्यायः", "द्वितीयोऽध्यायः", etc. Verse references look like "{skandha}.X.Y" where X is the chapter number.

For EACH chapter whose commentary appears on these pages, output a JSON object with:
- chapter: the chapter number
- sanskrit_excerpts: [key Sanskrit quotes from the Tatparya Nirnaya for this chapter]
- key_teachings: [each major philosophical point Madhvacharya makes, in English]
- dvaita_concepts: [specific Dvaita philosophical concepts with Sanskrit terms]
- english_summary: 3-4 sentence summary of Madhvacharya's interpretation. Be SPECIFIC — mention characters, events, verses. Include Sanskrit terms with translations.

Output a JSON ARRAY of chapter objects. Example:
[
  {{
    "chapter": 5,
    "sanskrit_excerpts": ["..."],
    "key_teachings": ["..."],
    "dvaita_concepts": ["..."],
    "english_summary": "..."
  }}
]

IMPORTANT:
- Only include content ACTUALLY VISIBLE in these pages
- Include ALL chapters visible, even if only partially
- Be specific to each chapter's content — no generic Dvaita philosophy
- If a chapter spans multiple batches, extract what's visible here
- Output [] if no chapter commentary is identifiable"""

    response = call_gemini(images, prompt)
    result = parse_json_response(response)

    if isinstance(result, list):
        return result
    return []


def scan_skandha(doc, skandha, force=False):
    """Scan an entire skandha sequentially, extracting all chapters."""
    pdf_start, pdf_end = SKANDHA_PDF_RANGES[skandha]
    num_chapters = SKANDHA_CHAPTERS[skandha]
    batch_size = 8  # pages per batch

    print(f'\n=== Skandha {skandha} ({num_chapters} chapters, PDF pages {pdf_start}-{pdf_end}) ===')

    # Check which chapters we already have
    existing = set()
    if not force:
        for ch in range(1, num_chapters + 1):
            cache_path = os.path.join(CACHE_DIR, f'{skandha}-{ch}.json')
            if os.path.exists(cache_path):
                with open(cache_path) as f:
                    data = json.load(f)
                if data.get('found', False):
                    existing.add(ch)

    if len(existing) == num_chapters and not force:
        print(f'  All {num_chapters} chapters already cached, skipping')
        return num_chapters, 0, 0

    # Collect all chapter data from sequential batches
    all_chapters = {}  # chapter_num -> best data

    for batch_start in range(pdf_start, pdf_end + 1, batch_size):
        batch_end = min(batch_start + batch_size, pdf_end + 1)
        print(f'  Scanning pages {batch_start}-{batch_end - 1}...', end=' ', flush=True)

        try:
            results = extract_batch(doc, skandha, batch_start, batch_end)
            if results:
                chapters_in_batch = []
                for entry in results:
                    ch = entry.get('chapter')
                    if ch and 1 <= ch <= num_chapters:
                        # Merge: keep the version with more teachings
                        if ch in all_chapters:
                            old_count = len(all_chapters[ch].get('key_teachings', []))
                            new_count = len(entry.get('key_teachings', []))
                            if new_count > old_count:
                                all_chapters[ch] = entry
                        else:
                            all_chapters[ch] = entry
                        chapters_in_batch.append(ch)
                if chapters_in_batch:
                    print(f'found chapters {sorted(set(chapters_in_batch))}')
                else:
                    print(f'no chapters identified')
            else:
                print(f'no results')
        except Exception as e:
            print(f'error: {e}')

        time.sleep(4)

    # Save results
    saved = 0
    not_found = 0
    for ch in range(1, num_chapters + 1):
        cache_path = os.path.join(CACHE_DIR, f'{skandha}-{ch}.json')

        if ch in existing and not force:
            continue

        if ch in all_chapters:
            data = all_chapters[ch]
            data['found'] = True
            data['skandha'] = skandha
            data['chapter'] = ch
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            saved += 1
        else:
            # Save as not found
            data = {
                'found': False,
                'skandha': skandha,
                'chapter': ch,
                'sanskrit_excerpts': [],
                'key_teachings': [],
                'dvaita_concepts': [],
                'english_summary': ''
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            not_found += 1

    found_total = len(all_chapters) + len(existing)
    print(f'  Skandha {skandha}: {found_total}/{num_chapters} chapters found, {saved} new, {len(existing)} cached, {not_found} not found')
    return found_total, saved, not_found


def main():
    if not GEMINI_KEY:
        print('ERROR: GOOGLE_GENERATIVE_AI_API_KEY not found in .env.local', file=sys.stderr)
        sys.exit(1)

    os.makedirs(CACHE_DIR, exist_ok=True)

    target_sk = None
    force = '--force' in sys.argv
    retry_missing = '--retry-missing' in sys.argv

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--skandha' and i < len(sys.argv) - 1:
            target_sk = int(sys.argv[i + 1])

    # If retrying missing, delete not-found cache files first
    if retry_missing:
        import glob as g
        for path in g.glob(os.path.join(CACHE_DIR, '*.json')):
            with open(path) as f:
                data = json.load(f)
            if not data.get('found', False):
                os.remove(path)
                print(f'  Removed not-found cache: {os.path.basename(path)}')

    doc = fitz.open(PDF_PATH)
    print(f'Extracting Tatparya Nirnaya commentary ({len(doc)} pages)')
    print(f'  Strategy: Sequential scan with {8}-page batches')
    print(f'  PDF: {PDF_PATH}')

    total_found = 0
    total_saved = 0
    total_missing = 0

    for skandha in sorted(SKANDHA_PDF_RANGES.keys()):
        if target_sk and skandha != target_sk:
            continue
        found, saved, missing = scan_skandha(doc, skandha, force=force)
        total_found += found
        total_saved += saved
        total_missing += missing

    doc.close()

    total_chapters = sum(SKANDHA_CHAPTERS.values())
    print(f'\n{"="*60}')
    print(f'DONE: {total_found}/{total_chapters} chapters found')
    print(f'  New: {total_saved}, Missing: {total_missing}')
    print(f'  Cache: {CACHE_DIR}')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
