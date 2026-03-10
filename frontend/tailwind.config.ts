import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          primary: "#09090F",
          secondary: "#0F0F1A",
        },
        accent: {
          gold: "#F4A918",
          'gold-lt': "#FFBE45",
        },
        text: {
          primary: "#F7F8FA",
          secondary: "#8892A4",
          muted: "#4A5568",
        },
        success: "#22C55E",
        error: "#F43F5E",
      },
      borderRadius: {
        sm: "6px",
        md: "12px",
        lg: "20px",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic": "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.7", transform: "scale(1.05)" },
        }
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
      }
    },
  },
  plugins: [],
};
export default config;
