import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eefbf9",
          100: "#d3f4ee",
          200: "#a8e8de",
          300: "#72d6c8",
          400: "#3fbcae",
          500: "#219f92",
          600: "#157f76",
          700: "#146560",
          800: "#14514e",
          900: "#134341",
        },
        urgent: {
          50: "#fffaeb",
          100: "#fef0c7",
          500: "#f59e0b",
          600: "#d97706",
          700: "#b45309",
        },
        emergency: {
          50: "#fef2f2",
          100: "#fee2e2",
          500: "#ef4444",
          600: "#dc2626",
          700: "#b91c1c",
        },
        ink: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          500: "#64748b",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
        },
      },
      borderRadius: {
        card: "1rem",
        control: "0.75rem",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgba(15, 23, 42, 0.06), 0 1px 3px 0 rgba(15, 23, 42, 0.08)",
        floating: "0 8px 24px -4px rgba(15, 23, 42, 0.12)",
      },
      fontSize: {
        base: ["1.0625rem", "1.65rem"],
      },
    },
  },
  plugins: [],
};

export default config;
