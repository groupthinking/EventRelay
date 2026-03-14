'use client';

import { useEffect, useState, useCallback, createContext, useContext } from 'react';
import { clsx } from 'clsx';

// ── Types ──

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  addToast: (message: string, type?: ToastType) => void;
}

// ── Context ──

const ToastContext = createContext<ToastContextValue>({ addToast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

// ── Individual Toast ──

const TOAST_STYLES: Record<ToastType, string> = {
  success: 'bg-green-500/15 border-green-500/30 text-green-300',
  error:   'bg-red-500/15 border-red-500/30 text-red-300',
  info:    'bg-blue-500/15 border-blue-500/30 text-blue-300',
  warning: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
};

const TOAST_ICONS: Record<ToastType, string> = {
  success: '✓',
  error:   '✕',
  info:    'ℹ',
  warning: '⚠',
};

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Trigger enter animation
    requestAnimationFrame(() => setVisible(true));
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(() => onDismiss(toast.id), 300);
    }, 3500);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  return (
    <div
      className={clsx(
        'flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-md text-sm font-medium',
        'shadow-lg transition-all duration-300',
        TOAST_STYLES[toast.type],
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
      )}
    >
      <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold shrink-0 bg-current/20">
        {TOAST_ICONS[toast.type]}
      </span>
      <span>{toast.message}</span>
      <button
        onClick={() => { setVisible(false); setTimeout(() => onDismiss(toast.id), 300); }}
        className="ml-auto text-current/60 hover:text-current transition-colors"
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}

// ── Provider ──

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((prev) => [...prev.slice(-4), { id, message, type }]);
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      {/* Toast container */}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 w-80 pointer-events-none"
      >
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem toast={toast} onDismiss={dismiss} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
