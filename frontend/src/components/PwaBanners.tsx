/** Offline notice and "new version" bar; both sit above the phone tab bar. */
import { ArrowPathIcon, SignalSlashIcon } from "@heroicons/react/24/outline";

import { applyUpdate, usePwa } from "../pwa";

export function PwaBanners() {
  const { online, updateReady } = usePwa();
  if (online && !updateReady) return null;
  return (
    <div className="no-print fixed inset-x-0 bottom-[calc(72px+env(safe-area-inset-bottom))] z-[55] flex flex-col items-center gap-2 px-3 lg:bottom-4" aria-live="polite">
      {!online && (
        <div role="status" className="flex w-full max-w-lg items-start gap-2 border border-band-medium bg-surface p-3 text-sm shadow-none">
          <SignalSlashIcon className="h-5 w-5 shrink-0 text-band-medium" aria-hidden />
          <span>
            <strong>You're offline.</strong> Screens you open need the connection; nothing can be saved until you're back
            online. No risk data is stored on this device.
          </span>
        </div>
      )}
      {updateReady && (
        <div role="status" className="flex w-full max-w-lg items-center gap-3 border border-btn bg-surface p-3 text-sm">
          <ArrowPathIcon className="h-5 w-5 shrink-0 text-accent" aria-hidden />
          <span className="flex-1">A new version of RiskTrack is ready.</span>
          <button type="button" className="btn-primary btn-sm" onClick={applyUpdate}>
            Reload
          </button>
        </div>
      )}
    </div>
  );
}
