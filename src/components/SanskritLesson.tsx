'use client';

import React, { memo, useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { SanskritWord } from '@/types';
import { speakWord } from '@/lib/speech';
import { shuffle } from '@/lib/gameState';

interface SanskritLessonProps {
  words: SanskritWord[];
  onContinue: () => void;
  onBack: () => void;
  onDndComplete: () => void;
  onDndError: () => void;
}

const SanskritLesson = memo(function SanskritLesson({
  words,
  onContinue,
  onBack,
  onDndComplete,
  onDndError,
}: SanskritLessonProps) {
  const dndWords = useMemo(
    () => shuffle([...words].filter((w) => w.san?.trim())).slice(0, 4),
    [words]
  );

  return (
    <div className="max-w-[700px] mx-auto animate-fadeIn">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="font-heading text-[#f0d078] text-[1.3rem]">Sanskrit Mini-Lesson</h2>
        <p className="text-[#a89b8c] text-[0.85rem] mt-1">
          Learn key words from this verse
        </p>
      </div>

      {/* Teach Cards */}
      <div className="space-y-4 mb-8">
        {words.map((w, i) => (
          <TeachCard key={`${w.san}-${i}`} word={w} />
        ))}
      </div>

      {/* Drag and Drop Exercise */}
      <DragDropExercise
        words={dndWords}
        onComplete={onDndComplete}
        onError={onDndError}
      />

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
          Continue to Quiz {'\u2192'}
        </button>
      </div>
    </div>
  );
});

const TeachCard = memo(function TeachCard({ word }: { word: SanskritWord }) {
  return (
    <div className="bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl p-4 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-5 transition-all hover:border-[#8a6d2b]">
      <div className="font-sanskrit text-[#f0d078] text-[1.8rem] sm:min-w-[100px] text-left sm:text-center w-full sm:w-auto">
        {word.san || word.trans}
      </div>
      <div className="flex-1">
        <div className="text-[#f4a03b] text-[0.9rem] italic">{word.trans}</div>
        <div className="text-[#e8e0d0] text-base mt-1">{word.mean}</div>
        {word.example && (
          <div className="text-[#6b6157] text-[0.8rem] mt-1.5">{word.example}</div>
        )}
      </div>
      <button
        onClick={() => speakWord(word.san || word.trans)}
        className="text-[1.2rem] cursor-pointer opacity-60 hover:opacity-100 transition-opacity flex-shrink-0 p-1 bg-transparent border-none"
        title="Listen to pronunciation"
      >
        {'\uD83D\uDD0A'}
      </button>
    </div>
  );
});

interface DragDropExerciseProps {
  words: SanskritWord[];
  onComplete: () => void;
  onError: () => void;
}

function DragDropExercise({ words, onComplete, onError }: DragDropExerciseProps) {
  const [matched, setMatched] = useState<Set<string>>(new Set());
  const [dragging, setDragging] = useState<string | null>(null);
  const [hoverTarget, setHoverTarget] = useState<string | null>(null);
  const [wrongTarget, setWrongTarget] = useState<string | null>(null);
  const touchDragRef = useRef<string | null>(null);

  const sources = useMemo(() => shuffle([...words]), [words]);
  const targets = useMemo(() => shuffle([...words]), [words]);

  const matchCount = matched.size;

  useEffect(() => {
    if (matchCount === words.length && words.length > 0) {
      onComplete();
    }
  }, [matchCount, words.length, onComplete]);

  const handleDrop = useCallback(
    (droppedWord: string, targetAnswer: string) => {
      if (matched.has(targetAnswer)) return;

      if (droppedWord === targetAnswer) {
        setMatched((prev) => new Set([...prev, targetAnswer]));
      } else {
        setWrongTarget(targetAnswer);
        onError();
        setTimeout(() => setWrongTarget(null), 500);
      }
    },
    [matched, onError]
  );

  // Touch support
  const handleTouchStart = useCallback((word: string) => {
    touchDragRef.current = word;
    setDragging(word);
  }, []);

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      if (!touchDragRef.current) return;
      setDragging(null);

      const touch = e.changedTouches[0];
      const el = document.elementFromPoint(touch.clientX, touch.clientY);
      const targetEl = el?.closest('[data-drop-answer]') as HTMLElement | null;

      if (targetEl) {
        const answer = targetEl.dataset.dropAnswer!;
        handleDrop(touchDragRef.current, answer);
      }
      touchDragRef.current = null;
    },
    [handleDrop]
  );

  return (
    <div className="my-8">
      <h3 className="font-heading text-[#d4a843] text-[0.85rem] tracking-[1px] uppercase mb-4 text-center">
        Match the Sanskrit Words
      </h3>
      <p className="text-center text-[#6b6157] text-[0.8rem] mb-4">
        Drag each Sanskrit word to its correct meaning
      </p>

      <div className="flex flex-col sm:flex-row gap-4 sm:gap-10 justify-center">
        {/* Sources column */}
        <div className="flex flex-col gap-2 w-full sm:min-w-[140px] sm:w-auto">
          <div className="text-[0.7rem] text-[#6b6157] uppercase tracking-[1px] text-center mb-1">
            Sanskrit
          </div>
          {sources.map((w, i) => {
            const isMatched = matched.has(w.san);
            const isDragging = dragging === w.san;
            return (
              <div
                key={`src-${i}`}
                draggable={!isMatched}
                onDragStart={(e) => {
                  e.dataTransfer.setData('text/plain', w.san);
                  setDragging(w.san);
                }}
                onDragEnd={() => setDragging(null)}
                onTouchStart={() => handleTouchStart(w.san)}
                onTouchEnd={handleTouchEnd}
                className={`px-4 py-2.5 rounded-lg text-center select-none text-[1.1rem] font-sanskrit transition-all ${
                  isMatched
                    ? 'opacity-30 cursor-default bg-[#1a1a2e] border border-[#2a2a3e] text-[#e8e0d0]'
                    : isDragging
                      ? 'opacity-40 border-[#d4a843] bg-[#1a1a2e] border text-[#e8e0d0] cursor-grabbing'
                      : 'bg-[#1a1a2e] border border-[#2a2a3e] text-[#e8e0d0] cursor-grab hover:border-[#8a6d2b] hover:bg-[#222240]'
                }`}
              >
                {w.san}
              </div>
            );
          })}
        </div>

        {/* Targets column */}
        <div className="flex flex-col gap-2 w-full sm:min-w-[140px] sm:w-auto">
          <div className="text-[0.7rem] text-[#6b6157] uppercase tracking-[1px] text-center mb-1">
            Meaning
          </div>
          {targets.map((w, i) => {
            const isMatched = matched.has(w.san);
            const isHover = hoverTarget === w.san;
            const isWrong = wrongTarget === w.san;
            return (
              <div
                key={`tgt-${i}`}
                data-drop-answer={w.san}
                onDragOver={(e) => {
                  e.preventDefault();
                  if (!isMatched) setHoverTarget(w.san);
                }}
                onDragLeave={() => setHoverTarget(null)}
                onDrop={(e) => {
                  e.preventDefault();
                  setHoverTarget(null);
                  const word = e.dataTransfer.getData('text/plain');
                  handleDrop(word, w.san);
                }}
                className={`px-4 py-2.5 rounded-lg text-center min-h-[44px] flex items-center justify-center text-[0.9rem] transition-all ${
                  isMatched
                    ? 'border-2 border-[#27ae60] bg-[rgba(39,174,96,0.1)] text-[#27ae60] font-sanskrit text-[1.1rem] cursor-default'
                    : isWrong
                      ? 'border-2 border-[#c0392b] bg-[rgba(192,57,43,0.1)] text-[#6b6157] animate-shake'
                      : isHover
                        ? 'border-2 border-dashed border-[#d4a843] bg-[rgba(212,168,67,0.05)] text-[#6b6157]'
                        : 'border-2 border-dashed border-[#2a2a3e] text-[#6b6157]'
                }`}
              >
                {isMatched ? `${w.san} \u2713` : w.mean}
              </div>
            );
          })}
        </div>
      </div>

      <div className="text-center mt-4">
        <span className="text-[#a89b8c] text-[0.85rem]">
          {matchCount} / {words.length} matched
        </span>
      </div>
    </div>
  );
}

export default SanskritLesson;
