'use client';

import { useEffect, useState, useCallback } from 'react';

export interface ToastMessage {
  id: string;
  text: string;
  type: 'xp' | 'badge' | 'heart' | 'success' | 'error';
}

let toastId = 0;
let addToastExternal: ((text: string, type: ToastMessage['type']) => void) | null = null;

export function showToast(text: string, type: ToastMessage['type'] = 'xp') {
  if (addToastExternal) {
    addToastExternal(text, type);
  }
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((text: string, type: ToastMessage['type']) => {
    const id = String(++toastId);
    setToasts((prev) => [...prev, { id, text, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 2800);
  }, []);

  useEffect(() => {
    addToastExternal = addToast;
    return () => {
      addToastExternal = null;
    };
  }, [addToast]);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-16 right-6 z-[200] flex flex-col gap-2">
      {toasts.map((toast) => {
        const bg =
          toast.type === 'xp'
            ? 'bg-gradient-to-r from-[#8a6d2b] to-[#d4a843] text-[#0a0a12]'
            : toast.type === 'badge'
              ? 'bg-gradient-to-r from-[#8a6d2b] to-[#f0d078] text-[#0a0a12]'
              : toast.type === 'heart'
                ? 'bg-gradient-to-r from-[#8b0000] to-[#c0392b] text-white'
                : toast.type === 'success'
                  ? 'bg-gradient-to-r from-[#1a6b3a] to-[#27ae60] text-white'
                  : 'bg-gradient-to-r from-[#8b0000] to-[#c0392b] text-white';

        return (
          <div
            key={toast.id}
            className={`${bg} px-5 py-3 rounded-lg text-sm font-medium shadow-lg animate-slideIn`}
          >
            {toast.text}
          </div>
        );
      })}
    </div>
  );
}
