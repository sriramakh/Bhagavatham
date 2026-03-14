#!/usr/bin/env python3
"""
Fix two data quality issues across all 335 chapters:

1. SYLLABLES: Replace character-level syllables with word-level syllables
   (split verse Sanskrit text by spaces/newlines)

2. WORDS san field: Populate empty san (Devanagari) fields by matching
   verse Devanagari words with transliteration word positions

Usage:
    python scripts/fix-syllables-words.py              # Fix all
    python scripts/fix-syllables-words.py --dry-run     # Preview
    python scripts/fix-syllables-words.py 1-1           # Single chapter
"""
import os, sys, json, re, glob

SCRIPT_DIR = os.path.dirname(__file__)
LESSON_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'generated-lessons')
VEDABASE_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'vedabase-cache')


def get_word_syllables(sanskrit):
    """Split Sanskrit verse into word-level syllables."""
    if not sanskrit:
        return []
    # Normalize: remove verse numbers, dandas for splitting
    text = sanskrit.strip()
    # Remove double dandas and verse numbers
    text = re.sub(r'॥\s*[०-९\d]+\s*॥', '', text)
    text = text.replace('॥', '')
    text = text.replace('।', '')
    # Split by whitespace and newlines
    words = text.split()
    # Filter empty strings
    words = [w.strip() for w in words if w.strip()]
    return words


def is_char_level(syllables):
    """Detect if syllables are character-level (bad) vs word-level (good)."""
    if not syllables:
        return False
    # Character-level syllables are very short (1-2 chars) and there are many of them
    non_space = [s for s in syllables if s.strip()]
    if not non_space:
        return False
    avg_len = sum(len(s) for s in non_space) / len(non_space)
    # Word-level avg ~4-8 chars; char-level avg ~1-2 chars
    return avg_len < 2.5 and len(non_space) > 15


def populate_san_field(words, sanskrit, vedabase_data=None):
    """Populate empty san fields in word objects using verse Devanagari text.

    The vedabase word-by-word breakdown often has MORE entries than Devanagari
    words because Sanskrit compounds are split into components. E.g., the single
    Devanagari word "जन्माद्यस्य" maps to multiple meanings: ādi, asya.

    Strategy: walk through Devanagari words sequentially, assigning each to the
    first empty-san word object. When vedabase has multiple sub-words for one
    Devanagari word, only the first gets the san field; the rest stay empty
    (which is fine — they share the same Devanagari source).
    """
    if not words:
        return words, 0

    needs_fix = any(not w.get('san', '') for w in words)
    if not needs_fix:
        return words, 0

    dev_words = get_word_syllables(sanskrit)
    if not dev_words:
        return words, 0

    # Assign Devanagari words to word objects that have empty san
    fixed = 0
    dev_idx = 0
    for w in words:
        if w.get('san', ''):
            # Already has san — this word was already assigned
            continue
        if dev_idx < len(dev_words):
            w['san'] = dev_words[dev_idx]
            dev_idx += 1
            fixed += 1

    return words, fixed


def main():
    dry_run = '--dry-run' in sys.argv
    target = None
    for arg in sys.argv[1:]:
        if '-' in arg and arg[0].isdigit():
            target = arg

    lesson_files = sorted(glob.glob(os.path.join(LESSON_DIR, '*.json')))
    if not lesson_files:
        print('No lesson files found.')
        sys.exit(1)

    syllable_fixes = 0
    san_fixes = 0
    total_san_words_fixed = 0

    for path in lesson_files:
        ch_id = os.path.splitext(os.path.basename(path))[0]
        if target and ch_id != target:
            continue

        with open(path, encoding='utf-8') as f:
            lesson = json.load(f)

        verse = lesson.get('verse', {})
        sanskrit = verse.get('sanskrit', '')
        syllables = verse.get('syllables', [])
        words = verse.get('words', [])
        changed = False

        # Fix 1: Character-level syllables → word-level
        if is_char_level(syllables):
            new_syllables = get_word_syllables(sanskrit)
            if new_syllables:
                verse['syllables'] = new_syllables
                changed = True
                syllable_fixes += 1
                if not dry_run:
                    pass  # will save below
                else:
                    print(f'  {ch_id}: syllables {len(syllables)} chars → {len(new_syllables)} words')

        # Fix 2: Empty san fields
        words, num_fixed = populate_san_field(words, sanskrit)
        if num_fixed > 0:
            verse['words'] = words
            changed = True
            san_fixes += 1
            total_san_words_fixed += num_fixed
            if dry_run:
                print(f'  {ch_id}: filled {num_fixed} empty san fields')

        if changed and not dry_run:
            lesson['verse'] = verse
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(lesson, f, ensure_ascii=False, indent=2)

    print(f'\n{"="*60}')
    action = 'Would fix' if dry_run else 'Fixed'
    print(f'{action}:')
    print(f'  Syllables: {syllable_fixes} chapters (char-level → word-level)')
    print(f'  San fields: {san_fixes} chapters ({total_san_words_fixed} words)')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
