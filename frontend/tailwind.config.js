/** Guardian "Deep Intel" design system mapped onto CSS variables (PLAN.md §2.6). */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  safelist: ["bg-band-low", "bg-band-medium", "bg-band-high", "bg-band-critical"],
  theme: {
    borderRadius: { none: "0", DEFAULT: "0", full: "9999px" },
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      colors: {
        bg: v("bg"),
        surface: v("surface"),
        container: v("surface-container"),
        hover: v("hover"),
        ink: v("text"),
        muted: v("text-muted"),
        outline: v("outline"),
        line: v("outline-variant"),
        primary: v("primary"),
        "primary-container": v("primary-container"),
        "on-accent": v("on-accent"),
        btn: v("btn"),
        "btn-hover": v("btn-hover"),
        "on-btn": v("on-btn"),
        "danger-fill": v("danger-fill"),
        "on-danger-fill": v("on-danger-fill"),
        "strong-fill": v("strong-fill"),
        "on-strong-fill": v("on-strong-fill"),
        accent: v("accent"),
        danger: v("error"),
        footer: v("footer"),
        band: {
          low: v("band-low"),
          medium: v("band-medium"),
          high: v("band-high"),
          critical: v("band-critical"),
        },
      },
      fontSize: {
        display: ["48px", { lineHeight: "1.1", fontWeight: "700" }],
        h1: ["32px", { lineHeight: "1.2", fontWeight: "700" }],
        h2: ["24px", { lineHeight: "1.3", fontWeight: "600" }],
        h3: ["20px", { lineHeight: "1.35", fontWeight: "600" }],
      },
    },
  },
  plugins: [],
};
