import { ShieldCheckIcon } from "@heroicons/react/24/outline";
import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { Notice, TextField } from "../components/ui";
import { ThemeToggle, TimezoneSelect } from "../layout/TopBarControls";

export function LoginPage() {
  const { me, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  if (me) return <Navigate to={from} replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-14 items-center gap-2 border-b border-outline bg-primary-container px-4 pt-[env(safe-area-inset-top)] text-white">
        <span className="flex items-center gap-2 text-lg font-bold tracking-tight">
          <ShieldCheckIcon className="h-6 w-6" aria-hidden /> RiskTrack
        </span>
        <div className="ml-auto flex items-center gap-1">
          <div className="w-36 sm:w-56">
            <TimezoneSelect compact />
          </div>
          <ThemeToggle onDark />
        </div>
      </header>
      <main className="flex flex-1 items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="mb-6">
            <div className="label-caps">The Alajo · GRC</div>
            <h1 className="mt-1">Sign in</h1>
            <p className="mt-1 text-muted">
              Cyber risk register and treatment management. Sign in with your Alajo account.
            </p>
          </div>
          <form onSubmit={submit} className="card flex flex-col gap-4 p-6" noValidate>
            {error && <Notice tone="danger">{error}</Notice>}
            <TextField
              label="Username"
              name="username"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <TextField
              label="Password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button type="submit" className="btn-primary w-full" disabled={busy || !username || !password}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="mt-4 text-xs text-muted">
            The Alajo is a fictional organisation used for the GRC208 capstone. Demo accounts are
            listed in the project README.
          </p>
        </div>
      </main>
    </div>
  );
}
