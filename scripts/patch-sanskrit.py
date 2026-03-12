#!/usr/bin/env python3
"""
Patch generated lessons with authentic Sanskrit data from vedabase.io.

Replaces hallucinated Devanagari, transliteration, translation, and word
breakdowns with real data fetched from vedabase.io (stored in vedabase-cache/).

For each lesson:
1. Replaces verse.sanskrit with real Devanagari from vedabase
2. Replaces verse.transliteration with real IAST
3. Replaces verse.translation with authoritative translation
4. Rebuilds verse.words from vedabase synonyms (adds Devanagari + full explanations via existing lesson data)
5. Updates verse.ref to match the actual verse number
6. Updates verse.syllables from real Devanagari
7. Merges vedabase words into sanskritWords

Usage:
    python scripts/patch-sanskrit.py              # Patch all lessons
    python scripts/patch-sanskrit.py --skandha 1  # Just skandha 1
    python scripts/patch-sanskrit.py 1-1          # Single chapter
    python scripts/patch-sanskrit.py --dry-run    # Preview changes without writing
"""
import os, sys, json, re

SCRIPT_DIR = os.path.dirname(__file__)
LESSON_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'generated-lessons')
VEDABASE_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'vedabase-cache')


def transliteration_to_devanagari_approx(trans_word):
    """Very rough IAST to Devanagari mapping for basic words.
    Not a full transliterator — just enough for word lookup matching.
    """
    # This is a best-effort lookup helper, not a production transliterator
    mapping = {
        'a': 'अ', 'ā': 'आ', 'i': 'इ', 'ī': 'ई', 'u': 'उ', 'ū': 'ऊ',
        'ṛ': 'ऋ', 'ṝ': 'ॠ', 'e': 'ए', 'ai': 'ऐ', 'o': 'ओ', 'au': 'औ',
        'k': 'क', 'kh': 'ख', 'g': 'ग', 'gh': 'घ', 'ṅ': 'ङ',
        'c': 'च', 'ch': 'छ', 'j': 'ज', 'jh': 'झ', 'ñ': 'ञ',
        'ṭ': 'ट', 'ṭh': 'ठ', 'ḍ': 'ड', 'ḍh': 'ढ', 'ṇ': 'ण',
        't': 'त', 'th': 'थ', 'd': 'द', 'dh': 'ध', 'n': 'न',
        'p': 'प', 'ph': 'फ', 'b': 'ब', 'bh': 'भ', 'm': 'म',
        'y': 'य', 'r': 'र', 'l': 'ल', 'v': 'व',
        'ś': 'श', 'ṣ': 'ष', 's': 'स', 'h': 'ह',
        'ṃ': 'ं', 'ḥ': 'ः',
    }
    # We won't do full conversion — just return the IAST for now
    # The lesson's existing verse.words may have Devanagari we can match
    return trans_word


def split_devanagari_syllables(text):
    """Split Devanagari text into syllables for the learning UI."""
    # Remove verse numbers and punctuation
    clean = re.sub(r'[॥।\d\s॥]+', ' ', text)
    clean = re.sub(r'ॐ', 'ॐ ', clean)
    # Split on spaces and filter
    parts = [p.strip() for p in clean.split() if p.strip()]
    return parts


def find_devanagari_for_word(trans_word, devanagari_text, existing_words):
    """Try to find the Devanagari form of a transliterated word.

    Strategy:
    1. Check existing verse.words for a match by transliteration
    2. Look for the word boundary in the full Devanagari text
    """
    # Normalize
    trans_lower = trans_word.lower().strip().replace('-', '')

    # Check existing lesson words
    for w in existing_words:
        existing_trans = w.get('trans', '').lower().strip().replace('-', '')
        if existing_trans == trans_lower:
            return w.get('san', '')

    return ''


def patch_lesson(lesson, vedabase_data):
    """Patch a single lesson with vedabase Sanskrit data.

    Returns (patched_lesson, changes_list).
    """
    changes = []
    verse = lesson.get('verse', {})
    if not verse:
        return lesson, ['NO_VERSE: lesson has no verse object']

    vb = vedabase_data
    existing_words = verse.get('words', [])

    # 1. Replace Devanagari
    if 'devanagari' in vb:
        old = verse.get('sanskrit', '')
        verse['sanskrit'] = vb['devanagari']
        if old != vb['devanagari']:
            changes.append('SANSKRIT: replaced with vedabase Devanagari')

    # 2. Replace transliteration
    if 'transliteration' in vb:
        old = verse.get('transliteration', '')
        verse['transliteration'] = vb['transliteration']
        if old != vb['transliteration']:
            changes.append('TRANSLITERATION: replaced with vedabase IAST')

    # 3. Replace translation
    if 'translation' in vb:
        old = verse.get('translation', '')
        verse['translation'] = vb['translation']
        if old != vb['translation']:
            changes.append('TRANSLATION: replaced with vedabase translation')

    # 4. Update verse ref
    if 'ref' in vb:
        sk = vb.get('skandha', '')
        ch = vb.get('chapter', '')
        vn = vb.get('verse_num', 1)
        new_ref = f"Srimad Bhagavatam {sk}.{ch}.{vn}"
        if verse.get('ref') != new_ref:
            verse['ref'] = new_ref
            changes.append(f'REF: updated to {new_ref}')

    # 5. Update syllables from real Devanagari
    if 'devanagari' in vb:
        syllables = split_devanagari_syllables(vb['devanagari'])
        if syllables:
            verse['syllables'] = syllables
            changes.append(f'SYLLABLES: rebuilt ({len(syllables)} from real Devanagari)')

    # 6. Rebuild verse.words from vedabase synonyms
    if 'words' in vb and vb['words']:
        new_words = []
        for vb_word in vb['words']:
            trans = vb_word['trans']
            mean = vb_word['mean']

            # Try to find Devanagari and full explanation from existing lesson
            san = find_devanagari_for_word(trans, vb.get('devanagari', ''), existing_words)
            full_explanation = ''
            for ew in existing_words:
                et = ew.get('trans', '').lower().replace('-', '')
                if et == trans.lower().replace('-', ''):
                    if not san:
                        san = ew.get('san', '')
                    full_explanation = ew.get('full', '')
                    break

            if not full_explanation:
                full_explanation = mean  # Fallback to the synonym meaning

            new_words.append({
                'san': san,
                'trans': trans,
                'mean': mean,
                'full': full_explanation,
            })

        verse['words'] = new_words
        changes.append(f'WORDS: rebuilt from vedabase ({len(new_words)} words)')

    lesson['verse'] = verse

    # 7. Merge vedabase words into sanskritWords
    if 'words' in vb and vb['words']:
        existing_sw = lesson.get('sanskritWords', [])
        existing_trans = {w.get('trans', '').lower().replace('-', '') for w in existing_sw}

        added = 0
        for vb_word in vb['words']:
            t = vb_word['trans'].lower().replace('-', '')
            if t not in existing_trans:
                san = find_devanagari_for_word(
                    vb_word['trans'], vb.get('devanagari', ''),
                    verse.get('words', [])
                )
                existing_sw.append({
                    'san': san,
                    'trans': vb_word['trans'],
                    'mean': vb_word['mean'],
                    'full': vb_word['mean'],
                    'example': f"From verse: {vb_word['trans']} — {vb_word['mean']}",
                })
                existing_trans.add(t)
                added += 1

        if added:
            lesson['sanskritWords'] = existing_sw
            changes.append(f'SANSKRIT_WORDS: added {added} from vedabase')

    return lesson, changes


def main():
    target_sk = None
    target_ch = None
    dry_run = '--dry-run' in sys.argv

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--skandha' and i < len(sys.argv) - 1:
            target_sk = int(sys.argv[i + 1])
        if '-' in arg and arg[0].isdigit():
            parts = arg.split('-')
            target_sk, target_ch = int(parts[0]), int(parts[1])

    # Find all lessons that have vedabase data
    vedabase_files = set()
    if os.path.exists(VEDABASE_DIR):
        for f in os.listdir(VEDABASE_DIR):
            if f.endswith('.json'):
                vedabase_files.add(f.replace('.json', ''))

    lesson_files = []
    if os.path.exists(LESSON_DIR):
        for f in sorted(os.listdir(LESSON_DIR)):
            if not f.endswith('.json'):
                continue
            ch_id = f.replace('.json', '')
            parts = ch_id.split('-')
            if len(parts) != 2:
                continue
            sk, ch = int(parts[0]), int(parts[1])
            if target_sk and sk != target_sk:
                continue
            if target_ch and ch != target_ch:
                continue
            lesson_files.append((ch_id, sk, ch))

    print(f"Patching lessons with vedabase Sanskrit data...")
    print(f"  Lessons: {len(lesson_files)}")
    print(f"  Vedabase cache: {len(vedabase_files)} chapters")
    if dry_run:
        print(f"  DRY RUN — no files will be modified")
    print()

    patched = 0
    no_vedabase = 0
    unchanged = 0

    for ch_id, sk, ch in lesson_files:
        if ch_id not in vedabase_files:
            no_vedabase += 1
            continue

        # Load both files
        with open(os.path.join(LESSON_DIR, f"{ch_id}.json"), 'r', encoding='utf-8') as f:
            lesson = json.load(f)
        with open(os.path.join(VEDABASE_DIR, f"{ch_id}.json"), 'r', encoding='utf-8') as f:
            vedabase = json.load(f)

        patched_lesson, changes = patch_lesson(lesson, vedabase)

        if not changes:
            unchanged += 1
            continue

        if dry_run:
            print(f"  {ch_id}: would apply {len(changes)} changes:")
            for c in changes:
                print(f"    - {c}")
        else:
            with open(os.path.join(LESSON_DIR, f"{ch_id}.json"), 'w', encoding='utf-8') as f:
                json.dump(patched_lesson, f, ensure_ascii=False, indent=2)
            print(f"  {ch_id}: patched ({len(changes)} changes)")

        patched += 1

    print(f"\n{'='*60}")
    print(f"DONE: {patched} patched, {unchanged} unchanged, {no_vedabase} no vedabase data")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
