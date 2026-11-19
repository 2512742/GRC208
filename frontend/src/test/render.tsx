import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";

import type { Me } from "../api/types";
import { AuthProvider } from "../auth/AuthContext";
import { ToastProvider } from "../components/Toast";

export function person(role: Me["role"], permissions: string[], id = 7): Me {
  return {
    id,
    username: role,
    full_name: `Test ${role}`,
    role,
    job_title: null,
    department: null,
    is_active: true,
    email: null,
    display_timezone: "Africa/Lagos",
    created_at: "2026-11-01T00:00:00Z",
    last_login_at: null,
    permissions,
    csrf_token: "x",
  };
}

/** Render inside the real providers with a pre-signed-in user (no network). */
export function renderAs(ui: ReactElement, me: Me | null) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  client.setQueryData(["me"], me);
  client.setQueryData(["timezones"], [{ value: "system", label: "System" }]);
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ToastProvider>
          <AuthProvider>{ui}</AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
