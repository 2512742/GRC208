import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, buildUrl, describeError } from "./client";

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "risktrack_csrf=; Max-Age=0; path=/";
});

describe("api client", () => {
  it("drops empty query values", () => {
    expect(buildUrl("/risks", { q: "", band: "high", page: 2, x: undefined, y: null })).toBe("/api/risks?band=high&page=2");
  });

  it("turns FastAPI errors into readable messages", () => {
    expect(describeError(403, { detail: "You own this risk, so another approver must decide." }).message).toBe(
      "You own this risk, so another approver must decide.",
    );
    const err = describeError(422, {
      detail: [{ loc: ["body", "justification"], msg: "String should have at least 30 characters" }],
    });
    expect(err.message).toBe("justification: String should have at least 30 characters");
    expect(err.fieldErrors.justification).toContain("30");
    expect(describeError(429, null).message).toMatch(/Too many attempts/);
  });

  it("sends the CSRF cookie value in X-CSRF-Token on writes only (T23)", async () => {
    document.cookie = "risktrack_csrf=abc123; path=/";
    const fetchMock = vi.fn().mockImplementation(async () => new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.get("/me");
    await api.post("/auth/logout");
    expect(fetchMock.mock.calls[0][1].headers["X-CSRF-Token"]).toBeUndefined();
    expect(fetchMock.mock.calls[1][1].headers["X-CSRF-Token"]).toBe("abc123");
    expect(fetchMock.mock.calls[1][1].credentials).toBe("same-origin");
  });

  it("throws ApiError with the status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Not found." }), { status: 404 })));
    await expect(api.get("/risks/999")).rejects.toEqual(new ApiError(404, "Not found."));
  });
});
