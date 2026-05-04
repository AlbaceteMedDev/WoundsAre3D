import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f1f6ff",
          100: "#dde9ff",
          500: "#3a6cff",
          600: "#2a55cc",
          700: "#1d3f99",
        },
      },
    },
  },
  plugins: [],
};

export default config;
