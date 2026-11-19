import { PlusIcon } from "@heroicons/react/24/outline";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../api/client";
import type { Role, UserDetail, UserSummary } from "../api/types";
import { useMe } from "../auth/AuthContext";
import { Modal } from "../components/Modal";
import { useToast } from "../components/Toast";
import { DataTable, ErrorState, Loading, Notice, PageHeader, SelectField, TextField } from "../components/ui";
import { ROLE_LABELS } from "../lib/format";

const ROLES: Role[] = ["admin", "analyst", "owner", "approver", "auditor"];

export default function UsersPage() {
  const q = useQuery({ queryKey: ["users", "all"], queryFn: () => api.get<UserSummary[]>("/users") });
  const [editing, setEditing] = useState<UserSummary | "new" | null>(null);
  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Users"
        description="Accounts and roles. Disable an account instead of deleting it, so its history stays attributable."
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
          columns={[
            { key: "username", header: "Username", render: (u) => <span className="mono-data">{u.username}</span> },
            { key: "name", header: "Name", render: (u) => u.full_name },
            { key: "title", header: "Job title", render: (u) => u.job_title ?? "—" },
            { key: "role", header: "Role", render: (u) => <span className="chip">{ROLE_LABELS[u.role]}</span> },
            { key: "active", header: "Status", render: (u) => (u.is_active ? "Active" : <span className="chip-strong">Disabled</span>) },
          ]}
        />
      )}
      {editing && <UserDialog user={editing === "new" ? undefined : editing} onClose={() => setEditing(null)} />}
    </>
  );
}

function UserDialog({ user, onClose }: { user?: UserSummary; onClose: () => void }) {
  const me = useMe();
  const toast = useToast();
  const qc = useQueryClient();
  const [username, setUsername] = useState(user?.username ?? "");
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [jobTitle, setJobTitle] = useState(user?.job_title ?? "");
  const [department, setDepartment] = useState(user?.department ?? "");
  const [role, setRole] = useState<Role>(user?.role ?? "owner");
  const [active, setActive] = useState(user?.is_active ?? true);
  const [password, setPassword] = useState("");
  const self = user?.id === me.id;

  const m = useMutation({
    mutationFn: () =>
      user
        ? api.patch<UserDetail>(`/users/${user.id}`, {
            full_name: fullName,
            job_title: jobTitle || null,
            department: department || null,
            role,
            is_active: active,
            new_password: password || null,
          })
        : api.post<UserDetail>("/users", {
            username,
            full_name: fullName,
            job_title: jobTitle || null,
            department: department || null,
            role,
            password,
          }),
    onSuccess: (u) => {
      toast.success(`${u.username} saved.`);
      qc.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
  });

  return (
    <Modal
      open
      onClose={onClose}
      title={user ? `Edit ${user.username}` : "New user"}
      footer={
        <>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" form="user-form" className="btn-primary" disabled={m.isPending}>
            {m.isPending ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      <form
        id="user-form"
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          m.mutate();
        }}
      >
        {m.error && <Notice tone="danger">{m.error.message}</Notice>}
        {!user && <TextField label="Username" required autoCapitalize="none" value={username} onChange={(e) => setUsername(e.target.value)} hint="Lowercase letters, digits, dots or dashes." />}
        <TextField label="Full name" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <TextField label="Job title" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} />
          <TextField label="Department" value={department} onChange={(e) => setDepartment(e.target.value)} />
          <SelectField label="Role" value={role} disabled={self} onChange={(e) => setRole(e.target.value as Role)} options={ROLES.map((r) => ({ value: r, label: ROLE_LABELS[r] }))} hint={self ? "You can't change your own role." : undefined} />
          {user && (
            <SelectField label="Status" value={active ? "1" : "0"} disabled={self} onChange={(e) => setActive(e.target.value === "1")} options={[{ value: "1", label: "Active" }, { value: "0", label: "Disabled" }]} />
          )}
        </div>
        <TextField
          label={user ? "New password" : "Initial password"}
          type="password"
          autoComplete="new-password"
          required={!user}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          hint={user ? "Leave empty to keep the current password. Changing it signs the user out everywhere." : "Share it privately; never in chat, slides or the report."}
        />
      </form>
    </Modal>
  );
}
