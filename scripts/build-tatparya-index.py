#!/usr/bin/env python3
"""
Build a chapter-to-page index for Sri Bhagavata Tatparya Nirnaya PDF
by scanning pages with Gemini Vision to find chapter boundaries.

Sends batches of pages and asks Gemini to identify chapter markers
(e.g., "प्रथमोऽध्यायः", "द्वितीयोऽध्यायः") and their page numbers.

Saves index to data/tatparya-index.json
"""
import os, sys, json, time, base64
import fitz
from dotenv import load_dotenv
import urllib.request

SCRIPT_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(SCRIPT_DIR, '..', '.env.local'))

PDF_PATH = os.path.join(SCRIPT_DIR, '..', '..', 'Sri Bhagavata Tatparya Nirnaya.pdf')
INDEX_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'tatparya-index.json')

GEMINI_KEY = os.environ.get('GOOGLE_GENERATIVE_AI_API_KEY', '')
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'

CONTENT_OFFSET = 19  # Content starts at PDF page 19

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


def call_gemini(images_b64, prompt):
    parts = [{"inline_data": {"mime_type": "image/png", "data": img}} for img in images_b64]
    parts.append({"text": prompt})

    payload = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096}
    }).encode('utf-8')

    url = f"{GEMINI_URL}?key={GEMINI_KEY}"
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            text = data['candidates'][0]['content']['parts'][0]['text']
            return text.strip()
        except Exception as e:
            if attempt == 2:
                print(f'    Gemini error: {e}')
                return None
            time.sleep(10)
    return None


def scan_skandha(doc, skandha, pdf_start, pdf_end):
    """Scan a skandha's pages to find chapter boundaries."""
    # Send pages in batches of 10-15
    batch_size = 12
    chapters_found = []

    for batch_start in range(pdf_start, pdf_end, batch_size):
        batch_end = min(batch_start + batch_size, pdf_end)
        images = []
        for pg in range(batch_start, batch_end):
            if pg < len(doc):
                page = doc[pg]
                pix = page.get_pixmap(dpi=150)
                images.append(base64.b64encode(pix.tobytes('png')).decode('utf-8'))

        if not images:
            continue

        prompt = f"""These are pages from Sri Bhagavata Tatparya Nirnaya (Skandha {skandha}).

Scan ALL these pages and find EVERY chapter boundary marker. Chapter markers in this text look like:
- "प्रथमोऽध्यायः" (First Chapter)
- "द्वितीयोऽध्यायः" (Second Chapter)
- "...ध्यायः" pattern for chapter endings/beginnings
- Or Sanskrit ordinal numbers followed by "अध्यायः"

Also look for the printed page number at the bottom of each page.

For each chapter boundary you find, output a JSON line like:
{{"chapter": N, "page_number": printed_page_num, "pdf_page": estimated_pdf_page, "marker_text": "the actual Sanskrit text"}}

Output ONLY a JSON array of chapter boundaries found. If no chapter boundaries on these pages, output [].
The PDF pages in this batch are {batch_start} to {batch_end - 1}."""

        response = call_gemini(images, prompt)
        if response:
            try:
                text = response.strip()
                if text.startswith('```'):
                    text = text.split('\n', 1)[1]
                    if '```' in text:
                        text = text[:text.rfind('```')].strip()
                found = json.loads(text)
                if isinstance(found, list):
                    for entry in found:
                        entry['batch_pdf_start'] = batch_start
                        entry['batch_pdf_end'] = batch_end
                        entry['skandha'] = skandha
                    chapters_found.extend(found)
                    if found:
                        print(f'    Batch {batch_start}-{batch_end}: found {len(found)} chapter markers')
            except json.JSONDecodeError:
                print(f'    Batch {batch_start}-{batch_end}: could not parse response')

        time.sleep(4)

    return chapters_found


def main():
    if not GEMINI_KEY:
        print('ERROR: GOOGLE_GENERATIVE_AI_API_KEY not set', file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(PDF_PATH)
    print(f'Scanning Tatparya Nirnaya PDF ({len(doc)} pages) for chapter boundaries...')

    # Determine which skandhas to scan
    target_sk = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--skandha' and i < len(sys.argv) - 1:
            target_sk = int(sys.argv[i + 1])

    all_chapters = []

    for skandha, (pdf_start, pdf_end) in SKANDHA_PDF_RANGES.items():
        if target_sk and skandha != target_sk:
            continue

        print(f'\n=== Skandha {skandha} (PDF pages {pdf_start}-{pdf_end}) ===')
        found = scan_skandha(doc, skandha, pdf_start, pdf_end)
        all_chapters.extend(found)
        print(f'  Total: {len(found)} chapters found in Skandha {skandha}')

    doc.close()

    # Build index
    index = {
        "source": "Sri Bhagavata Tatparya Nirnaya.pdf",
        "total_pages": 863,
        "content_offset": CONTENT_OFFSET,
        "chapters": all_chapters,
    }

    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f'\n{"="*60}')
    print(f'Index saved to {INDEX_PATH}')
    print(f'Total chapter markers found: {len(all_chapters)}')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
