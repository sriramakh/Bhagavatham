'use client';

import React, { memo, useState, useCallback, useMemo } from 'react';
import { QuizQuestion } from '@/types';
import { shuffle } from '@/lib/gameState';

interface QuizBattleProps {
  questions: QuizQuestion[];
  title: string;
  subtitle: string;
  isBoss?: boolean;
  onComplete: (correct: number, total: number) => void;
  onCorrect: () => void;
  onWrong: () => void;
}

const QuizBattle = memo(function QuizBattle({
  questions,
  title,
  subtitle,
  isBoss = false,
  onComplete,
  onCorrect,
  onWrong,
}: QuizBattleProps) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [feedback, setFeedback] = useState<{
    correct: boolean;
    title: string;
    explanation: string;
  } | null>(null);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [selectedFill, setSelectedFill] = useState<string | null>(null);
  const [matchLeft, setMatchLeft] = useState<number | null>(null);
  const [matchedPairs, setMatchedPairs] = useState<Set<number>>(new Set());
  const [wrongMatch, setWrongMatch] = useState<{ left?: number; right?: string } | null>(null);

  const total = questions.length;
  const q = questions[currentIdx] ?? null;
  const pct = total > 0 ? ((currentIdx) / total) * 100 : 0;

  const shuffledMatchRight = useMemo(() => {
    if (q?.type === 'match' && q.pairs) {
      return shuffle(q.pairs.map((p) => p[1]));
    }
    return [];
  }, [q]);

  const handleNext = useCallback(() => {
    const nextIdx = currentIdx + 1;
    setAnswered(false);
    setFeedback(null);
    setSelectedOption(null);
    setSelectedFill(null);
    setMatchLeft(null);
    setMatchedPairs(new Set());
    setWrongMatch(null);

    if (nextIdx >= total) {
      onComplete(correctCount, total);
    } else {
      setCurrentIdx(nextIdx);
    }
  }, [currentIdx, total, correctCount, onComplete]);

  const handleMCQ = useCallback(
    (chosen: number) => {
      if (answered || !q) return;
      setAnswered(true);
      setSelectedOption(chosen);

      const isCorrect = chosen === q.correct;
      if (isCorrect) {
        setCorrectCount((c) => c + 1);
        onCorrect();
        setFeedback({
          correct: true,
          title: 'Correct! +5 XP',
          explanation: q.explanation,
        });
      } else {
        onWrong();
        setFeedback({
          correct: false,
          title: 'Not quite!',
          explanation: q.explanation,
        });
      }
    },
    [answered, q, onCorrect, onWrong]
  );

  const handleFill = useCallback(
    (chosen: string) => {
      if (answered || !q) return;
      setAnswered(true);
      setSelectedFill(chosen);

      const isCorrect = chosen === q.answer;
      if (isCorrect) {
        setCorrectCount((c) => c + 1);
        onCorrect();
        setFeedback({
          correct: true,
          title: 'Correct! +5 XP',
          explanation: q.explanation,
        });
      } else {
        onWrong();
        setFeedback({
          correct: false,
          title: 'Not quite!',
          explanation: q.explanation,
        });
      }
    },
    [answered, q, onCorrect, onWrong]
  );

  const handleMatchLeft = useCallback((idx: number) => {
    setMatchLeft(idx);
    setWrongMatch(null);
  }, []);

  const handleMatchRight = useCallback(
    (rightVal: string) => {
      if (matchLeft === null || !q?.pairs) return;

      const correctRight = q.pairs[matchLeft][1];
      if (rightVal === correctRight) {
        const newMatched = new Set(matchedPairs);
        newMatched.add(matchLeft);
        setMatchedPairs(newMatched);
        setMatchLeft(null);
        onCorrect();

        if (newMatched.size >= q.pairs.length) {
          setCorrectCount((c) => c + 1);
          setAnswered(true);
          setFeedback({
            correct: true,
            title: 'All matched correctly!',
            explanation: q.explanation,
          });
        }
      } else {
        setWrongMatch({ left: matchLeft, right: rightVal });
        onWrong();
        setTimeout(() => {
          setWrongMatch(null);
          setMatchLeft(null);
        }, 600);
      }
    },
    [matchLeft, matchedPairs, q, onCorrect, onWrong]
  );

  if (!q) return null;

  return (
    <div className="max-w-[700px] mx-auto animate-fadeIn">
      {/* Header */}
      <div className="text-center mb-6">
        <h2
          className={`font-heading text-[1.3rem] ${isBoss ? 'text-[#c0392b]' : 'text-[#f0d078]'}`}
        >
          {isBoss && '\u2694\uFE0F '}
          {title}
          {isBoss && ' \u2694\uFE0F'}
        </h2>
        <div className="text-[#a89b8c] text-[0.85rem] mt-1">{subtitle}</div>
      </div>

      {/* Progress */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex-1 h-1.5 bg-[#1a1a2e] rounded-sm overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[#8a6d2b] to-[#d4a843] rounded-sm transition-[width] duration-400"
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="text-[0.8rem] text-[#a89b8c] min-w-[40px] text-right">
          {currentIdx + 1}/{total}
        </div>
      </div>

      {/* Question Card */}
      <div className="bg-[#1a1a2e] border border-[#2a2a3e] rounded-xl p-6">
        {/* MCQ */}
        {q.type === 'mcq' && (
          <>
            <div className="text-[0.7rem] text-[#8a6d2b] font-heading uppercase tracking-[1px] mb-2">
              Multiple Choice
            </div>
            <div className="text-[#e8e0d0] text-base mb-4 leading-[1.7]">{q.question}</div>
            <div className="grid grid-cols-1 gap-2">
              {['A', 'B', 'C', 'D'].map((letter, i) => {
                if (!q.options || !q.options[i]) return null;
                const isSelected = selectedOption === i;
                const isCorrectAnswer = i === q.correct;
                let optClass =
                  'flex items-center gap-3 px-4 py-3 bg-[#12121e] border border-[#2a2a3e] rounded-lg cursor-pointer transition-all';

                if (answered) {
                  optClass += ' pointer-events-none';
                  if (isCorrectAnswer) {
                    optClass +=
                      ' border-[#27ae60] bg-[rgba(39,174,96,0.1)] text-[#27ae60]';
                  } else if (isSelected && !isCorrectAnswer) {
                    optClass +=
                      ' border-[#c0392b] bg-[rgba(192,57,43,0.1)] text-[#c0392b]';
                  }
                } else {
                  optClass +=
                    ' hover:border-[#8a6d2b] hover:bg-[#222240] hover:-translate-y-px';
                }

                return (
                  <button key={i} onClick={() => handleMCQ(i)} className={optClass}>
                    <span className="w-7 h-7 rounded-full border border-[#2a2a3e] flex items-center justify-center text-[0.75rem] font-heading text-[#8a6d2b] flex-shrink-0">
                      {letter}
                    </span>
                    <span className="text-[0.9rem]">{q.options[i]}</span>
                  </button>
                );
              })}
            </div>
          </>
        )}

        {/* Fill in the Blank */}
        {q.type === 'fill' && (
          <>
            <div className="text-[0.7rem] text-[#8a6d2b] font-heading uppercase tracking-[1px] mb-2">
              Fill in the Blank
            </div>
            <div
              className="text-[#e8e0d0] text-base mb-4 leading-[1.7]"
              dangerouslySetInnerHTML={{
                __html: q.question.replace(
                  '___',
                  `<span class="px-3 py-0.5 mx-1 border-b-2 border-dashed border-[#d4a843] text-[#d4a843] font-sanskrit text-lg">${
                    answered && q.answer ? q.answer : '___'
                  }</span>`
                ),
              }}
            />
            <div className="flex flex-wrap gap-2 justify-center">
              {q.options?.map((opt, i) => {
                const isSelected = selectedFill === opt;
                const isCorrectAnswer = opt === q.answer;
                let cls =
                  'px-4 py-2.5 rounded-lg border font-sanskrit text-[1.1rem] transition-all cursor-pointer';

                if (answered) {
                  cls += ' pointer-events-none';
                  if (isCorrectAnswer) {
                    cls +=
                      ' border-[#27ae60] bg-[rgba(39,174,96,0.1)] text-[#27ae60]';
                  } else if (isSelected) {
                    cls +=
                      ' border-[#c0392b] bg-[rgba(192,57,43,0.1)] text-[#c0392b]';
                  } else {
                    cls += ' border-[#2a2a3e] text-[#6b6157]';
                  }
                } else {
                  cls +=
                    ' border-[#2a2a3e] text-[#e8e0d0] bg-[#12121e] hover:border-[#8a6d2b] hover:bg-[#222240]';
                }

                return (
                  <button key={i} onClick={() => handleFill(opt)} className={cls}>
                    {opt}
                  </button>
                );
              })}
            </div>
          </>
        )}

        {/* Match */}
        {q.type === 'match' && q.pairs && (
          <>
            <div className="text-[0.7rem] text-[#8a6d2b] font-heading uppercase tracking-[1px] mb-2">
              Matching
            </div>
            <div className="text-[#e8e0d0] text-base mb-4 leading-[1.7]">{q.question}</div>
            <div className="flex gap-5 justify-center flex-wrap mt-3">
              <div className="flex flex-col gap-1.5">
                {q.pairs.map((p, i) => {
                  const isMatched = matchedPairs.has(i);
                  const isSelectedLeft = matchLeft === i;
                  const isWrongLeft = wrongMatch?.left === i;
                  return (
                    <button
                      key={`ml-${i}`}
                      onClick={() => !isMatched && handleMatchLeft(i)}
                      disabled={isMatched}
                      className={`px-4 py-2.5 rounded-lg border min-w-[120px] text-center font-sanskrit text-[1.1rem] transition-all cursor-pointer ${
                        isMatched
                          ? 'border-[#27ae60] bg-[rgba(39,174,96,0.1)] text-[#27ae60] pointer-events-none'
                          : isWrongLeft
                            ? 'border-[#c0392b] bg-[rgba(192,57,43,0.1)] text-[#c0392b]'
                            : isSelectedLeft
                              ? 'border-[#d4a843] bg-[rgba(212,168,67,0.1)] text-[#f0d078]'
                              : 'border-[#2a2a3e] bg-[#12121e] text-[#e8e0d0] hover:border-[#8a6d2b]'
                      }`}
                    >
                      {p[0]}
                    </button>
                  );
                })}
              </div>
              <div className="flex flex-col gap-1.5">
                {shuffledMatchRight.map((r, i) => {
                  const pairIdx = q.pairs!.findIndex((p) => p[1] === r);
                  const isMatched = matchedPairs.has(pairIdx);
                  const isWrongRight = wrongMatch?.right === r;
                  return (
                    <button
                      key={`mr-${i}`}
                      onClick={() => !isMatched && handleMatchRight(r)}
                      disabled={isMatched}
                      className={`px-4 py-2.5 rounded-lg border min-w-[120px] text-center text-[0.9rem] transition-all cursor-pointer ${
                        isMatched
                          ? 'border-[#27ae60] bg-[rgba(39,174,96,0.1)] text-[#27ae60] pointer-events-none'
                          : isWrongRight
                            ? 'border-[#c0392b] bg-[rgba(192,57,43,0.1)] text-[#c0392b]'
                            : 'border-[#2a2a3e] bg-[#12121e] text-[#e8e0d0] hover:border-[#8a6d2b]'
                      }`}
                    >
                      {r}
                    </button>
                  );
                })}
              </div>
            </div>
          </>
        )}

        {/* Feedback */}
        {feedback && (
          <div
            className={`mt-5 p-4 rounded-lg flex items-start gap-3 animate-slideIn ${
              feedback.correct
                ? 'bg-[rgba(39,174,96,0.1)] border border-[rgba(39,174,96,0.3)]'
                : 'bg-[rgba(192,57,43,0.1)] border border-[rgba(192,57,43,0.3)]'
            }`}
          >
            <span className="text-xl">{feedback.correct ? '\u2705' : '\u274C'}</span>
            <div>
              <strong className={feedback.correct ? 'text-[#27ae60]' : 'text-[#c0392b]'}>
                {feedback.title}
              </strong>
              {feedback.explanation && (
                <p className="text-[#a89b8c] text-[0.85rem] mt-1">{feedback.explanation}</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Next button */}
      {answered && (
        <div className="flex justify-end mt-5">
          <button
            onClick={handleNext}
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-br from-[#8a6d2b] to-[#d4a843] text-[#0a0a12] rounded-lg font-heading text-[0.9rem] tracking-[1px] shadow-[0_4px_15px_rgba(212,168,67,0.3)] hover:-translate-y-0.5 hover:shadow-[0_6px_25px_rgba(212,168,67,0.4)] active:translate-y-0 transition-all cursor-pointer"
          >
            {currentIdx + 1 >= total ? 'Finish' : 'Next Question'} {'\u2192'}
          </button>
        </div>
      )}
    </div>
  );
});

export default QuizBattle;
