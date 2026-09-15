import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07111f",
        panel: "#0d1b2a",
        panelMuted: "#12243a",
        signal: "#b8f36b",
        amber: "#ffbd70",
        danger: "#ff8585",
        quiet: "#8ea4bb",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(184,243,107,.08), 0 20px 60px rgba(0,0,0,.24)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "SFMono-Regular"],
      },
    },
  },
  plugins: [],
};

export default config;
