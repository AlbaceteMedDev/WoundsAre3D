import type { Config } from "tailwindcss";

const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: token("bg"),
        surface: token("surface"),
        "surface-2": token("surface-2"),
        hairline: token("hairline"),
        ink: token("ink"),
        "ink-soft": token("ink-soft"),
        "ink-muted": token("ink-muted"),
        accent: token("accent"),
        "accent-bright": token("accent-bright"),
        "accent-soft": token("accent-soft"),
        success: token("success"),
        warn: token("warn"),
        danger: token("danger"),
        // Legacy alias so older `brand-*` classes keep compiling.
        brand: {
          50: token("accent-soft"),
          100: token("accent-soft"),
          500: token("accent"),
          600: token("accent"),
          700: token("accent-bright"),
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        // Layered ramps: a tight contact shadow plus a soft ambient one. The
        // per-theme --shadow-N strengths keep dark mode from rendering these as
        // invisible pure black (it previously had --shadow: 0 0 0, i.e. none).
        soft: "0 1px 2px rgb(var(--shadow) / var(--shadow-1)), 0 6px 16px -4px rgb(var(--shadow) / var(--shadow-2))",
        elevated:
          "0 1px 2px rgb(var(--shadow) / var(--shadow-1)), 0 8px 24px -6px rgb(var(--shadow) / var(--shadow-2)), 0 24px 56px -12px rgb(var(--shadow) / var(--shadow-3))",
        accent: "0 8px 30px rgb(var(--accent) / 0.18)",
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
        xl: "24px",
      },
      transitionTimingFunction: {
        "out-expo": "cubic-bezier(0.19, 1, 0.22, 1)",
        "out-quart": "cubic-bezier(0.25, 1, 0.5, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
