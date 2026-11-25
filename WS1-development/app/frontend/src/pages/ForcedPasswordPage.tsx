/** After an administrator sets a password, nothing else opens until the user replaces it. */
import { ShieldCheckIcon } from "@heroicons/react/24/outline";

import { useAuth, useMe } from "../auth/AuthContext";
import { Notice } from "../components/ui";
import { ChangePasswordForm } from "./AccountPage";

export function ForcedPasswordPage() {
  const me = useMe();
  const { signOut } = useAuth();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-14 items-center gap-2 border-b border-line bg-bar px-4 pt-[env(safe-area-inset-top)] text-on-bar">
        <span className="flex items-center gap-2 text-lg font-bold tracking-tight">
          <ShieldCheckIcon className="h-6 w-6" aria-hidden /> RiskTrack
        </span>
        <button type="button" className="ml-auto p-2 text-sm text-on-bar/80 hover:text-on-bar" onClick={() => signOut()}>
          Sign out
        </button>
      </header>
      <main className="flex flex-1 items-start justify-center p-4 pt-8 sm:items-center">
        <div className="w-full max-w-md">
          <div className="label-caps">Welcome, {me.full_name.split(" ")[0]}</div>
          <h1 className="mt-1">Choose your own password</h1>
          <div className="mt-4">
            <Notice tone="warning">
              Your password was set by the administrator, so they know it. Replace it with one only you know before
              continuing.
            </Notice>
          </div>
          <div className="card mt-4 p-5 sm:p-6">
            <ChangePasswordForm forced />
          </div>
          <p className="mt-4 text-xs text-muted">
            Next, create a recovery code under My account, so you can reset a forgotten password yourself.
          </p>
        </div>
      </main>
    </div>
  );
}
