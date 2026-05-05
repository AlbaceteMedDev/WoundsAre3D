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
      },
      boxShadow: {
        soft: "0 8px 24px rgb(var(--shadow) / 0.20)",
        elevated: "0 20px 60px rgb(var(--shadow) / 0.30)",
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
