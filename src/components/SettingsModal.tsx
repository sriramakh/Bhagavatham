'use client';

import React, { memo, useState, useCallback } from 'react';

interface SettingsModalProps {
  isOpen: boolean;
  soundEnabled: boolean;
  onClose: () => void;
  onResetProgress: () => void;
  onToggleSound: (enabled: boolean) => void;
}

const SettingsModal = memo(function SettingsModal({
  isOpen,
  soundEnabled,
  onClose,
  onResetProgress,
  onToggleSound,
}: SettingsModalProps) {
  const [confirmReset, setConfirmReset] = useState(false);

  const handleReset = useCallback(() => {
    if (confirmReset) {
      onResetProgress();
      setConfirmReset(false);
    } else {
      setConfirmReset(true);
      setTimeout(() => setConfirmReset(false), 3000);
    }
  }, [confirmReset, onResetProgress]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center z-[200]"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-[#1a1a2e] border border-[#8a6d2b] rounded-xl p-8 max-w-[420px] w-[90%] text-center animate-slideIn">
        <h3 className="font-heading text-[#d4a843] text-[1.1rem] mb-6">Settings</h3>

        {/* Sound Toggle */}
        <div className="flex items-center justify-between px-2 py-3 border-b border-[#2a2a3e] mb-4">
          <span className="text-[#e8e0d0] text-[0.9rem]">
            {'\uD83D\uDD0A'} Sound Effects
          </span>
          <button
            onClick={() => onToggleSound(!soundEnabled)}
            className={`w-12 h-6 rounded-full relative transition-colors cursor-pointer border-none ${
              soundEnabled ? 'bg-[#27ae60]' : 'bg-[#2a2a3e]'
            }`}
          >
            <div
              className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                soundEnabled ? 'translate-x-[26px]' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>

        {/* API Key Info */}
        <div className="text-left px-2 py-3 border-b border-[#2a2a3e] mb-4">
          <div className="text-[#a89b8c] text-[0.8rem] mb-1">API Keys</div>
          <p className="text-[#6b6157] text-[0.75rem] leading-[1.6]">
            API keys for OpenAI (image generation) and chat are managed server-side via
            environment variables. No client-side key configuration is needed.
          </p>
        </div>

        {/* Reset Progress */}
        <div className="px-2 py-3 mb-6">
          <button
            onClick={handleReset}
            className={`px-5 py-2.5 rounded-lg font-heading text-[0.8rem] tracking-[1px] border-none cursor-pointer transition-all ${
              confirmReset
                ? 'bg-gradient-to-br from-[#8b0000] to-[#c0392b] text-white'
                : 'bg-transparent border border-[#c0392b] text-[#c0392b] hover:bg-[rgba(192,57,43,0.1)]'
            }`}
            style={confirmReset ? {} : { border: '1px solid #c0392b' }}
          >
            {confirmReset ? 'Confirm Reset — This Cannot Be Undone' : 'Reset All Progress'}
          </button>
        </div>

        {/* Close */}
        <div className="flex justify-center">
          <button
            onClick={onClose}
            className="px-8 py-2.5 border border-[#8a6d2b] text-[#f0d078] rounded-lg font-heading text-[0.85rem] tracking-[1px] bg-transparent hover:bg-[rgba(212,168,67,0.1)] hover:border-[#d4a843] transition-all cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
});

export default SettingsModal;
