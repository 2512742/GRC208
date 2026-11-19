/**
 * One small fetch wrapper for the whole app.
 *
 * - Same-origin only: the session cookie is HttpOnly; the CSRF cookie is readable and echoed in
 *   the X-CSRF-Token header on every state-changing request (T23).
 * - Errors become ApiError with the server's message, so screens show "You own this risk"
 *   instead of a generic failure.
 * - A 401 tells the auth layer the session is gone (expired or signed out elsewhere).
 */

export const CSRF_COOKIE = "risktrack_csrf";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly fieldErrors: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | number | boolean | null | undefined>;

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

export function readCookie(name: string): string | null {
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

export function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return `/api${path}${qs ? `?${qs}` : ""}`;
}

/** Turn FastAPI's error bodies (string detail or a validation list) into readable text. */
export function describeError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return new ApiError(status, detail);
  if (Array.isArray(detail)) {
    const fields: Record<string, string> = {};
    const lines = detail.map((d: { loc?: (string | number)[]; msg?: string }) => {
      const loc = (d.loc ?? []).filter((p) => p !== "body" && p !== "query");
      const field = loc.join(".");
      const msg = (d.msg ?? "invalid").replace(/^Value error, /, "");
      if (field) fields[field] = msg;
      return field ? `${field}: ${msg}` : msg;
    });
    return new ApiError(status, lines.join("; "), fields);
  }
  const fallback: Record<number, string> = {
    401: "Please sign in.",
    403: "You don't have permission to do that.",
    404: "Not found.",
    413: "That file is too large.",
    429: "Too many attempts. Please wait and try again.",
  };
  return new ApiError(status, fallback[status] ?? `Request failed (${status}).`);
}

export async function request<T>(
  method: string,
  path: string,
  options: { query?: Query; json?: unknown; form?: FormData } = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  let body: BodyInit | undefined;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  } else if (options.form) {
    body = options.form;
  }
  if (method !== "GET" && method !== "HEAD") {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  const response = await fetch(buildUrl(path, options.query), {
    method,
    headers,
    body,
    credentials: "same-origin",
  });
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login") onUnauthorized?.();
    throw describeError(response.status, data);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>("GET", path, { query }),
  post: <T>(path: string, json?: unknown) => request<T>("POST", path, { json: json ?? {} }),
  patch: <T>(path: string, json: unknown) => request<T>("PATCH", path, { json }),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, { form }),
  /** DELETE, optionally with a JSON body (e.g. a password confirmation). */
  remove: <T>(path: string, json?: unknown) => request<T>("DELETE", path, json === undefined ? {} : { json }),
};

/** Downloads go through fetch (so the CSRF/session rules stay identical), then a blob link. */
export async function download(path: string, query?: Query): Promise<void> {
  const response = await fetch(buildUrl(path, query), { credentials: "same-origin" });
  if (!response.ok) {
    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    throw describeError(response.status, data);
  }
  const disposition = response.headers.get("content-disposition") ?? "";
  const name = /filename="?([^";]+)"?/.exec(disposition)?.[1] ?? "download";
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
