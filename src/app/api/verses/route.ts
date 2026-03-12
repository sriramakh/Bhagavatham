import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

function loadVerses() {
  const filePath = path.join(process.cwd(), 'data', 'verses.json');
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

// GET /api/verses?skandha=1&chapter=1
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const skandha = searchParams.get('skandha');
    const chapter = searchParams.get('chapter');

    const data = loadVerses();

    if (skandha && chapter) {
      const sk = data.skandhas.find((s: any) => s.number === parseInt(skandha));
      if (!sk) return NextResponse.json({ error: 'Skandha not found' }, { status: 404 });
      const ch = sk.chapters.find((c: any) => c.num === parseInt(chapter));
      if (!ch) return NextResponse.json({ error: 'Chapter not found' }, { status: 404 });

      // Check if verse image exists
      if (ch.verse?.ref) {
        const safeRef = ch.verse.ref.replace(/[^a-zA-Z0-9.]/g, '_').replace(/\s+/g, '_');
        const imagePath = `/images/verses/verse_${safeRef}.png`;
        const fullPath = path.join(process.cwd(), 'public', imagePath);
        if (fs.existsSync(fullPath)) {
          ch.verse.imagePath = imagePath;
        }
      }

      return NextResponse.json(ch);
    }

    if (skandha) {
      const sk = data.skandhas.find((s: any) => s.number === parseInt(skandha));
      if (!sk) return NextResponse.json({ error: 'Skandha not found' }, { status: 404 });
      return NextResponse.json(sk);
    }

    // Return overview of all skandhas
    return NextResponse.json({
      skandhas: data.skandhas.map((s: any) => ({
        number: s.number,
        name: s.name,
        nameDevanagari: s.nameDevanagari,
        description: s.description,
        chapterCount: s.chapters.length,
      }))
    });
  } catch (error: any) {
    console.error('Verses error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
