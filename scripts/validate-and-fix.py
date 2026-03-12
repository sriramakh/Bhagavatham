#!/usr/bin/env python3
"""
Validate all generated lessons and regenerate ones that fail quality checks.
Uses GPT-4o (not mini) for higher quality regeneration with the actual PDF text.
"""
import os, sys, json, time, re, fitz
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

SCRIPT_DIR = os.path.dirname(__file__)
CACHE_DIR = os.path.join(SCRIPT_DIR, '..', 'data', 'generated-lessons')
PDF_PATH = os.path.join(SCRIPT_DIR, '..', '..', 'srimad-bhagavata-mahapurana-english-translations.pdf')

client = OpenAI()

# ─── Step 1: Extract actual verse text from the English PDF per chapter ───

def extract_chapter_text(doc, skandha, chapter, max_chars=6000):
    """Extract the actual text content for a specific chapter from the PDF."""
    full_text = ""
    capturing = False
    target = f"SB {skandha}.{chapter}:"
    next_ch = f"SB {skandha}.{chapter+1}:"
    next_sk = f"SB {skandha+1}.1:"

    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        if target in text:
            capturing = True
        if capturing:
            full_text += text + "\n"
            # Stop if we hit the next chapter
            if (next_ch in text or next_sk in text) and len(full_text) > 200:
                break
        if len(full_text) > max_chars:
            break

    # Trim to just this chapter's content
    start_idx = full_text.find(target)
    if start_idx > 0:
        full_text = full_text[start_idx:]

    end_markers = [next_ch, next_sk]
    for marker in end_markers:
        end_idx = full_text.find(marker, len(target))
        if end_idx > 0:
            full_text = full_text[:end_idx]

    return full_text[:max_chars]


# ─── Step 2: Validate a single lesson ───

def validate_lesson(ch_id, lesson):
    """Return list of issues found in a lesson."""
    issues = []
    v = lesson.get('verse', {})
    san = v.get('sanskrit', '')
    trans = v.get('translation', '')
    vwords = v.get('words', [])
    swords = lesson.get('sanskritWords', [])
    madhva = lesson.get('madhvaTeaching', '')
    story = lesson.get('story', [])
    quiz = lesson.get('quiz', [])
    boss = lesson.get('boss', [])

    # Critical issues
    if len(san) < 20:
        issues.append('CRITICAL: Sanskrit verse too short or missing')
    if len(trans) < 40:
        issues.append('CRITICAL: Translation too short')
    if trans.rstrip().endswith('...') or trans.rstrip().endswith('…'):
        issues.append('CRITICAL: Translation truncated')
    if not vwords:
        issues.append('CRITICAL: No verse word breakdown')
    if not story:
        issues.append('CRITICAL: No story beats')

    # Quality issues
    if len(vwords) < 4:
        issues.append(f'QUALITY: Only {len(vwords)} verse words (need all words from shloka)')
    if len(swords) < 3:
        issues.append(f'QUALITY: Only {len(swords)} lesson words (need at least 5)')

    # Check word completeness
    empty_full = [w for w in vwords if not w.get('full', '').strip()]
    if empty_full:
        issues.append(f'QUALITY: {len(empty_full)}/{len(vwords)} verse words missing "full" explanation')

    swords_no_full = [w for w in swords if not w.get('full', '').strip()]
    if swords_no_full:
        issues.append(f'QUALITY: {len(swords_no_full)}/{len(swords)} lesson words missing "full" explanation')

    if len(madhva) < 150:
        issues.append(f'QUALITY: Madhva teaching too short ({len(madhva)} chars)')
    if madhva and not madhva.rstrip().endswith(('.', '!', '?', '।', '"')):
        issues.append('QUALITY: Madhva teaching appears truncated')

    if len(quiz) < 5:
        issues.append(f'QUALITY: Only {len(quiz)} quiz questions (need 5)')
    if len(boss) < 3:
        issues.append(f'QUALITY: Only {len(boss)} boss questions (need 4)')

    if len(story) < 4:
        issues.append(f'QUALITY: Only {len(story)} story beats (need 5-6)')

    return issues


# ─── Step 3: Regenerate a lesson with better prompt and actual PDF text ───

ENHANCED_PROMPT = """You are an expert Sanskrit scholar and educator creating content for a gamified Srimad Bhagavatam learning app that teaches Sanskrit and Madhvacharya's Dvaita Vedanta philosophy.

ACTUAL TEXT FROM THE PDF for Skandha {skandha}, Chapter {chapter} — "{title}":
---
{pdf_text}
---

Using the ACTUAL verses and content above, generate a comprehensive lesson. You MUST use the real shlokas from the text above, NOT made-up verses.

Output VALID JSON:
{{
  "id": "{skandha}-{chapter}",
  "skandha": {skandha},
  "num": {chapter},
  "title": "{title}",
  "desc": "One engaging sentence describing this chapter's content",
  "characters": {characters},
  "story": [
    // 5-6 beats mixing narration and dialogue. Make it vivid and engaging.
    {{"type": "narration", "text": "..."}},
    {{"type": "dialogue", "speaker": "CharacterName", "text": "..."}}
  ],
  "verse": {{
    "ref": "Srimad Bhagavatam {skandha}.{chapter}.X",
    "sanskrit": "FULL Devanagari text of the KEY verse (complete, not truncated)",
    "transliteration": "Complete IAST transliteration",
    "translation": "Complete English translation (do NOT truncate)",
    "syllables": ["each", "Devanagari", "syllable", "separately"],
    "words": [
      // EVERY word from the Sanskrit verse. Each word MUST have all 4 fields populated:
      {{"san": "देवनागरी", "trans": "IAST", "mean": "brief meaning", "full": "Detailed 1-2 sentence explanation of this word in context"}}
    ]
  }},
  "madhvaTeaching": "3-4 sentences on Madhvacharya's Dvaita interpretation of this chapter. Reference specific concepts: jīva-Brahma bheda (soul-God distinction), viṣṇu-sarvottamatva (Vishnu's supremacy), pañca-bheda (five-fold difference). Use Sanskrit philosophical terms with translations.",
  "sanskritWords": [
    // ALL words from verse.words, PLUS 2-3 additional important Sanskrit terms from this chapter.
    // Each MUST have all fields populated:
    {{"san": "देवनागरी", "trans": "IAST", "mean": "brief meaning", "full": "Detailed explanation with etymology or context", "example": "usage example from the verse"}}
  ],
  "quiz": [
    // Exactly 5 questions. Mix types:
    {{"type": "mcq", "question": "...", "options": ["A","B","C","D"], "correct": 0, "explanation": "Detailed explanation referencing the verse"}},
    {{"type": "fill", "question": "The Sanskrit word ___ means...", "answer": "word", "options": ["4","choices","here","too"], "explanation": "..."}},
    {{"type": "match", "question": "Match Sanskrit words to meanings:", "pairs": [["word1","meaning1"],["word2","meaning2"],["word3","meaning3"]], "explanation": "..."}}
  ],
  "boss": [
    // 4 harder questions requiring deeper understanding of Madhva's philosophy and Sanskrit grammar
  ]
}}

CRITICAL RULES:
1. Use the ACTUAL Sanskrit verse from the PDF text above — do NOT hallucinate shlokas
2. The verse.sanskrit field must be the COMPLETE shloka in Devanagari, not truncated
3. EVERY word in verse.words must have a non-empty "full" field (1-2 sentence explanation)
4. EVERY word in sanskritWords must have a non-empty "full" field AND "example" field
5. sanskritWords should include ALL verse words plus additional chapter vocabulary
6. Madhva's teaching must reference specific Dvaita concepts, not generic statements
7. Translation must be COMPLETE — never end with "..." or truncate mid-sentence
8. Quiz questions should test both Sanskrit vocabulary AND philosophical understanding"""


def regenerate_lesson(skandha, chapter, title, pdf_text, characters):
    """Regenerate a lesson with enhanced prompt and actual PDF text."""
    char_json = json.dumps(characters)
    prompt = ENHANCED_PROMPT.format(
        skandha=skandha, chapter=chapter, title=title,
        pdf_text=pdf_text[:4000], characters=char_json
    )

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are a Sanskrit scholar. Output ONLY valid JSON, no markdown fences or extra text. Ensure all text fields are complete and not truncated."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=8192,
                temperature=0.5,
            )

            text = response.choices[0].message.content.strip()
            # Remove markdown fences
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if "```" in text:
                    text = text[:text.rfind("```")].strip()

            lesson = json.loads(text)
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


# ─── Main ───

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "audit"
    delay = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

    # Load PDF
    print("Loading PDF...")
    doc = fitz.open(PDF_PATH)

    # Load all cached lessons
    files = sorted(
        [f for f in os.listdir(CACHE_DIR) if f.endswith('.json')],
        key=lambda f: (int(f.replace('.json','').split('-')[0]), int(f.replace('.json','').split('-')[1]))
    )

    print(f"Found {len(files)} cached lessons\n")

    # Audit all
    critical_fails = []
    quality_fails = []
    all_issues = {}

    for fname in files:
        ch_id = fname.replace('.json', '')
        with open(os.path.join(CACHE_DIR, fname)) as f:
            lesson = json.load(f)

        issues = validate_lesson(ch_id, lesson)
        if issues:
            all_issues[ch_id] = issues
            has_critical = any('CRITICAL' in i for i in issues)
            if has_critical:
                critical_fails.append(ch_id)
            else:
                quality_fails.append(ch_id)

    passed = len(files) - len(all_issues)
    print("=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    print(f"  Total lessons:    {len(files)}")
    print(f"  Passed:           {passed}")
    print(f"  Critical fails:   {len(critical_fails)}")
    print(f"  Quality fails:    {len(quality_fails)}")
    print()

    if critical_fails:
        print("CRITICAL FAILURES (must regenerate):")
        for ch_id in critical_fails:
            print(f"  {ch_id}:")
            for issue in all_issues[ch_id]:
                if 'CRITICAL' in issue:
                    print(f"    - {issue}")

    # Count issue frequency
    issue_counts = {}
    for ch_id, issues in all_issues.items():
        for issue in issues:
            tag = issue.split(':')[0].strip()
            issue_counts[tag] = issue_counts.get(tag, 0) + 1

    print("\nISSUE FREQUENCY:")
    for tag, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count}")

    if mode == "audit":
        print(f"\nRun with 'fix' to regenerate failed lessons:")
        print(f"  python3 scripts/validate-and-fix.py fix 2.0")
        return

    # ─── Fix mode ───
    if mode == "fix":
        # Regenerate all chapters that have issues (critical first, then quality)
        to_fix = critical_fails + quality_fails
        print(f"\n{'='*60}")
        print(f"REGENERATING {len(to_fix)} lessons...")
        print(f"{'='*60}")

        fixed = 0
        still_broken = 0

        for i, ch_id in enumerate(to_fix):
            parts = ch_id.split('-')
            skandha, chapter = int(parts[0]), int(parts[1])

            # Load existing lesson for title/characters
            with open(os.path.join(CACHE_DIR, f"{ch_id}.json")) as f:
                old = json.load(f)

            title = old.get('title', f'Skandha {skandha} Chapter {chapter}')
            characters = old.get('characters', old.get('characterIds', ['suta', 'shaunaka']))

            # Extract actual PDF text for this chapter
            pdf_text = extract_chapter_text(doc, skandha, chapter)
            if not pdf_text.strip():
                print(f"  [{i+1}/{len(to_fix)}] {ch_id} '{title[:40]}' — NO PDF TEXT FOUND, skipping")
                still_broken += 1
                continue

            print(f"  [{i+1}/{len(to_fix)}] {ch_id} '{title[:40]}' — regenerating... ({len(pdf_text)} chars PDF text)")

            new_lesson = regenerate_lesson(skandha, chapter, title, pdf_text, characters)
            if not new_lesson:
                print(f"    ✗ Regeneration failed")
                still_broken += 1
                continue

            # Validate the new lesson
            new_issues = validate_lesson(ch_id, new_lesson)
            new_critical = [i for i in new_issues if 'CRITICAL' in i]

            if new_critical:
                print(f"    ✗ Still has critical issues: {new_critical[0]}")
                still_broken += 1
                continue

            # Save the improved lesson
            old_issues = len(all_issues.get(ch_id, []))
            with open(os.path.join(CACHE_DIR, f"{ch_id}.json"), 'w') as f:
                json.dump(new_lesson, f, ensure_ascii=False, indent=2)

            remaining = len(new_issues)
            print(f"    ✓ Fixed ({old_issues} issues → {remaining})")
            fixed += 1

            time.sleep(delay)

        print(f"\n{'='*60}")
        print(f"FIX COMPLETE: {fixed} fixed, {still_broken} still need attention")
        print(f"{'='*60}")

    doc.close()


if __name__ == "__main__":
    main()
