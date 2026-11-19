/** "Install app" (Android/desktop Chrome and Edge) or Add-to-Home-Screen steps (iPhone). */
import { ArrowDownTrayIcon, ArrowUpOnSquareIcon } from "@heroicons/react/24/outline";

import { promptInstall, usePwa } from "../pwa";
import { useToast } from "./Toast";

export function InstallApp({ compact }: { compact?: boolean }) {
  const { canInstall, installed, iosHint } = usePwa();
  const toast = useToast();
  if (installed) return compact ? null : <p className="text-sm text-muted">RiskTrack is installed on this device.</p>;
  if (canInstall)
    return (
      <button
        type="button"
        className="btn-secondary w-full"
        onClick={async () => {
          if (await promptInstall()) toast.success("RiskTrack installed. Open it from your home screen or apps.");
        }}
      >
        <ArrowDownTrayIcon className="h-5 w-5" aria-hidden /> Install the app
      </button>
    );
  if (iosHint)
    return (
      <p className="flex items-start gap-2 text-sm text-muted">
        <ArrowUpOnSquareIcon className="h-5 w-5 shrink-0" aria-hidden />
        <span>
          To install on iPhone or iPad: tap <strong>Share</strong>, then <strong>Add to Home Screen</strong>.
        </span>
      </p>
    );
  return compact ? null : (
    <p className="text-sm text-muted">
      Your browser can install RiskTrack from its menu (Install app, or Add to Home Screen) when the site is served over
      HTTPS.
    </p>
  );
}
