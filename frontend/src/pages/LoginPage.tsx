import { ShieldCheckIcon } from "@heroicons/react/24/outline";
import { useState } from "react";
import type { FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { NewPasswordFields, PasswordInput, newPasswordValid } from "../components/password";
import { Notice, TextField } from "../components/ui";
import { ThemeToggle, TimezoneSelect } from "../layout/TopBarControls";

type Mode = "signin" | "recover";

export function LoginPage() {
  const { me, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<Mode>("signin");
  const [notice, setNotice] = useState<string | null>(null);
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  if (me) return <Navigate to={from} replace />;

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-14 items-center gap-2 border-b border-outline bg-primary-container px-4 pt-[env(safe-area-inset-top)] text-white">
        <span className="flex shrink-0 items-center gap-2 text-lg font-bold tracking-tight">
          <ShieldCheckIcon className="h-6 w-6" aria-hidden /> RiskTrack
        </span>
        <div className="ml-auto flex min-w-0 items-center gap-1">
          <div className="min-w-0 max-w-[9rem] flex-1 sm:w-56 sm:max-w-none">
            <TimezoneSelect compact />
          </div>
          <ThemeToggle onDark />
        </div>
      </header>
      <main className="flex flex-1 items-start justify-center p-4 pt-8 sm:items-center sm:pt-4">
        <div className="w-full max-w-md">
          {mode === "signin" ? (
            <SignInForm
              notice={notice}
              onForgot={() => {
                setNotice(null);
                setMode("recover");
              }}
              onSignIn={async (u, p) => {
                await signIn(u, p);
                navigate(from, { replace: true });
              }}
            />
          ) : (
            <RecoverForm
              onBack={() => setMode("signin")}
              onDone={() => {
                setNotice("Password reset. Your recovery code is now used up; sign in with the new password and create a new code under My account.");
                setMode("signin");
              }}
            />
          )}
          <p className="mt-4 text-xs text-muted">
            The Alajo is a fictional organisation used for the GRC208 capstone. Demo accounts are listed in the
            project README.
          </p>
        </div>
      </main>
    </div>
  );
}

function SignInForm({
  notice,
  onForgot,
  onSignIn,
}: {
  notice: string | null;
  onForgot: () => void;
  onSignIn: (username: string, password: string) => Promise<void>;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSignIn(username.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="mb-6">
        <div className="label-caps">The Alajo · GRC</div>
        <h1 className="mt-1">Sign in</h1>
        <p className="mt-1 text-muted">Cyber risk register and treatment management. Sign in with your Alajo account.</p>
      </div>
      <form onSubmit={submit} className="card flex flex-col gap-4 p-5 sm:p-6" noValidate>
        {notice && <Notice title="Done">{notice}</Notice>}
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
        <PasswordInput label="Password" autoComplete="current-password" value={password} onChange={setPassword} />
        <button type="submit" className="btn-primary w-full" disabled={busy || !username || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <button type="button" className="btn-ghost self-center" onClick={onForgot}>
          Forgot password?
        </button>
      </form>
    </>
  );
}

/** "Forgot password" without email (Sentinel's design): username + one-time recovery code. */
function RecoverForm({ onBack, onDone }: { onBack: () => void; onDone: () => void }) {
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const valid = !!username.trim() && !!code.trim() && newPasswordValid(password, confirm, username.trim() || " ");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.post("/auth/recover", { username: username.trim(), code, new_password: password });
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="mb-6">
        <div className="label-caps">Account recovery</div>
        <h1 className="mt-1">Reset your password</h1>
        <p className="mt-1 text-muted">
          RiskTrack sends no email, so a reset needs the one-time <strong>recovery code</strong> you created under My
          account. No code? Ask the administrator to set a temporary password for you.
        </p>
      </div>
      <form onSubmit={submit} className="card flex flex-col gap-4 p-5 sm:p-6" noValidate>
        {error && <Notice tone="danger">{error}</Notice>}
        <TextField
          label="Username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <TextField
          label="Recovery code"
          autoComplete="one-time-code"
          autoCapitalize="characters"
          spellCheck={false}
          required
          placeholder="XXXXX-XXXXX-XXXXX-XXXXX"
          className="mono-data uppercase tracking-wider"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          hint="Dashes and capitals are optional. The code works once."
        />
        <NewPasswordFields username={username.trim() || " "} value={password} confirm={confirm} onValue={setPassword} onConfirm={setConfirm} />
        <button type="submit" className="btn-primary w-full" disabled={busy || !valid}>
          {busy ? "Resetting…" : "Reset password"}
        </button>
        <button type="button" className="btn-ghost self-center" onClick={onBack}>
          Back to sign in
        </button>
      </form>
    </>
  );
}
