import type { Config } from "tailwindcss";

/** Every color resolves to a CSS variable holding "R G B" channels (see app/globals.css). */
const channel = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const scale = (name: string, steps: number[]) =>
  Object.fromEntries(steps.map((step) => [step, channel(`${name}-${step}`)]));

const SEMANTIC_STEPS = [50, 100, 200, 500, 600, 700, 800];

export default {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand: ultramarine. Accent: signal lime (used on dark surfaces / as highlight, never as text on white).
        brand: scale("brand", [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]),
        signal: { DEFAULT: channel("signal"), soft: channel("signal-soft"), ink: channel("signal-ink") },
        // Decision semantics: PAGAR = pay, FRENAR = stop, ESCALAR = escalate, info = neutral info.
        pay: scale("pay", SEMANTIC_STEPS),
        stop: scale("stop", SEMANTIC_STEPS),
        escalate: scale("escalate", SEMANTIC_STEPS),
        info: scale("info", SEMANTIC_STEPS),
        // Surfaces & text.
        paper: channel("paper"),
        canvas: channel("canvas"),
        surface: { DEFAULT: channel("surface"), raised: channel("surface-raised"), sunken: channel("surface-sunken") },
        night: { DEFAULT: channel("night"), soft: channel("night-soft"), line: channel("night-line") },
        ink: { DEFAULT: channel("ink"), muted: channel("ink-muted"), subtle: channel("ink-subtle") },
        line: { DEFAULT: channel("line"), strong: channel("line-strong") },
        // Legacy aliases kept so older markup stays on-palette.
        accent: { DEFAULT: channel("brand-600"), hover: channel("brand-700") },
        danger: channel("stop-700"),
        success: channel("pay-700"),
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-sans)", "ui-sans-serif", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        display: ["2.75rem", { lineHeight: "1.05", letterSpacing: "-0.035em", fontWeight: "700" }],
        h1: ["2rem", { lineHeight: "1.1", letterSpacing: "-0.03em", fontWeight: "700" }],
        h2: ["1.25rem", { lineHeight: "1.25", letterSpacing: "-0.015em", fontWeight: "650" }],
        h3: ["1rem", { lineHeight: "1.35", letterSpacing: "-0.01em", fontWeight: "600" }],
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
        eyebrow: ["0.6875rem", { lineHeight: "1rem", letterSpacing: "0.12em", fontWeight: "600" }],
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        DEFAULT: "var(--radius-md)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
        "2xl": "var(--radius-2xl)",
      },
      boxShadow: {
        xs: "var(--shadow-xs)",
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        glow: "var(--shadow-glow)",
      },
      maxWidth: {
        content: "72rem",
        narrow: "48rem",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.45", transform: "scale(0.8)" },
        },
        shimmer: {
          from: { backgroundPosition: "-200% 0" },
          to: { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "fade-up": "fade-up 320ms cubic-bezier(0.2, 0.7, 0.2, 1) both",
        "pulse-dot": "pulse-dot 1.6s ease-in-out infinite",
        shimmer: "shimmer 1.6s linear infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
