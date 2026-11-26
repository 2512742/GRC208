/**
 * My account: profile, preferences, password, recovery code, sessions and recent activity.
 * Security features follow the Sentinel project (no email: one-time recovery code, forced
 * change after an admin reset, other sessions ended on a password change).
 */
import {
  ArrowRightStartOnRectangleIcon,
  ClipboardDocumentIcon,
  ComputerDesktopIcon,
  DevicePhoneMobileIcon,
  KeyIcon,
  LifebuoyIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useSearchParams } from "react-router-dom";

import { api } from "../api/client";
import type { ActivityOut, Me, RecoveryCodeOut, SecurityOverview, SessionOut, SignedOut } from "../api/types";
import { useAuth, useMe } from "../auth/AuthContext";
import { ConfirmDialog, Modal } from "../components/Modal";
import { NewPasswordFields, PasswordInput, newPasswordValid } from "../components/password";
import { InstallApp } from "../components/InstallApp";
import { useToast } from "../components/Toast";
import { Card, DateTime, EmptyState, ErrorState, KeyValue, Loading, Notice, PageHeader, Tabs, TextField, cx } from "../components/ui";
import { ROLE_LABELS, initials } from "../lib/format";
import { TimezoneSelect } from "../layout/TopBarControls";
import { useTheme } from "../theme/useTheme";

type Tab = "profile" | "security" | "sessions" | "activity";

export function useSecurity() {
  return useQuery({ queryKey: ["me", "security"], queryFn: () => api.get<SecurityOverview>("/me/security") });
}

export default function AccountPage() {
  const me = useMe();
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) ?? "profile";
  const security = useSecurity();

  return (
    <>
      <PageHeader eyebrow="My account" title="Profile and security" />
      <div className="mb-5 flex items-center gap-4">
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-accent text-lg font-bold text-on-accent">
          {initials(me.full_name)}
        </span>
        <div className="min-w-0">
          <div className="truncate text-lg font-semibold">{me.full_name}</div>
          <div className="truncate text-sm text-muted">
            <span className="mono-data">{me.username}</span> · {ROLE_LABELS[me.role]}
            {me.job_title ? ` · ${me.job_title}` : ""}
          </div>
        </div>
      </div>

      {security.data && <SecuritySummary s={security.data} onGo={(t) => setParams({ tab: t }, { replace: true })} />}

      <div className="mt-5">
        <Tabs<Tab>
          active={tab}
          onChange={(t) => setParams(t === "profile" ? {} : { tab: t }, { replace: true })}
          tabs={[
            { key: "profile", label: "Profile" },
            { key: "security", label: "Password and recovery" },
            { key: "sessions", label: "Sessions" },
            { key: "activity", label: "Activity" },
          ]}
        />
      </div>
      <div className="mt-4">
        {tab === "profile" && <ProfileTab />}
        {tab === "security" && <SecurityTab security={security.data} />}
        {tab === "sessions" && <SessionsTab />}
        {tab === "activity" && <ActivityTab />}
      </div>
    </>
  );
}

function SecuritySummary({ s, onGo }: { s: SecurityOverview; onGo: (t: Tab) => void }) {
  const items: { label: string; value: React.ReactNode; tone?: "ok" | "warn"; tab: Tab }[] = [
    {
      label: "Password",
      value: s.password_changed_at ? <>Changed <DateTime iso={s.password_changed_at} /></> : "Never changed",
      tone: s.password_changed_at ? "ok" : "warn",
      tab: "security",
    },
    {
      label: "Recovery code",
      value: s.has_recovery_code ? "Set" : "Not set",
      tone: s.has_recovery_code ? "ok" : "warn",
      tab: "security",
    },
    { label: "Signed-in sessions", value: String(s.active_sessions), tab: "sessions" },
    {
      label: `Failed sign-ins (${s.lockout_minutes} min)`,
      value: String(s.recent_failed_sign_ins),
      tone: s.recent_failed_sign_ins ? "warn" : "ok",
      tab: "activity",
    },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {items.map((i) => (
        <button key={i.label} type="button" onClick={() => onGo(i.tab)} className="card min-w-0 p-3 text-left hover:bg-hover">
          <div className="label-caps text-[11px] leading-tight">{i.label}</div>
          <div className={cx("mt-1 break-words text-sm font-semibold", i.tone === "warn" ? "text-band-high" : i.tone === "ok" ? "text-band-low" : "")}>
            {i.value}
          </div>
        </button>
      ))}
    </div>
  );
}

// ── Profile and preferences ───────────────────────────────────────────────────────────────

function ProfileTab() {
  const me = useMe();
  const toast = useToast();
  const qc = useQueryClient();
  const { theme, set } = useTheme();
  const [form, setForm] = useState({ full_name: me.full_name, job_title: me.job_title ?? "", department: me.department ?? "", email: me.email ?? "" });
  useEffect(
    () => setForm({ full_name: me.full_name, job_title: me.job_title ?? "", department: me.department ?? "", email: me.email ?? "" }),
    [me.full_name, me.job_title, me.department, me.email],
  );
  const save = useMutation({
    mutationFn: () => api.patch<Me>("/me/profile", form),
    onSuccess: (updated) => {
      qc.setQueryData(["me"], updated);
      qc.invalidateQueries({ queryKey: ["users"] });
      toast.success("Profile saved.");
    },
  });
  const dirty =
    form.full_name !== me.full_name ||
    form.job_title !== (me.job_title ?? "") ||
    form.department !== (me.department ?? "") ||
    form.email !== (me.email ?? "");

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
      <Card title="Profile details" className="xl:col-span-2">
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          {save.error && <Notice tone="danger">{save.error.message}</Notice>}
          <TextField label="Full name" required minLength={2} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextField label="Job title" value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} />
            <TextField label="Department" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
          </div>
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            hint="For contact only. RiskTrack never sends email, so it can't be used to reset a password."
          />
          <div>
            <button type="submit" className="btn-primary w-full sm:w-auto" disabled={!dirty || save.isPending}>
              {save.isPending ? "Saving…" : "Save profile"}
            </button>
          </div>
        </form>
      </Card>
      <div className="flex flex-col gap-6">
        <Card title="Account">
          <KeyValue
            items={[
              ["Username", <span className="mono-data">{me.username}</span>],
              ["Role", ROLE_LABELS[me.role]],
              ["Member since", <DateTime iso={me.created_at} />],
              ["Last sign-in", <DateTime iso={me.last_login_at} />],
            ]}
          />
          <p className="mt-3 text-xs text-muted">Username and role are managed by the administrator.</p>
        </Card>
        <Card title="Preferences">
          <div className="flex flex-col gap-4">
            <div>
              <div className="label-caps mb-1">Show times in</div>
              <TimezoneSelect compact />
              <p className="mt-1 text-xs text-muted">Saved to your account. Deadlines are always evaluated in WAT (Lagos).</p>
            </div>
            <fieldset>
              <legend className="label-caps mb-1">Theme</legend>
              <div className="grid grid-cols-2 gap-2">
                {(["light", "dark"] as const).map((t) => (
                  <button
                    key={t}
                    type="button"
                    aria-pressed={theme === t}
                    onClick={() => set(t)}
                    className={theme === t ? "btn-primary" : "btn-secondary"}
                  >
                    {t === "light" ? "Light" : "Dark"}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-xs text-muted">Remembered on this device.</p>
            </fieldset>
            <div>
              <div className="label-caps mb-1">App</div>
              <InstallApp />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── Password and recovery code ────────────────────────────────────────────────────────────

export function ChangePasswordForm({ forced, onDone }: { forced?: boolean; onDone?: () => void }) {
  const me = useMe();
  const toast = useToast();
  const qc = useQueryClient();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const change = useMutation({
    mutationFn: () => api.post<Me>("/me/password", { current_password: current, new_password: next }),
    onSuccess: (updated) => {
      qc.setQueryData(["me"], updated);
      qc.invalidateQueries({ queryKey: ["me", "security"] });
      qc.invalidateQueries({ queryKey: ["me", "sessions"] });
      setCurrent("");
      setNext("");
      setConfirm("");
      toast.success("Password changed. Your other sessions were signed out.");
      onDone?.();
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    change.mutate();
  };
  return (
    <form className="flex flex-col gap-4" onSubmit={submit}>
      {change.error && <Notice tone="danger">{change.error.message}</Notice>}
      <PasswordInput
        label={forced ? "Temporary password" : "Current password"}
        autoComplete="current-password"
        value={current}
        onChange={setCurrent}
      />
      <NewPasswordFields username={me.username} current={current} value={next} confirm={confirm} onValue={setNext} onConfirm={setConfirm} />
      <div>
        <button
          type="submit"
          className="btn-primary w-full sm:w-auto"
          disabled={!current || !newPasswordValid(next, confirm, me.username, current) || change.isPending}
        >
          <KeyIcon className="h-4 w-4" aria-hidden /> {change.isPending ? "Changing…" : "Change password"}
        </button>
      </div>
      {!forced && (
        <p className="text-xs text-muted">
          Changing your password signs out every other session (other browsers and phones). This one stays signed in.
        </p>
      )}
    </form>
  );
}

function SecurityTab({ security }: { security?: SecurityOverview }) {
  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <Card title="Change password">
        <ChangePasswordForm />
      </Card>
      <RecoveryCodeCard security={security} />
      {security && (
        <Card title="Sign-in protection" className="xl:col-span-2">
          <ul className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
            <li className="flex gap-2">
              <ShieldCheckIcon className="h-5 w-5 shrink-0 text-accent" aria-hidden />
              <span>
                After {security.lockout_after_failures} wrong passwords or recovery codes, sign-in pauses for{" "}
                {security.lockout_minutes} minutes. It unlocks by itself.
              </span>
            </li>
            <li className="flex gap-2">
              <ShieldCheckIcon className="h-5 w-5 shrink-0 text-accent" aria-hidden />
              <span>
                Sessions last up to {security.session_hours} hours and end after {Math.round(security.session_idle_minutes / 60)}{" "}
                hours without activity.
              </span>
            </li>
            <li className="flex gap-2">
              <ShieldCheckIcon className="h-5 w-5 shrink-0 text-accent" aria-hidden />
              <span>Passwords are stored only as Argon2 hashes; nobody, including the administrator, can read yours.</span>
            </li>
            <li className="flex gap-2">
              <ShieldCheckIcon className="h-5 w-5 shrink-0 text-accent" aria-hidden />
              <span>Every sign-in, failed attempt and account change is recorded in the tamper-evident audit log.</span>
            </li>
          </ul>
        </Card>
      )}
    </div>
  );
}

function RecoveryCodeCard({ security }: { security?: SecurityOverview }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [asking, setAsking] = useState<null | "create" | "revoke">(null);
  const [password, setPassword] = useState("");
  const [issued, setIssued] = useState<RecoveryCodeOut | null>(null);
  const [saved, setSaved] = useState(false);

  const run = useMutation({
    mutationFn: async (what: "create" | "revoke") => {
      if (what === "create") return api.post<RecoveryCodeOut>("/me/recovery-code", { current_password: password });
      await api.remove("/me/recovery-code", { current_password: password });
      return null;
    },
    onSuccess: (result) => {
      setAsking(null);
      setPassword("");
      qc.invalidateQueries({ queryKey: ["me"] });
      if (result) {
        setSaved(false);
        setIssued(result);
      } else toast.success("Recovery code revoked.");
    },
  });

  return (
    <Card title="Recovery code">
      <div className="flex flex-col gap-3">
        <div className="flex items-start gap-3">
          <LifebuoyIcon className="mt-0.5 h-6 w-6 shrink-0 text-accent" aria-hidden />
          <p className="text-sm">
            RiskTrack sends no email, so if you forget your password the only self-service way back in is a{" "}
            <strong>one-time recovery code</strong>. Keep it somewhere safe and offline (a password manager or paper).
            It works once; a new code replaces the old one.
          </p>
        </div>
        {security &&
          (security.has_recovery_code ? (
            <Notice title="A recovery code is set">
              Created <DateTime iso={security.recovery_code_created_at} />. Generate a new one if you've lost it or used it.
            </Notice>
          ) : (
            <Notice tone="warning" title="No recovery code yet">
              Without one, only the administrator can reset your password.
            </Notice>
          ))}
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-primary flex-1 sm:flex-none" onClick={() => setAsking("create")}>
            {security?.has_recovery_code ? "Generate a new code" : "Generate a recovery code"}
          </button>
          {security?.has_recovery_code && (
            <button type="button" className="btn-secondary flex-1 sm:flex-none" onClick={() => setAsking("revoke")}>
              Revoke code
            </button>
          )}
        </div>
      </div>

      <Modal
        open={asking !== null}
        title={asking === "create" ? "Confirm it's you" : "Revoke your recovery code?"}
        onClose={() => {
          setAsking(null);
          setPassword("");
          run.reset();
        }}
        footer={
          <>
            <button type="button" className="btn-secondary" onClick={() => setAsking(null)}>
              Cancel
            </button>
            <button type="submit" form="confirm-pw" className={asking === "revoke" ? "btn-danger" : "btn-primary"} disabled={!password || run.isPending}>
              {run.isPending ? "Checking…" : asking === "create" ? "Generate" : "Revoke"}
            </button>
          </>
        }
      >
        <form
          id="confirm-pw"
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (asking) run.mutate(asking);
          }}
        >
          {run.error && <Notice tone="danger">{run.error.message}</Notice>}
          <p className="text-sm text-muted">
            {asking === "create"
              ? "Enter your password to create a new code. Any earlier code stops working immediately."
              : "Enter your password. Without a code, only the administrator can reset your password."}
          </p>
          <PasswordInput label="Your password" autoComplete="current-password" value={password} onChange={setPassword} />
        </form>
      </Modal>

      <Modal
        open={issued !== null}
        title="Your recovery code"
        onClose={() => saved && setIssued(null)}
        footer={
          <button type="button" className="btn-primary" disabled={!saved} onClick={() => setIssued(null)}>
            Done
          </button>
        }
      >
        {issued && (
          <div className="flex flex-col gap-4">
            <Notice tone="warning" title="Shown only once">
              Save it now. RiskTrack keeps only a fingerprint of it and can't show it again.
            </Notice>
            <div className="mono-data select-all break-all border-2 border-dashed border-accent bg-accent/5 p-4 text-center text-xl font-bold tracking-wider" data-testid="recovery-code">
              {issued.code}
            </div>
            <button
              type="button"
              className="btn-secondary"
              onClick={() =>
                navigator.clipboard
                  ?.writeText(issued.code)
                  .then(() => toast.success("Copied. Paste it into your password manager."))
                  .catch(() => toast.error("Couldn't copy; select the code and copy it by hand."))
              }
            >
              <ClipboardDocumentIcon className="h-4 w-4" aria-hidden /> Copy
            </button>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={saved} onChange={(e) => setSaved(e.target.checked)} />
              I've saved this code somewhere safe
            </label>
          </div>
        )}
      </Modal>
    </Card>
  );
}

// ── Sessions ──────────────────────────────────────────────────────────────────────────────

function SessionsTab() {
  const toast = useToast();
  const qc = useQueryClient();
  const { signOut } = useAuth();
  const [confirmAll, setConfirmAll] = useState(false);
  const q = useQuery({ queryKey: ["me", "sessions"], queryFn: () => api.get<SessionOut[]>("/me/sessions") });
  const end = useMutation({
    mutationFn: (id: number) => api.remove<SignedOut>(`/me/sessions/${id}`),
    onSuccess: () => {
      toast.success("That session was signed out.");
      qc.invalidateQueries({ queryKey: ["me"] });
    },
    onError: toast.error,
  });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} retry={() => q.refetch()} />;
  const rows = q.data ?? [];
  const others = rows.filter((s) => !s.current).length;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted">
        Everywhere you're signed in. If you don't recognise one, sign it out and change your password.
      </p>
      <ul className="flex flex-col gap-3">
        {rows.map((s) => {
          const Icon = /iPhone|Android|iPad/.test(s.device) ? DevicePhoneMobileIcon : ComputerDesktopIcon;
          return (
            <li key={s.id} className={cx("card flex flex-col gap-3 p-3 sm:flex-row sm:items-center", s.current && "border-l-4 border-l-accent")}>
              <div className="flex min-w-0 flex-1 items-start gap-3">
                <Icon className="mt-0.5 h-6 w-6 shrink-0 text-muted" aria-hidden />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 font-semibold">
                    {s.device}
                    {s.current && <span className="chip border-accent text-accent">This device</span>}
                  </div>
                  <div className="text-xs text-muted">
                    {s.ip ? <span className="mono-data">{s.ip}</span> : "Unknown address"} · signed in <DateTime iso={s.created_at} />
                  </div>
                  <div className="text-xs text-muted">
                    Last active <DateTime iso={s.last_seen_at} />
                  </div>
                </div>
              </div>
              {s.current ? (
                <button type="button" className="btn-secondary w-full sm:w-auto" onClick={() => signOut()}>
                  <ArrowRightStartOnRectangleIcon className="h-4 w-4" aria-hidden /> Sign out
                </button>
              ) : (
                <button type="button" className="btn-secondary w-full sm:w-auto" disabled={end.isPending} onClick={() => end.mutate(s.id)}>
                  Sign out this session
                </button>
              )}
            </li>
          );
        })}
      </ul>
      {others > 0 && (
        <div>
          <button type="button" className="btn-danger w-full sm:w-auto" onClick={() => setConfirmAll(true)}>
            Sign out all other sessions ({others})
          </button>
        </div>
      )}
      <ConfirmDialog
        open={confirmAll}
        danger
        title="Sign out everywhere else?"
        message={`${others} other session(s) will be signed out immediately. This device stays signed in.`}
        confirmLabel="Sign them out"
        onConfirm={async () => {
          const r = await api.post<SignedOut>("/me/sessions/sign-out-others");
          toast.success(`${r.sessions_ended} session(s) signed out.`);
          qc.invalidateQueries({ queryKey: ["me"] });
        }}
        onClose={() => setConfirmAll(false)}
      />
    </div>
  );
}

// ── Activity ──────────────────────────────────────────────────────────────────────────────

const ACTIVITY_TEXT: Record<string, string> = {
  LOGIN: "Signed in",
  LOGIN_FAILED: "Failed attempt",
  LOGOUT: "Signed out",
  UPDATE: "Account changed",
};

function ActivityTab() {
  const q = useQuery({ queryKey: ["me", "activity"], queryFn: () => api.get<ActivityOut[]>("/me/activity") });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorState error={q.error} retry={() => q.refetch()} />;
  const rows = q.data ?? [];
  if (!rows.length) return <EmptyState title="No account activity yet" />;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted">Your last 30 sign-ins, failed attempts and account changes. Anything you don't recognise? Change your password.</p>
      <ol className="divide-y divide-line border border-line bg-surface">
        {rows.map((a) => (
          <li key={a.id} className="flex flex-col gap-0.5 px-3 py-2.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className={a.action === "LOGIN_FAILED" ? "chip-strong" : "chip"}>{ACTIVITY_TEXT[a.action] ?? a.action}</span>
              <span className="text-xs text-muted">
                <DateTime iso={a.occurred_at} />
              </span>
            </div>
            {a.detail && <div className="text-sm">{a.detail}</div>}
            {a.ip && <div className="mono-data text-xs text-muted">{a.ip}</div>}
          </li>
        ))}
      </ol>
    </div>
  );
}
