#!/usr/bin/env python3
"""
Fetch authentic Sanskrit data from vedabase.io for all Bhagavatam chapters.

For each chapter, fetches verse 1 (or the key verse from the generated lesson) to get:
- Devanagari text
- IAST transliteration
- Word-by-word synonyms
- English translation

Saves to data/vedabase-cache/{skandha}-{chapter}.json

Usage:
    python scripts/fetch-vedabase-sanskrit.py              # All 335 chapters
    python scripts/fetch-vedabase-sanskrit.py --skandha 1  # Just skandha 1
    python scripts/fetch-vedabase-sanskrit.py 1-1          # Single chapter
    python scripts/fetch-vedabase-sanskrit.py --key-verse  # Use verse ref from generated lesson
    python scripts/fetch-vedabase-sanskrit.py --force      # Re-fetch even if cached
"""
import os, sys, json, time, re
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(__file__)
CACHE_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'vedabase-cache')
LESSON_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'generated-lessons')

SKANDHA_CHAPTERS = {
    1: 19, 2: 10, 3: 33, 4: 31, 5: 26, 6: 19,
    7: 15, 8: 24, 9: 24, 10: 90, 11: 31, 12: 13,
}

BASE_URL = "https://vedabase.io/en/library/sb"


def fetch_url(url, retries=3):
    """Fetch URL with retries."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) BhagavatamEduApp/1.0',
        'Accept': 'text/html,application/xhtml+xml',
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return None


def strip_html(text):
    """Remove HTML tags and clean whitespace."""
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&#39;', "'").replace('&quot;', '"')
    return text.strip()


def parse_vedabase_html(html):
    """Parse vedabase.io verse page HTML to extract all sections."""
    if not html:
        return None

    result = {}

    # === DEVANAGARI ===
    # Div class "av-devanagari" contains the Sanskrit in Devanagari script
    deva_match = re.search(
        r'av-devanagari"[^>]*>.*?<div[^>]*>(.*?)</div>\s*</div>',
        html, re.DOTALL
    )
    if deva_match:
        raw = deva_match.group(1)
        # Get inner div content
        inner = re.search(r'<div[^>]*>(.*?)</div>', raw, re.DOTALL)
        if inner:
            raw = inner.group(1)
        devanagari = strip_html(raw)
        if devanagari:
            result['devanagari'] = devanagari

    # === VERSE TEXT (IAST transliteration) ===
    # Class is "av-verse_text" (underscore)
    vt_match = re.search(
        r'av-verse_text"[^>]*>.*?<div[^>]*id="[^"]*"[^>]*>(.*?)</div>\s*</div>',
        html, re.DOTALL
    )
    if vt_match:
        raw = vt_match.group(1)
        inner = re.search(r'<div[^>]*>(.*?)</div>', raw, re.DOTALL)
        if inner:
            raw = inner.group(1)
        transliteration = strip_html(raw)
        if transliteration:
            result['transliteration'] = transliteration

    # === SYNONYMS (word-by-word) ===
    syn_match = re.search(
        r'av-synonyms"[^>]*>.*?<div[^>]*id="[^"]*"[^>]*>(.*?)</div>\s*</div>',
        html, re.DOTALL
    )
    if syn_match:
        syn_html = syn_match.group(1)
        words = []

        # Each word is in a <span class="inline"> with <a><em>word</em></a> — meaning; </span>
        word_matches = re.findall(
            r'<a[^>]*><em>([^<]+)</em></a>\s*—\s*<span[^>]*>(.*?)</span>',
            syn_html, re.DOTALL
        )
        if not word_matches:
            # Fallback: try simpler pattern
            word_matches = re.findall(
                r'<em>([^<]+)</em>\s*</a>\s*—\s*(.*?)(?:;\s*</span>|</span>)',
                syn_html, re.DOTALL
            )

        for san_word, meaning in word_matches:
            clean_meaning = strip_html(meaning).rstrip(';').strip()
            words.append({
                'trans': san_word.strip(),
                'mean': clean_meaning
            })

        if words:
            result['words'] = words
            result['synonyms_raw'] = '; '.join(
                f"{w['trans']} — {w['mean']}" for w in words
            )

    # === TRANSLATION ===
    trans_match = re.search(
        r'av-translation"[^>]*>.*?<div[^>]*id="[^"]*"[^>]*>(.*?)</div>\s*</div>',
        html, re.DOTALL
    )
    if trans_match:
        raw = trans_match.group(1)
        inner = re.search(r'<div[^>]*>(.*?)</div>', raw, re.DOTALL)
        if inner:
            raw = inner.group(1)
        # Also handle <strong> wrapped translation
        translation = strip_html(raw)
        if translation:
            result['translation'] = translation

    return result if result else None


def get_key_verse_num(skandha, chapter):
    """Get the verse number from the generated lesson's ref field."""
    lesson_path = os.path.join(LESSON_DIR, f"{skandha}-{chapter}.json")
    if os.path.exists(lesson_path):
        try:
            with open(lesson_path) as f:
                lesson = json.load(f)
            ref = lesson.get('verse', {}).get('ref', '')
            match = re.search(r'(\d+)\.(\d+)\.(\d+)', ref)
            if match:
                return int(match.group(3))
        except Exception:
            pass
    return 1


def fetch_verse_data(skandha, chapter, verse_num=1):
    """Fetch and parse a verse from vedabase.io.

    Tries single verse first, then combined verse URLs (e.g., 1-2, 1-3)
    since vedabase.io sometimes groups verses together.
    """
    # Try single verse first
    url = f"{BASE_URL}/{skandha}/{chapter}/{verse_num}/"
    html = fetch_url(url)

    # If 404, try combined verse URLs
    if not html:
        for end in range(verse_num + 1, verse_num + 10):
            url = f"{BASE_URL}/{skandha}/{chapter}/{verse_num}-{end}/"
            html = fetch_url(url)
            if html:
                break

    if not html:
        return None

    data = parse_vedabase_html(html)
    if data:
        data['skandha'] = skandha
        data['chapter'] = chapter
        data['verse_num'] = verse_num
        data['ref'] = f"SB {skandha}.{chapter}.{verse_num}"
        data['source_url'] = url
    return data


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)

    target_sk = None
    target_ch = None
    key_verse = '--key-verse' in sys.argv
    force = '--force' in sys.argv
    delay = 1.0

    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--skandha' and i < len(sys.argv) - 1:
            target_sk = int(sys.argv[i + 1])

    for arg in args:
        if '-' in arg and arg[0].isdigit():
            parts = arg.split('-')
            target_sk, target_ch = int(parts[0]), int(parts[1])

    # Build chapter list
    chapters = []
    for sk, num_ch in SKANDHA_CHAPTERS.items():
        if target_sk and sk != target_sk:
            continue
        for ch in range(1, num_ch + 1):
            if target_ch and ch != target_ch:
                continue
            chapters.append((sk, ch))

    print(f"Fetching Sanskrit from vedabase.io for {len(chapters)} chapters...")
    print(f"  Mode: {'key verse from lesson' if key_verse else 'verse 1'}")

    fetched = 0
    skipped = 0
    failed = 0

    for i, (sk, ch) in enumerate(chapters):
        ch_id = f"{sk}-{ch}"
        cache_path = os.path.join(CACHE_DIR, f"{ch_id}.json")

        if os.path.exists(cache_path) and not force:
            skipped += 1
            continue

        verse_num = get_key_verse_num(sk, ch) if key_verse else 1
        print(f"  [{i+1}/{len(chapters)}] {ch_id} v{verse_num}", end=" ", flush=True)

        try:
            data = fetch_verse_data(sk, ch, verse_num)
            if data and ('devanagari' in data or 'words' in data):
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                d = '✓' if 'devanagari' in data else '✗'
                t = '✓' if 'transliteration' in data else '✗'
                tr = '✓' if 'translation' in data else '✗'
                w = len(data.get('words', []))
                print(f"— deva:{d} iast:{t} trans:{tr} words:{w}")
                fetched += 1
            else:
                print(f"— no data extracted")
                failed += 1
        except Exception as e:
            print(f"— ERROR: {e}")
            failed += 1

        time.sleep(delay)

    print(f"\n{'='*60}")
    print(f"DONE: {fetched} fetched, {skipped} cached, {failed} failed")
    print(f"Cache: {CACHE_DIR}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
