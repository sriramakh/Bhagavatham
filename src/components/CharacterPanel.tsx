'use client';

import React, { memo, useMemo } from 'react';
import { GameState, SKANDHA_NAMES } from '@/types';
import { getLevelProgress, toRoman } from '@/lib/gameState';

const BADGES = [
  { id: 'first-verse', name: 'First Verse', icon: '\uD83D\uDCDC' },
  { id: 'sanskrit-novice', name: 'Sanskrit Novice', icon: '\uD83D\uDD24' },
  { id: 'madhva-disciple', name: "Madhva's Disciple", icon: '\uD83D\uDE4F' },
  { id: 'quiz-warrior', name: 'Quiz Warrior', icon: '\u2694\uFE0F' },
  { id: 'boss-slayer', name: 'Boss Slayer', icon: '\uD83D\uDC09' },
  { id: 'chapter-complete', name: 'Chapter Master', icon: '\u2705' },
  { id: 'perfect-quiz', name: 'Perfect Score', icon: '\uD83D\uDC8E' },
  { id: 'streak-3', name: '3-Day Streak', icon: '\uD83D\uDD25' },
];

interface CharacterPanelProps {
  state: GameState;
  onSelectSkandha: (num: number) => void;
}

const CharacterPanel = memo(function CharacterPanel({
  state,
  onSelectSkandha,
}: CharacterPanelProps) {
  const levelInfo = useMemo(() => getLevelProgress(state.xp), [state.xp]);
  const accuracy = useMemo(
    () =>
      state.totalAnswered > 0
        ? Math.round((state.totalCorrect / state.totalAnswered) * 100)
        : 0,
    [state.totalCorrect, state.totalAnswered]
  );

  return (
    <aside className="bg-[#12121e] border-r border-[#2a2a3e] p-5 px-4 overflow-y-auto h-[calc(100vh-56px)] sticky top-14">
      <div className="text-center">
        {/* Avatar */}
        <div className="w-[100px] h-[100px] mx-auto mb-3 rounded-full border-[3px] border-[#d4a843] bg-[#1a1a2e] flex items-center justify-center text-[2.8rem] shadow-[0_0_20px_rgba(212,168,67,0.3)] relative overflow-hidden">
          <div className="absolute inset-[-3px] rounded-full border-[3px] border-transparent border-t-[#e8862a] animate-spin" />
          {'\uD83D\uDE4F'}
        </div>

        <div className="font-heading text-[#f0d078] text-base mb-0.5">Seeker</div>
        <div className="text-[#a89b8c] text-[0.75rem] tracking-[1px] uppercase mb-4">
          {levelInfo.levelName}
        </div>

        {/* XP Bar */}
        <div className="mb-5">
          <div className="flex justify-between text-[0.75rem] text-[#a89b8c] mb-1">
            <span>XP</span>
            <span>
              {levelInfo.isMax ? 'MAX' : `${levelInfo.xpInLevel} / ${levelInfo.xpForNext}`}
            </span>
          </div>
          <div className="w-full h-2.5 bg-[#0a0a12] rounded-[5px] overflow-hidden border border-[#2a2a3e]">
            <div
              className="h-full bg-gradient-to-r from-[#e8862a] to-[#f0d078] rounded-[5px] transition-[width] duration-800 ease-[cubic-bezier(0.4,0,0.2,1)] relative"
              style={{ width: `${levelInfo.pct}%` }}
            >
              <div className="absolute top-0 left-0 right-0 h-1/2 bg-white/20 rounded-t-[5px]" />
            </div>
          </div>
          <div className="font-heading text-[#d4a843] text-[0.85rem] mt-1.5">
            Level {levelInfo.level + 1} — {levelInfo.levelName}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-2 my-4">
          <StatBox value={state.versesStudied} label="Verses" />
          <StatBox value={state.learnedWords.length} label="Words" />
          <StatBox value={state.quizzesCompleted} label="Quizzes" />
          <StatBox value={`${accuracy}%`} label="Accuracy" />
        </div>

        {/* Badges */}
        <div className="mt-5 text-left">
          <h3 className="font-heading text-[0.75rem] text-[#d4a843] tracking-[1px] uppercase mb-2.5">
            Badges Earned
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {BADGES.map((badge) => {
              const earned = state.badges.includes(badge.id);
              return (
                <span
                  key={badge.id}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[0.7rem] border transition-all ${
                    earned
                      ? 'border-[rgba(212,168,67,0.3)] bg-[rgba(212,168,67,0.08)] text-[#f0d078] hover:bg-[rgba(212,168,67,0.15)] hover:-translate-y-px cursor-default'
                      : 'border-[rgba(212,168,67,0.3)] bg-transparent text-[#6b6157] opacity-30 grayscale'
                  }`}
                  title={earned ? badge.name : `${badge.name} (locked)`}
                >
                  {badge.icon} {badge.name}
                </span>
              );
            })}
          </div>
        </div>

        {/* Skandha Map */}
        <div className="mt-6 text-left">
          <h3 className="font-heading text-[0.75rem] text-[#d4a843] tracking-[1px] uppercase mb-2.5">
            Realms (Skandhas)
          </h3>
          <div className="flex flex-col gap-1">
            {SKANDHA_NAMES.map((name, i) => {
              const num = i + 1;
              const isActive = num === state.currentSkandha;
              const isLocked = false;
              return (
                <button
                  key={num}
                  onClick={() => !isLocked && onSelectSkandha(num)}
                  disabled={isLocked}
                  className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-[0.75rem] border transition-all text-left w-full ${
                    isActive
                      ? 'bg-[#1a1a2e] border-[#8a6d2b] text-[#f0d078]'
                      : isLocked
                        ? 'border-transparent opacity-35 cursor-not-allowed'
                        : 'border-transparent hover:bg-[#222240] hover:border-[#2a2a3e] cursor-pointer'
                  }`}
                >
                  <span className="font-heading text-[#8a6d2b] w-5 text-center">
                    {toRoman(num)}
                  </span>
                  <span
                    className={`flex-1 ${isActive ? 'text-[#f0d078]' : 'text-[#a89b8c]'}`}
                  >
                    {name}
                  </span>
                  <span className="text-[0.65rem]">
                    {isLocked ? '\uD83D\uDD12' : isActive ? '\u25B6' : ''}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </aside>
  );
});

function StatBox({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="bg-[#1a1a2e] border border-[#2a2a3e] rounded-lg p-2 text-center">
      <div className="font-heading text-[#f0d078] text-[1.1rem]">{value}</div>
      <div className="text-[0.65rem] text-[#6b6157] uppercase tracking-[0.5px]">{label}</div>
    </div>
  );
}

export default CharacterPanel;
