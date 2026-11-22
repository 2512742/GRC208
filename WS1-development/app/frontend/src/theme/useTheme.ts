import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";
const KEY = "risktrack-theme";

function current(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

/** Pairs with public/theme-init.js, which applies the saved theme before first paint. */
export function useTheme(): { theme: Theme; toggle: () => void; set: (t: Theme) => void } {
  const [theme, setTheme] = useState<Theme>(current);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const set = useCallback((t: Theme) => {
    setTheme(t);
    try {
      localStorage.setItem(KEY, t);
    } catch {
      /* storage blocked */
    }
  }, []);

  const toggle = useCallback(() => set(current() === "dark" ? "light" : "dark"), [set]);
  return { theme, toggle, set };
}
