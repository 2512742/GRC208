import { CheckCircleIcon, ExclamationCircleIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

type Tone = "success" | "error";
interface ToastItem {
  id: number;
  tone: Tone;
  message: string;
}

interface ToastApi {
  success: (message: string) => void;
  error: (messageOrError: unknown) => void;
}

const ToastContext = createContext<ToastApi | null>(null);
let nextId = 1;

/** Bottom-right toasts (success teal, error red) instead of alert(). */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: number) => setItems((all) => all.filter((t) => t.id !== id)), []);
  const push = useCallback(
    (tone: Tone, message: string) => {
      const id = nextId++;
      setItems((all) => [...all.slice(-3), { id, tone, message }]);
      setTimeout(() => dismiss(id), tone === "error" ? 8000 : 4000);
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({
      success: (m) => push("success", m),
      error: (e) =>
        push("error", e instanceof Error ? e.message : typeof e === "string" ? e : "Something went wrong."),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        className="no-print pointer-events-none fixed bottom-[calc(80px+env(safe-area-inset-bottom))] right-4 z-[60] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2 lg:bottom-4"
      >
        {items.map((t) => (
          <div
            key={t.id}
            role={t.tone === "error" ? "alert" : "status"}
            className={`toast-in pointer-events-auto flex items-start gap-2 border p-3 text-sm ${
              t.tone === "success"
                ? "border-accent bg-accent text-on-accent"
                : "border-danger bg-danger text-white dark:text-bg"
            }`}
          >
            {t.tone === "success" ? (
              <CheckCircleIcon className="h-5 w-5 shrink-0" aria-hidden />
            ) : (
              <ExclamationCircleIcon className="h-5 w-5 shrink-0" aria-hidden />
            )}
            <span className="flex-1">{t.message}</span>
            <button type="button" aria-label="Dismiss" onClick={() => dismiss(t.id)}>
              <XMarkIcon className="h-4 w-4" aria-hidden />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
