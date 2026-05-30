import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        muted: "#6b7280",
        line: "#d9dde3",
        paper: "#ffffff",
        mist: "#f5f6f8",
        field: "#f9fafb",
        accent: "#15803d",
        accentSoft: "#e8f5ec"
      },
      boxShadow: {
        line: "0 1px 0 rgba(17, 24, 39, 0.06)"
      }
    }
  },
  plugins: []
} satisfies Config;
