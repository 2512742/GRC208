import { describe, expect, it } from "vitest";

import { bandFor, compactNaira, previewExplanation } from "./format";

describe("scoring preview mirrors services/scoring.py", () => {
  it("bands every score 1-25 at the same boundaries", () => {
    const bands = Array.from({ length: 25 }, (_, i) => bandFor(i + 1));
    expect(bands.slice(0, 4).every((b) => b === "low")).toBe(true);
    expect(bands.slice(4, 9).every((b) => b === "medium")).toBe(true);
    expect(bands.slice(9, 14).every((b) => b === "high")).toBe(true);
    expect(bands.slice(14).every((b) => b === "critical")).toBe(true);
  });

  const policy = { appetite_threshold: 10, sla_days_critical: 30, sla_days_high: 90, sla_days_medium: 180 };

  it("reproduces the brief's explanation text for L4 x I5", () => {
    expect(previewExplanation(4, 5, policy)).toBe(
      "Likelihood 4 (Likely) × Impact 5 (Severe) = 20 → Critical. Above appetite (threshold 10). Remediation due within 30 days.",
    );
  });

  it("flags the 9/10 appetite boundary", () => {
    expect(previewExplanation(3, 3, policy)).toContain("Within appetite (threshold 10)");
    expect(previewExplanation(2, 5, policy)).toContain("Above appetite (threshold 10)");
  });

  it("formats naira compactly", () => {
    expect(compactNaira("30650000.00")).toBe("₦30.65m");
    expect(compactNaira(2500)).toBe("₦2.5k");
  });
});
