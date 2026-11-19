import { describe, expect, it } from "vitest";

import { initials } from "../lib/format";
import { newPasswordValid, passwordChecks } from "./password";

describe("password checklist mirrors the server policy", () => {
  it("flags each rule", () => {
    const failed = (pw: string, current?: string) =>
      passwordChecks(pw, "omotayo", current)
        .filter((c) => !c.ok)
        .map((c) => c.text);
    expect(failed("short")).toContain("At least 10 characters");
    expect(failed("aaaaaaaaaaaa")).toEqual(["At least 5 different characters"]);
    expect(failed("Omotayo-2026-x")).toEqual(["Doesn't contain your username"]);
    expect(failed(" Ledger-Locks-2026")).toEqual(["No spaces at the start or end"]);
    expect(failed("Ledger-Locks-2026", "Ledger-Locks-2026")).toEqual(["Different from the current password"]);
    expect(failed("Ledger-Locks-2026")).toEqual([]);
  });

  it("needs the confirmation to match", () => {
    expect(newPasswordValid("Ledger-Locks-2026", "Ledger-Locks-2026", "omotayo")).toBe(true);
    expect(newPasswordValid("Ledger-Locks-2026", "Ledger-Locks-2027", "omotayo")).toBe(false);
  });

  it("makes avatar initials", () => {
    expect(initials("Ernestina Lamiorkor Tawiah")).toBe("EL");
    expect(initials("admin")).toBe("A");
  });
});
