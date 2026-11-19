import { KeyIcon, PlusIcon, ShieldExclamationIcon } from "@heroicons/react/24/outline";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api/client";
import type { Role, SecurityOverview, SignedOut, UserDetail, UserSummary } from "../api/types";
import { useMe } from "../auth/AuthContext";
import { ConfirmDialog, Modal } from "../components/Modal";
import { NewPasswordFields, newPasswordValid } from "../components/password";
import { useToast } from "../components/Toast";
import { DataTable, DateTime, ErrorState, KeyValue, Loading, Notice, PageHeader, SelectField, TextField } from "../components/ui";
import { ROLE_LABELS, initials } from "../lib/format";

const ROLES: Role[] = ["admin", "analyst", "owner", "approver", "auditor"];

export default function UsersPage() {
  const q = useQuery({ queryKey: ["users", "all"], queryFn: () => api.get<UserSummary[]>("/users") });
  const [editing, setEditing] = useState<UserSummary | "new" | null>(null);
  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Users"
        description="Accounts, roles and account security. Disable an account instead of deleting it, so its history stays attributable."
        actions={
          <button type="button" className="btn-primary" onClick={() => setEditing("new")}>
            <PlusIcon className="h-4 w-4" aria-hidden /> New user
          </button>
        }
      />
      {q.isLoading ? (
        <Loading />
      ) : q.error ? (
        <ErrorState error={q.error} retry={() => q.refetch()} />
      ) : (
        <DataTable
          caption="Users"
          rows={q.data ?? []}
          rowKey={(u) => u.id}
          onRowClick={setEditing}
          mobileHeader={(u) => <UserLine user={u} />}
          columns={[
            { key: "who", header: "User", render: (u) => <UserLine user={u} />, hideOnMobile: true },
            { key: "title", header: "Job title", render: (u) => u.job_title ?? "—" },
            { key: "role", header: "Role", render: (u) => <span className="chip">{ROLE_LABELS[u.role]}</span> },
            { key: "active", header: "Status", render: (u) => (u.is_active ? "Active" : <span className="chip-strong">Disabled</span>) },
          ]}
        />
      )}
      {editing === "new" && <NewUserDialog onClose={() => setEditing(null)} />}
      {editing && editing !== "new" && <UserDialog userId={editing.id} onClose={() => setEditing(null)} />}
    </>
  );
}

function UserLine({ user }: { user: UserSummary }) {
  return (
    <span className="flex items-center gap-3">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-container text-xs font-bold">
        {initials(user.full_name)}
      </span>
      <span className="min-w-0">
        <span className="block truncate font-medium">{user.full_name}</span>
        <span className="mono-data block truncate text-xs text-muted">{user.username}</span>
      </span>
    </span>
  );
}

function Footer({ onClose, busy, form, label, disabled }: { onClose: () => void; busy: boolean; form: string; label: string; disabled?: boolean }) {
  return (
    <>
      <button type="button" className="btn-secondary" onClick={onClose}>
        Cancel
      </button>
      <button type="submit" form={form} className="btn-primary" disabled={busy || disabled}>
        {busy ? "Saving…" : label}
      </button>
    </>
  );
}

function NewUserDialog({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [f, setF] = useState({ username: "", full_name: "", job_title: "", department: "", email: "", role: "owner" as Role });
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const m = useMutation({
    mutationFn: () =>
      api.post<UserDetail>("/users", {
        ...f,
        username: f.username.trim().toLowerCase(),
        job_title: f.job_title || null,
        department: f.department || null,
        email: f.email || null,
        password,
      }),
    onSuccess: (u) => {
      toast.success(`${u.username} created. They must choose their own password at first sign-in.`);
      qc.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
  });
  const valid = f.username.length >= 3 && f.full_name.length >= 2 && newPasswordValid(password, confirm, f.username || " ");
  return (
    <Modal open wide title="New user" onClose={onClose} footer={<Footer onClose={onClose} busy={m.isPending} form="new-user" label="Create user" disabled={!valid} />}>
      <form
        id="new-user"
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
      >
        {m.error && <Notice tone="danger">{m.error.message}</Notice>}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <TextField label="Username" required autoCapitalize="none" value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} hint="Lowercase letters, digits, dots or dashes." />
          <TextField label="Full name" required value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} />
          <TextField label="Job title" value={f.job_title} onChange={(e) => setF({ ...f, job_title: e.target.value })} />
          <TextField label="Department" value={f.department} onChange={(e) => setF({ ...f, department: e.target.value })} />
          <TextField label="Email" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
          <SelectField label="Role" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value as Role })} options={ROLES.map((r) => ({ value: r, label: ROLE_LABELS[r] }))} />
        </div>
        <Notice>
          This is a temporary password: the user must replace it at first sign-in, so you never know their working password.
          Share it privately, never in chat, slides or the report.
        </Notice>
        <NewPasswordFields username={f.username || " "} value={password} confirm={confirm} onValue={setPassword} onConfirm={setConfirm} />
      </form>
    </Modal>
  );
}

function UserDialog({ userId, onClose }: { userId: number; onClose: () => void }) {
  const me = useMe();
  const toast = useToast();
  const qc = useQueryClient();
  const self = userId === me.id;
  const detail = useQuery({ queryKey: ["users", userId], queryFn: () => api.get<UserDetail>(`/users/${userId}`) });
  const security = useQuery({ queryKey: ["users", userId, "security"], queryFn: () => api.get<SecurityOverview>(`/users/${userId}/security`) });
  const [form, setForm] = useState<{ full_name: string; job_title: string; department: string; role: Role; active: boolean } | null>(null);
  const [resetting, setResetting] = useState(false);
  const [signOutAll, setSignOutAll] = useState(false);

  const u = detail.data;
  const values = form ?? (u ? { full_name: u.full_name, job_title: u.job_title ?? "", department: u.department ?? "", role: u.role, active: u.is_active } : null);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["users"] });
  };
  const save = useMutation({
    mutationFn: () =>
      api.patch<UserDetail>(`/users/${userId}`, {
        full_name: values!.full_name,
        job_title: values!.job_title || null,
        department: values!.department || null,
        role: values!.role,
        is_active: values!.active,
      }),
    onSuccess: (saved) => {
      toast.success(`${saved.username} saved.`);
      refresh();
      onClose();
    },
  });

  return (
    <Modal
      open
      wide
      title={u ? `${u.full_name} (${u.username})` : "User"}
      onClose={onClose}
      footer={<Footer onClose={onClose} busy={save.isPending} form="user-form" label="Save" disabled={!form} />}
    >
      {detail.isLoading || !values || !u ? (
        <Loading />
      ) : (
        <div className="flex flex-col gap-5">
          <form
            id="user-form"
            className="flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate();
            }}
          >
            {save.error && <Notice tone="danger">{save.error.message}</Notice>}
            <TextField label="Full name" required value={values.full_name} onChange={(e) => setForm({ ...values, full_name: e.target.value })} />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TextField label="Job title" value={values.job_title} onChange={(e) => setForm({ ...values, job_title: e.target.value })} />
              <TextField label="Department" value={values.department} onChange={(e) => setForm({ ...values, department: e.target.value })} />
              <SelectField
                label="Role"
                value={values.role}
                disabled={self}
                onChange={(e) => setForm({ ...values, role: e.target.value as Role })}
                options={ROLES.map((r) => ({ value: r, label: ROLE_LABELS[r] }))}
                hint={self ? "You can't change your own role." : undefined}
              />
              <SelectField
                label="Status"
                value={values.active ? "1" : "0"}
                disabled={self}
                onChange={(e) => setForm({ ...values, active: e.target.value === "1" })}
                options={[
                  { value: "1", label: "Active" },
                  { value: "0", label: "Disabled (signs out everywhere)" },
                ]}
              />
            </div>
          </form>

          <section className="border-t border-line pt-4">
            <h3 className="label-caps mb-3 text-ink">Account security</h3>
            {security.data ? (
              <>
                {security.data.locked && (
                  <div className="mb-3">
                    <Notice tone="danger" title="Sign-in paused">
                      {security.data.recent_failed_sign_ins} failed attempts in the last {security.data.lockout_minutes} minutes. It unlocks by
                      itself; if it wasn't the user, reset the password.
                    </Notice>
                  </div>
                )}
                <KeyValue
                  items={[
                    ["Last sign-in", <DateTime iso={security.data.last_login_at} />],
                    ["Password changed", security.data.password_changed_at ? <DateTime iso={security.data.password_changed_at} /> : "Never"],
                    ["Must change password", security.data.must_change_password ? "Yes, at next sign-in" : "No"],
                    ["Recovery code", security.data.has_recovery_code ? "Set by the user" : "Not set"],
                    ["Signed-in sessions", String(security.data.active_sessions)],
                    ["Failed sign-ins (window)", String(security.data.recent_failed_sign_ins)],
                  ]}
                />
              </>
            ) : (
              <Loading />
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" className="btn-secondary flex-1 sm:flex-none" onClick={() => setResetting(true)}>
                <KeyIcon className="h-4 w-4" aria-hidden /> Reset password
              </button>
              <button
                type="button"
                className="btn-secondary flex-1 sm:flex-none"
                disabled={!security.data?.active_sessions}
                onClick={() => setSignOutAll(true)}
              >
                <ShieldExclamationIcon className="h-4 w-4" aria-hidden /> Sign out everywhere
              </button>
            </div>
            <p className="mt-2 text-xs text-muted">
              Administrators never see passwords or recovery codes. A reset sets a temporary password that the user must
              replace at the next sign-in, and ends their sessions.
            </p>
          </section>
        </div>
      )}

      {resetting && u && <ResetPasswordDialog user={u} onClose={() => setResetting(false)} />}
      <ConfirmDialog
        open={signOutAll}
        danger
        title={`Sign ${u?.full_name ?? "this user"} out everywhere?`}
        message="Every session of this account ends now (for a lost phone or a suspected compromise)."
        confirmLabel="Sign out everywhere"
        onConfirm={async () => {
          const r = await api.post<SignedOut>(`/users/${userId}/sign-out-everywhere`);
          toast.success(`${r.sessions_ended} session(s) ended.`);
          qc.invalidateQueries({ queryKey: ["users", userId, "security"] });
        }}
        onClose={() => setSignOutAll(false)}
      />
    </Modal>
  );
}

function ResetPasswordDialog({ user, onClose }: { user: UserDetail; onClose: () => void }) {
  const toast = useToast();
  const qc = useQueryClient();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const m = useMutation({
    mutationFn: () => api.patch<UserDetail>(`/users/${user.id}`, { new_password: password }),
    onSuccess: () => {
      toast.success(`Temporary password set for ${user.username}. They must change it at next sign-in.`);
      qc.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
  });
  return (
    <Modal
      open
      title={`Reset password for ${user.username}`}
      onClose={onClose}
      footer={<Footer onClose={onClose} busy={m.isPending} form="reset-pw" label="Set temporary password" disabled={!newPasswordValid(password, confirm, user.username)} />}
    >
      <form
        id="reset-pw"
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
      >
        {m.error && <Notice tone="danger">{m.error.message}</Notice>}
        <Notice tone="warning">
          Use this when the user has no recovery code. Their sessions end now and they must choose a new password at
          the next sign-in. Give them the temporary password privately.
        </Notice>
        <NewPasswordFields username={user.username} value={password} confirm={confirm} onValue={setPassword} onConfirm={setConfirm} />
      </form>
    </Modal>
  );
}
