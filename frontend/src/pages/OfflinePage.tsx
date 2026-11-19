/** Shown when the app opens (from the home screen) without a connection. */
import { ShieldCheckIcon, SignalSlashIcon } from "@heroicons/react/24/outline";

export function OfflinePage({ retry }: { retry: () => void }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-14 items-center gap-2 border-b border-outline bg-primary-container px-4 pt-[env(safe-area-inset-top)] text-white">
        <span className="flex items-center gap-2 text-lg font-bold tracking-tight">
          <ShieldCheckIcon className="h-6 w-6" aria-hidden /> RiskTrack
        </span>
      </header>
      <main className="flex flex-1 items-center justify-center p-6">
        <div className="max-w-sm text-center">
          <SignalSlashIcon className="mx-auto h-12 w-12 text-muted" aria-hidden />
          <h1 className="mt-4 text-2xl">You're offline</h1>
          <p className="mt-2 text-muted">
            RiskTrack keeps risk data on the server, never on this device, so it needs a connection to show it. Your
            session isn't affected.
          </p>
          <button type="button" className="btn-primary mt-6 w-full" onClick={retry}>
            Try again
          </button>
        </div>
      </main>
    </div>
  );
}
