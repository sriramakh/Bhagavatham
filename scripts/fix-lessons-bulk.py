#!/usr/bin/env python3
"""
Bulk fix structural quality issues in generated lessons:
1. Copy 'full' from verse.words into matching sanskritWords
2. Ensure all verse words appear in sanskritWords
3. Populate empty 'full' fields in sanskritWords from verse.words
4. Ensure minimum word count by promoting verse words
"""
import os, json

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'generated-lessons')

files = sorted(
    [f for f in os.listdir(CACHE_DIR) if f.endswith('.json')],
    key=lambda f: (int(f.replace('.json','').split('-')[0]), int(f.replace('.json','').split('-')[1]))
)

fixed_count = 0
total_words_added = 0
total_fulls_fixed = 0

for fname in files:
    path = os.path.join(CACHE_DIR, fname)
    with open(path) as f:
        ch = json.load(f)

    modified = False
    verse_words = ch.get('verse', {}).get('words', [])
    lesson_words = ch.get('sanskritWords', [])

    # Build lookup of verse words by san (Devanagari)
    verse_lookup = {}
    for vw in verse_words:
        san = vw.get('san', '')
        if san:
            verse_lookup[san] = vw

    # Fix 1: Populate empty 'full' fields in lesson words from verse words
    for lw in lesson_words:
        san = lw.get('san', '')
        if not lw.get('full', '').strip() and san in verse_lookup:
            lw['full'] = verse_lookup[san].get('full', lw.get('mean', ''))
            total_fulls_fixed += 1
            modified = True
        elif not lw.get('full', '').strip():
            # No matching verse word — generate a reasonable full from mean
            lw['full'] = lw.get('mean', '')
            total_fulls_fixed += 1
            modified = True

    # Fix 2: Ensure all verse words are in sanskritWords
    lesson_sans = {w.get('san', '') for w in lesson_words}
    for vw in verse_words:
        san = vw.get('san', '')
        if san and san not in lesson_sans:
            # Promote verse word to lesson word
            new_word = {
                'san': vw['san'],
                'trans': vw.get('trans', ''),
                'mean': vw.get('mean', ''),
                'full': vw.get('full', vw.get('mean', '')),
                'example': f"{vw['san']} — from the verse"
            }
            lesson_words.append(new_word)
            lesson_sans.add(san)
            total_words_added += 1
            modified = True

    if modified:
        ch['sanskritWords'] = lesson_words
        with open(path, 'w') as f:
            json.dump(ch, f, ensure_ascii=False, indent=2)
        fixed_count += 1

print(f"Processed {len(files)} lessons")
print(f"Modified: {fixed_count}")
print(f"'full' fields fixed: {total_fulls_fixed}")
print(f"Words added to sanskritWords: {total_words_added}")

# Verify
empty_fulls = 0
few_words = 0
for fname in files:
    with open(os.path.join(CACHE_DIR, fname)) as f:
        ch = json.load(f)
    sw = ch.get('sanskritWords', [])
    if any(not w.get('full', '').strip() for w in sw):
        empty_fulls += 1
    if len(sw) < 5:
        few_words += 1

print(f"\nAfter fix:")
print(f"  Lessons with empty 'full': {empty_fulls}/{len(files)}")
print(f"  Lessons with <5 words: {few_words}/{len(files)}")
