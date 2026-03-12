'use client';

import React, { memo, useMemo } from 'react';
import { SanskritWord } from '@/types';
import { speakWord } from '@/lib/speech';

interface WordBankProps {
  words: SanskritWord[];
}

const WordBank = memo(function WordBank({ words }: WordBankProps) {
  const uniqueWords = useMemo(() => {
    const seen = new Set<string>();
    return words.filter((w) => {
      if (seen.has(w.san)) return false;
      seen.add(w.san);
      return true;
    });
  }, [words]);

  return (
    <aside className="bg-[#12121e] border-l border-[#2a2a3e] p-5 px-4 overflow-y-auto h-[calc(100vh-56px)] sticky top-14">
      <h3 className="font-heading text-[0.75rem] text-[#d4a843] tracking-[1px] uppercase mb-3">
        {'\uD83D\uDCDA'} Sanskrit Word Bank
      </h3>

      {uniqueWords.length === 0 ? (
        <p className="text-[#6b6157] text-[0.8rem] italic text-center py-5">
          Learn Sanskrit words during your quest to fill your word bank.
        </p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {uniqueWords.map((word, i) => (
            <WordCard key={`${word.san}-${i}`} word={word} />
          ))}
        </div>
      )}
    </aside>
  );
});

const WordCard = memo(function WordCard({ word }: { word: SanskritWord }) {
  return (
    <div className="bg-[#1a1a2e] border border-[#2a2a3e] rounded-lg p-2.5 cursor-pointer transition-all hover:border-[#8a6d2b] hover:-translate-x-0.5 group">
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="font-sanskrit text-[#f0d078] text-[1.1rem]">{word.san}</div>
          <div className="text-[#f4a03b] text-[0.75rem] italic">{word.trans}</div>
          <div className="text-[#a89b8c] text-[0.75rem] mt-0.5">{word.mean}</div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            speakWord(word.san || word.trans);
          }}
          className="text-[#8a6d2b] hover:text-[#d4a843] transition-colors text-lg ml-2 flex-shrink-0 opacity-60 group-hover:opacity-100"
          title="Listen to pronunciation"
        >
          {'\uD83D\uDD0A'}
        </button>
      </div>
    </div>
  );
});

export default WordBank;
