import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// Condensed character descriptions for MiniMax (1500 char prompt limit)
const CHAR_SHORT: Record<string, string> = {
  krishna: "Lord Krishna: young deity with deep blue-black skin, lotus eyes, enigmatic smile, golden crown with peacock feather, yellow silk dhoti, wildflower garland, holding flute",
  vishnu: "Lord Vishnu: majestic blue-black skin, four arms holding conch/discus/mace/lotus, golden crown, kaustubha gem on chest, yellow silk, on serpent Shesha",
  brahma: "Lord Brahma: elderly deity with four faces, reddish-golden skin, white beard, holding Vedas/water pot/rosary/lotus, white garments, seated on lotus",
  shiva: "Lord Shiva: ash-smeared fair skin, matted dreadlocks with crescent moon, third eye, tiger skin, serpent ornaments, trident and damaru",
  suta: "Suta Goswami: middle-aged sage, warm brown skin, saffron robes, shaved head with shikha tuft, sacred thread, gentle smile",
  shaunaka: "Shaunaka Rishi: elderly sage, brown skin, long white beard, bark-cloth with saffron shawl, rudraksha mala",
  vyasa: "Vyasadeva: elderly sage, dark brown skin, grey matted hair, grey beard, powerful build, white garments, palm-leaf manuscripts",
  shukadeva: "Shukadeva: youth of 16, luminous fair skin, shaved head, loincloth only, large innocent eyes, spiritual glow",
  parikshit: "King Parikshit: noble young king, fair golden-brown skin, simple white garments, regal features, sitting by Ganges",
  narada: "Narada Muni: eternally youthful, golden-fair skin, carrying veena, white garments, shikha, ecstatic smile",
  madhvacharya: "Madhvacharya: powerfully built, dark brown skin, shaved head with Vaishnava tilaka, saffron robes, holding scriptures",
};

const TANJORE_STYLE = "Traditional South Indian Tanjore painting style. Rich jewel-tone colors, gold leaf accents on ornaments/halos/borders. Ornamental temple-motif borders. Serene expressions, elongated almond eyes. Warm golden light. Sacred, luminous, devotional.";

export async function POST(req: NextRequest) {
  try {
    const { verseRef, translation, characterIds, chapterTitle, chapterId } = await req.json();

    // Try chapter-based filename first (matches batch-generated images)
    const chapterFilename = chapterId ? `chapter_${chapterId}.png` : null;
    const publicDir = path.join(process.cwd(), 'public', 'images', 'verses');

    // Check chapter image cache first
    if (chapterFilename) {
      const chapterPath = path.join(publicDir, chapterFilename);
      if (fs.existsSync(chapterPath)) {
        return NextResponse.json({ url: `/images/verses/${chapterFilename}`, cached: true });
      }
    }

    // Legacy filename check
    const safeRef = verseRef?.replace(/[^a-zA-Z0-9.]/g, '_').replace(/\s+/g, '_') || 'unknown';
    const legacyFilename = `verse_${safeRef}.png`;
    const legacyPath = path.join(publicDir, legacyFilename);
    if (fs.existsSync(legacyPath)) {
      return NextResponse.json({ url: `/images/verses/${legacyFilename}`, cached: true });
    }

    // Ensure directory exists
    fs.mkdirSync(publicDir, { recursive: true });

    // Build condensed character descriptions (max 3 chars for prompt limit)
    const charDescs = (characterIds || [])
      .slice(0, 3)
      .map((id: string) => CHAR_SHORT[id])
      .filter(Boolean)
      .join('\n');

    const charsText = charDescs || "Indian sages in saffron robes gathered around sacred fire in ancient forest";

    // Build prompt under 1500 chars for MiniMax
    let prompt = `Tanjore painting of scene from Srimad Bhagavatam: "${chapterTitle || 'Sacred Scene'}"

${translation ? `Verse: "${translation.substring(0, 120)}"` : ''}

Characters (match exactly):
${charsText}

Style: ${TANJORE_STYLE}
No text or writing in the image.`;

    // Truncate to 1500 if needed
    if (prompt.length > 1490) {
      prompt = prompt.substring(0, 1487) + '...';
    }

    // Call MiniMax image generation
    const minimaxToken = process.env.MINIMAX_API_TOKEN;
    if (!minimaxToken) {
      return NextResponse.json({ error: 'MINIMAX_API_TOKEN not configured' }, { status: 500 });
    }

    const response = await fetch('https://api.minimax.io/v1/image_generation', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${minimaxToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'image-01',
        prompt,
        aspect_ratio: '1:1',
        response_format: 'base64',
        n: 1,
        prompt_optimizer: true,
      }),
    });

    const data = await response.json();

    if (data.base_resp?.status_code !== 0) {
      console.error('MiniMax error:', data.base_resp?.status_msg);
      return NextResponse.json(
        { error: data.base_resp?.status_msg || 'Image generation failed' },
        { status: 500 }
      );
    }

    const b64 = data.data?.image_base64?.[0];
    if (!b64) {
      return NextResponse.json({ error: 'No image data returned' }, { status: 500 });
    }

    // Save to disk with chapter-based filename
    const outputFilename = chapterFilename || legacyFilename;
    const outputPath = path.join(publicDir, outputFilename);
    const buffer = Buffer.from(b64, 'base64');
    fs.writeFileSync(outputPath, buffer);

    return NextResponse.json({ url: `/images/verses/${outputFilename}`, cached: false });
  } catch (error: any) {
    console.error('Image generation error:', error);
    return NextResponse.json(
      { error: error.message || 'Image generation failed' },
      { status: 500 }
    );
  }
}
