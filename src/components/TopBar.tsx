'use client';

import React, { memo } from 'react';

interface TopBarProps {
  skandha: string;
  chapter: string;
  progress: number;
  streak: number;
  hearts: number;
  maxHearts: number;
  onSettingsClick: () => void;
}

const TopBar = memo(function TopBar({
  skandha,
  chapter,
  progress,
  streak,
  hearts,
  maxHearts,
  onSettingsClick,
}: TopBarProps) {
  return (
    <div className="fixed top-0 left-0 right-0 h-14 bg-gradient-to-b from-[#12121e] to-[#12121ef2] border-b border-[rgba(212,168,67,0.3)] flex items-center justify-between px-3 md:px-6 z-[100] backdrop-blur-[10px] gap-2">
      {/* Logo */}
      <div className="font-heading text-[#d4a843] tracking-[1px] md:tracking-[2px] flex items-center gap-1.5 md:gap-2.5 flex-shrink-0 text-[0.85rem] md:text-[1.1rem]">
        <span className="font-sanskrit text-[1.3rem] text-[#e8862a] leading-none">{'\u0950'}</span>
        <span className="hidden sm:inline whitespace-nowrap">QUEST OF THE SKANDHAS</span>
        <span className="sm:hidden whitespace-nowrap text-[0.75rem]">SKANDHAS</span>
      </div>

      {/* Center nav — desktop only */}
      <div className="hidden lg:flex items-center gap-5 flex-1 justify-center">
        <span className="font-heading text-[#f0d078] text-[0.85rem] tracking-[1px]">
          {skandha}
        </span>
        <span className="text-[#a89b8c] text-[0.8rem] truncate max-w-[160px]">{chapter}</span>
        <div className="w-[160px] h-1.5 bg-[#1a1a2e] rounded-sm overflow-hidden flex-shrink-0">
          <div
            className="h-full bg-gradient-to-r from-[#8a6d2b] to-[#d4a843] rounded-sm transition-[width] duration-600"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Right nav */}
      <div className="flex items-center gap-2 md:gap-4 flex-shrink-0">
        {/* Streak */}
        <div className="flex items-center gap-1 bg-[#1a1a2e] px-2 md:px-3 py-1 rounded-full border border-[#2a2a3e] text-[0.75rem] md:text-[0.8rem]">
          <span className="text-[#e8862a]">{'\uD83D\uDD25'}</span>
          <span className="text-[#e8e0d0]">{streak}</span>
          <span className="hidden md:inline text-[#a89b8c]">day streak</span>
        </div>

        {/* Hearts */}
        <div className="flex gap-0.5">
          {Array.from({ length: maxHearts }).map((_, i) => (
            <span
              key={i}
              className={`text-[0.95rem] md:text-[1.1rem] transition-all duration-300 ${
                i >= hearts ? 'opacity-20 scale-[0.8]' : ''
              }`}
            >
              {'\u2764\uFE0F'}
            </span>
          ))}
        </div>

        {/* Settings */}
        <button
          onClick={onSettingsClick}
          className="bg-transparent border-none text-[#a89b8c] cursor-pointer text-[1.1rem] p-2 min-w-[40px] min-h-[40px] flex items-center justify-center hover:text-[#f0d078] transition-colors"
          title="Settings"
        >
          {'\u2699'}
        </button>
      </div>
    </div>
  );
});

export default TopBar;
