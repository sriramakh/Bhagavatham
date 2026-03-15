'use client';

import React, { memo, useState, useCallback, useRef, useEffect } from 'react';
import { Verse } from '@/types';
import { speakVerse, speakWord, speakSyllable, stopSpeech } from '@/lib/speech';

interface VerseStudyProps {
  verse: Verse;
  madhvaTeaching: string;
  chapterLabel: string;
  chapterId: string;
  characterIds?: string[];
  chapterTitle: string;
  onContinue: () => void;
  onBack: () => void;
}

const VerseStudy = memo(function VerseStudy({
  verse,
  madhvaTeaching,
  chapterLabel,
  chapterId,
  characterIds,
  chapterTitle,
  onContinue,
  onBack,
}: VerseStudyProps) {
  const [highlightedSyllable, setHighlightedSyllable] = useState<number | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(verse.imagePath || null);
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);
  const karaokeRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up karaoke on unmount
  useEffect(() => {
    return () => {
      if (karaokeRef.current) clearTimeout(karaokeRef.current);
      stopSpeech();
    };
  }, []);

  const playFullVerse = useCallback(
    (slow?: boolean) => {
      speakVerse(chapterId, verse.sanskrit, slow);
    },
    [chapterId, verse.sanskrit]
  );

  const startKaraoke = useCallback(() => {
    stopSpeech();
    if (karaokeRef.current) clearTimeout(karaokeRef.current);

    const syllables = verse.syllables;
    let i = 0;

    async function playNext() {
      if (i >= syllables.length) {
        setHighlightedSyllable(null);
        return;
      }
      while (i < syllables.length && syllables[i] === ' ') i++;
      if (i >= syllables.length) {
        setHighlightedSyllable(null);
        return;
      }

      setHighlightedSyllable(i);
      try {
        await speakSyllable(syllables[i]);
      } catch { /* ignore */ }
      i++;
      karaokeRef.current = setTimeout(playNext, 300);
    }
    playNext();
  }, [verse.syllables]);

  const handleSyllableClick = useCallback(
    async (idx: number) => {
      if (verse.syllables[idx] && verse.syllables[idx] !== ' ') {
        setHighlightedSyllable(idx);
        try {
          await speakSyllable(verse.syllables[idx]);
        } catch { /* ignore */ }
        setHighlightedSyllable(null);
      }
    },
    [verse.syllables]
  );

  const handleGenerateImage = useCallback(async () => {
    setImageLoading(true);
    setImageError(null);
    try {
      const res = await fetch('/api/generate-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          verseRef: verse.ref,
          translation: verse.translation,
          madhvaTeaching: madhvaTeaching.replace(/<[^>]+>/g, ''),
          characterIds: characterIds || [],
          chapterTitle,
        }),
      });
      const data = await res.json();
      if (data.error) {
        setImageError(data.error);
      } else {
        setImageUrl(data.url);
      }
    } catch (err: unknown) {
      setImageError(err instanceof Error ? err.message : 'Image generation failed');
    } finally {
      setImageLoading(false);
    }
  }, [verse.ref, verse.translation, madhvaTeaching, characterIds, chapterTitle]);

  return (
    <div className="max-w-[700px] mx-auto animate-fadeIn">
      {/* Header */}
      <div className="text-center mb-5">
        <div className="font-heading text-[#8a6d2b] text-[0.75rem] tracking-[2px] uppercase">
          {chapterLabel}
        </div>
        <h2 className="font-heading text-[#f0d078] text-[1.5rem] mt-1">Verse Study</h2>
      </div>

      {/* Verse Box */}
      <div className="bg-gradient-to-br from-[rgba(212,168,67,0.08)] to-[rgba(212,168,67,0.02)] border border-[rgba(212,168,67,0.3)] rounded-xl p-4 sm:p-8 text-center my-5 relative">
        {/* Decorative markers */}
        <span className="absolute top-2.5 left-4 font-heading text-[#8a6d2b] text-2xl opacity-30">
          {'\u0965'}
        </span>
        <span className="absolute bottom-2.5 right-4 font-heading text-[#8a6d2b] text-2xl opacity-30">
          {'\u0965'}
        </span>

        <div className="font-heading text-[#8a6d2b] text-[0.75rem] tracking-[2px] uppercase mb-4">
          {verse.ref}
        </div>

        {/* Audio Controls */}
        <div className="flex flex-wrap justify-center gap-2 mb-4">
          <AudioButton
            onClick={() => playFullVerse(false)}
            color="gold"
            label={'\uD83D\uDD0A Listen to Full Shloka'}
          />
          <AudioButton
            onClick={() => playFullVerse(true)}
            color="blue"
            label={'\uD83D\uDC22 Slow Mode'}
          />
          <AudioButton
            onClick={startKaraoke}
            color="saffron"
            label={'\uD83C\uDFA4 Follow Along'}
          />
          <AudioButton onClick={stopSpeech} color="crimson" label={'\u23F9 Stop'} />
        </div>

        <div className="font-sanskrit text-[#f0d078] text-[1.5rem] leading-[2] mb-4 whitespace-pre-line">
          {verse.sanskrit}
        </div>
        <div className="text-[#a89b8c] text-[0.9rem] italic leading-[1.7] max-w-[550px] mx-auto">
          &ldquo;{verse.translation}&rdquo;
        </div>
      </div>

      {/* Verse Image — disabled for now, pending improved generation */}

      {/* Pronunciation Guide */}
      <div className="my-5 text-center">
        <h3 className="font-heading text-[#d4a843] text-[0.85rem] tracking-[1px] uppercase mb-3">
          Pronunciation Guide — tap each syllable to hear it
        </h3>
        <div className="flex flex-wrap gap-1 justify-center">
          {verse.syllables.map((s, i) => {
            if (s === ' ') {
              return <span key={i} className="w-3 inline-block" />;
            }
            const isHighlighted = highlightedSyllable === i;
            return (
              <span
                key={i}
                onClick={() => handleSyllableClick(i)}
                className={`px-1.5 py-2 rounded font-sanskrit text-[1.2rem] cursor-pointer transition-all ${
                  isHighlighted
                    ? 'text-[#f0d078] bg-[rgba(212,168,67,0.15)] scale-110'
                    : 'text-[#a89b8c] hover:text-[#f0d078]'
                }`}
              >
                {s}
              </span>
            );
          })}
        </div>
        <div className="mt-3">
          <button
            onClick={startKaraoke}
            className="text-[0.75rem] px-3.5 py-1.5 border border-[#e8862a] text-[#f4a03b] bg-transparent rounded-full cursor-pointer hover:bg-[rgba(232,134,42,0.1)] transition-all"
          >
            {'\uD83D\uDD0A'} Auto-play syllables
          </button>
        </div>
      </div>

      {/* Word-by-Word Breakdown */}
      <div className="my-6">
        <h3 className="font-heading text-[#d4a843] text-[0.85rem] tracking-[1px] uppercase mb-3 text-center">
          Word-by-Word Breakdown
        </h3>
        <div className="flex flex-wrap gap-2 justify-center">
          {verse.words.map((w, i) => (
            <div
              key={i}
              className="flex flex-col items-center bg-[#1a1a2e] border border-[#2a2a3e] rounded-lg px-2.5 py-2.5 cursor-pointer transition-all min-w-[60px] hover:border-[#8a6d2b] hover:bg-[#222240] hover:-translate-y-0.5 relative group"
            >
              {/* Tooltip */}
              <div className="absolute bottom-[calc(100%+8px)] left-1/2 -translate-x-1/2 bg-[#0a0a12] border border-[#8a6d2b] rounded-lg px-3 py-2 text-[0.75rem] text-[#e8e0d0] whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-10">
                {w.full}
              </div>
              <span className="font-sanskrit text-[#f0d078] text-base">{w.san}</span>
              <span className="text-[#f4a03b] text-[0.65rem] italic mt-0.5">{w.trans}</span>
              <span className="text-[#a89b8c] text-[0.65rem] mt-0.5">{w.mean}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  speakWord(w.san || w.trans);
                }}
                className="text-[0.6rem] text-[#8a6d2b] cursor-pointer mt-1 opacity-70 hover:opacity-100 bg-transparent border-none"
              >
                {'\uD83D\uDD0A'} Listen
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Madhvacharya's Teaching */}
      <div className="bg-gradient-to-br from-[rgba(212,168,67,0.12)] to-[rgba(212,168,67,0.04)] border-2 border-[#8a6d2b] rounded-xl p-4 sm:p-6 my-6 relative">
        <div className="absolute -top-px left-5 right-5 h-0.5 bg-gradient-to-r from-transparent via-[#d4a843] to-transparent" />
        <div className="font-heading text-[#d4a843] text-[0.8rem] tracking-[2px] uppercase mb-2.5 flex items-center gap-2">
          {'\uD83E\uDEB7'} Madhvacharya&apos;s Teaching
        </div>
        <div
          className="text-[#e8e0d0] text-[0.9rem] leading-[1.7] [&_.key-concept]:inline [&_.key-concept]:bg-[rgba(212,168,67,0.15)] [&_.key-concept]:px-1.5 [&_.key-concept]:rounded [&_.key-concept]:text-[#f0d078] [&_.key-concept]:font-medium"
          dangerouslySetInnerHTML={{ __html: madhvaTeaching }}
        />
      </div>

      {/* Navigation */}
      <div className="flex justify-between items-center mt-10 pt-5 border-t border-[#2a2a3e]">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 px-5 py-2 border border-[#8a6d2b] text-[#f0d078] rounded-lg font-heading text-[0.8rem] tracking-[1px] bg-transparent hover:bg-[rgba(212,168,67,0.1)] hover:border-[#d4a843] transition-all cursor-pointer"
        >
          {'\u2190'} Back
        </button>
        <button
          onClick={onContinue}
          className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-br from-[#8a6d2b] to-[#d4a843] text-[#0a0a12] rounded-lg font-heading text-[0.9rem] tracking-[1px] shadow-[0_4px_15px_rgba(212,168,67,0.3)] hover:-translate-y-0.5 hover:shadow-[0_6px_25px_rgba(212,168,67,0.4)] active:translate-y-0 transition-all cursor-pointer"
        >
          Continue to Sanskrit Lesson {'\u2192'}
        </button>
      </div>
    </div>
  );
});

function AudioButton({
  onClick,
  color,
  label,
}: {
  onClick: () => void;
  color: 'gold' | 'blue' | 'saffron' | 'crimson';
  label: string;
}) {
  const colorMap = {
    gold: 'border-[#d4a843] text-[#d4a843] hover:bg-[rgba(212,168,67,0.1)]',
    blue: 'border-[#2980b9] text-[#2980b9] hover:bg-[rgba(41,128,185,0.1)]',
    saffron: 'border-[#e8862a] text-[#f4a03b] hover:bg-[rgba(232,134,42,0.1)]',
    crimson: 'border-[#c0392b] text-[#c0392b] hover:bg-[rgba(192,57,43,0.1)]',
  };

  return (
    <button
      onClick={onClick}
      className={`px-3 py-2 rounded-full border text-[0.75rem] min-h-[44px] bg-transparent cursor-pointer transition-all ${colorMap[color]}`}
    >
      {label}
    </button>
  );
}

export default VerseStudy;
