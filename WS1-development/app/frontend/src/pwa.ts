/**
 * Progressive web app glue: service-worker registration and updates, the install prompt, and
 * online/offline state, exposed through one small store (usePwa).
 */
import { useSyncExternalStore } from "react";

import { setNetworkListener } from "./api/client";

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

interface PwaState {
  online: boolean;
  updateReady: boolean;
  canInstall: boolean;
  installed: boolean;
  /** iPhone/iPad Safari has no install prompt: we show "Share → Add to Home Screen" instead. */
  iosHint: boolean;
}

let state: PwaState = {
  online: typeof navigator === "undefined" ? true : navigator.onLine,
  updateReady: false,
  canInstall: false,
  installed: false,
  iosHint: false,
};
let installEvent: InstallPromptEvent | null = null;
let waiting: ServiceWorker | null = null;
/** Set only when the user clicks "Reload" on the update bar. */
let updateRequested = false;
const listeners = new Set<() => void>();

function set(patch: Partial<PwaState>): void {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
}

function standalone(): boolean {
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

export function initPwa(): void {
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent) && !/crios|fxios/i.test(navigator.userAgent);
  set({ installed: standalone(), iosHint: ios && !standalone() });

  setNetworkListener((reachable) => {
    if (reachable !== state.online) set({ online: reachable });
  });
  window.addEventListener("online", () => set({ online: true }));
  window.addEventListener("offline", () => set({ online: false }));
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault(); // we offer our own button instead of the browser's mini-bar
    installEvent = e as InstallPromptEvent;
    set({ canInstall: true });
  });
  window.addEventListener("appinstalled", () => {
    installEvent = null;
    set({ canInstall: false, installed: true });
  });

  if (!("serviceWorker" in navigator) || !import.meta.env.PROD) return;
  window.addEventListener("load", async () => {
    try {
      const registration = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
      const track = (worker: ServiceWorker | null) => {
        if (!worker) return;
        worker.addEventListener("statechange", () => {
          // A new version is installed while an older one still controls the page.
          if (worker.state === "installed" && navigator.serviceWorker.controller) {
            waiting = worker;
            set({ updateReady: true });
          }
        });
      };
      if (registration.waiting && navigator.serviceWorker.controller) {
        waiting = registration.waiting;
        set({ updateReady: true });
      }
      registration.addEventListener("updatefound", () => track(registration.installing));
      // Long-open tabs still learn about new deploys.
      setInterval(() => registration.update().catch(() => undefined), 60 * 60 * 1000);
    } catch {
      /* the app works without it */
    }
  });
  // The first install also "changes" the controller (null -> worker); never reload for that,
  // or a half-typed form would be wiped. Reload only after the user asked for the update.
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!updateRequested) return;
    updateRequested = false;
    window.location.reload();
  });
}

export async function promptInstall(): Promise<boolean> {
  if (!installEvent) return false;
  await installEvent.prompt();
  const { outcome } = await installEvent.userChoice;
  installEvent = null;
  set({ canInstall: false });
  return outcome === "accepted";
}

export function applyUpdate(): void {
  updateRequested = true;
  if (waiting) waiting.postMessage("SKIP_WAITING");
  else window.location.reload();
}

export function usePwa(): PwaState {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => state,
  );
}
