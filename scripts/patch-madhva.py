#!/usr/bin/env python3
"""
Patch generated lessons with REAL Madhvacharya teachings extracted from
Sri Bhagavata Tatparya Nirnaya PDF (via Gemini Vision OCR).

Replaces the hallucinated madhvaTeaching field with content derived from
actual tatparya-cache data.

Usage:
    python scripts/patch-madhva.py              # Patch all lessons
    python scripts/patch-madhva.py 1-1          # Single chapter
    python scripts/patch-madhva.py --dry-run    # Preview without writing
"""
import os, sys, json, glob

SCRIPT_DIR = os.path.dirname(__file__)
LESSON_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'generated-lessons')
TATPARYA_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'tatparya-cache')


def build_madhva_html(tatparya):
    """Convert tatparya cache JSON into formatted HTML for madhvaTeaching field."""
    if not tatparya or not tatparya.get('found', False):
        return None

    parts = []

    # English summary (main teaching)
    summary = tatparya.get('english_summary', '').strip()
    if summary:
        parts.append(f'<p>{summary}</p>')

    # Key teachings as bullet points
    teachings = tatparya.get('key_teachings', [])
    if teachings:
        items = ''.join(f'<li>{t}</li>' for t in teachings if t.strip())
        if items:
            parts.append(f'<p><strong>Key points from the Tatparya Nirnaya:</strong></p><ul>{items}</ul>')

    # Dvaita concepts with key-concept spans
    concepts = tatparya.get('dvaita_concepts', [])
    if concepts:
        concept_parts = []
        for c in concepts:
            if ':' in c:
                term, explanation = c.split(':', 1)
                concept_parts.append(
                    f'<span class="key-concept">{term.strip()}</span>: {explanation.strip()}'
                )
            else:
                concept_parts.append(f'<span class="key-concept">{c.strip()}</span>')
        if concept_parts:
            parts.append(
                '<p><strong>Dvaita concepts:</strong> ' + '. '.join(concept_parts) + '</p>'
            )

    # Sanskrit excerpts (show 1-2 key quotes)
    excerpts = tatparya.get('sanskrit_excerpts', [])
    if excerpts:
        # Show up to 2 excerpts
        shown = excerpts[:2]
        quotes = ' '.join(f'<em>"{e}"</em>' for e in shown)
        parts.append(f'<p><strong>From the Tatparya Nirnaya:</strong> {quotes}</p>')

    if not parts:
        return None

    return '\n'.join(parts)


def main():
    dry_run = '--dry-run' in sys.argv
    target = None
    for arg in sys.argv[1:]:
        if '-' in arg and arg[0].isdigit():
            target = arg

    # Find all tatparya cache files
    cache_files = sorted(glob.glob(os.path.join(TATPARYA_DIR, '*.json')))
    if not cache_files:
        print('No tatparya cache files found. Run extract-tatparya.py first.')
        sys.exit(1)

    patched = 0
    skipped = 0
    no_lesson = 0
    not_found = 0

    for cache_path in cache_files:
        ch_id = os.path.splitext(os.path.basename(cache_path))[0]
        if target and ch_id != target:
            continue

        lesson_path = os.path.join(LESSON_DIR, f'{ch_id}.json')
        if not os.path.exists(lesson_path):
            no_lesson += 1
            continue

        with open(cache_path, encoding='utf-8') as f:
            tatparya = json.load(f)

        if not tatparya.get('found', False):
            not_found += 1
            continue

        html = build_madhva_html(tatparya)
        if not html:
            not_found += 1
            continue

        with open(lesson_path, encoding='utf-8') as f:
            lesson = json.load(f)

        old_teaching = lesson.get('madhvaTeaching', '')
        lesson['madhvaTeaching'] = html

        if dry_run:
            print(f'  {ch_id}: would patch ({len(old_teaching)} -> {len(html)} chars)')
        else:
            with open(lesson_path, 'w', encoding='utf-8') as f:
                json.dump(lesson, f, ensure_ascii=False, indent=2)
            print(f'  {ch_id}: patched ({len(old_teaching)} -> {len(html)} chars)')

        patched += 1

    print(f'\n{"="*60}')
    action = 'Would patch' if dry_run else 'Patched'
    print(f'{action}: {patched} lessons')
    print(f'Skipped (no tatparya): {not_found}, No lesson file: {no_lesson}')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
