import { describe, expect, it } from "vitest";

import { deadlineHint, formatDate, formatDateTime, formatUtc, resolveZone, zoneAbbreviation } from "./time";

describe("display time zones (PLAN.md §2.7)", () => {
  const iso = "2026-12-05T13:30:00Z";

  it("shows the same instant in WAT, EAT and GMT with the abbreviation", () => {
    expect(formatDateTime(iso, "Africa/Lagos")).toBe("5 Dec 2026, 14:30 WAT");
    expect(formatDateTime(iso, "Africa/Kampala")).toBe("5 Dec 2026, 16:30 EAT");
    expect(formatDateTime(iso, "Africa/Nairobi")).toBe("5 Dec 2026, 16:30 EAT");
    expect(formatDateTime(iso, "Africa/Accra")).toBe("5 Dec 2026, 13:30 GMT");
    expect(formatDateTime(iso, "UTC")).toBe("5 Dec 2026, 13:30 UTC");
  });

  it("crosses midnight correctly", () => {
    expect(formatDateTime("2026-12-05T22:30:00Z", "Africa/Kampala")).toBe("6 Dec 2026, 01:30 EAT");
  });

  it("never converts calendar dates", () => {
    expect(formatDate("2026-12-05")).toBe("5 Dec 2026");
    expect(formatDate(null)).toBe("—");
  });

  it("explains the WAT cut-off on deadlines", () => {
    expect(deadlineHint("2026-12-05")).toBe("Due 5 Dec 2026 (overdue after midnight WAT)");
  });

  it("resolves 'system' to the device zone and keeps explicit zones", () => {
    expect(resolveZone("Africa/Lagos")).toBe("Africa/Lagos");
    expect(resolveZone("system")).toBe(Intl.DateTimeFormat().resolvedOptions().timeZone);
    expect(zoneAbbreviation("Africa/Douala")).toBe("WAT");
  });

  it("gives exact UTC for tooltips", () => {
    expect(formatUtc(iso)).toBe("2026-12-05T13:30:00Z (UTC)");
  });
});
