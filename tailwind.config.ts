import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          50:  "#eeedf8",
          100: "#cccaf0",
          500: "#3d2d9e",
          600: "#29166f",  /* Boronkay blue */
          700: "#1e1054",
          900: "#0e0828",
        },
        crimson: {
          50:  "#f9eeee",
          100: "#f0d0ce",
          500: "#c22319",
          600: "#9a1c13",  /* Boronkay red */
          700: "#7a1610",
        },
      },
      animation: {
        "fade-in":    "fadeIn 0.5s ease-out both",
        "fade-up":    "fadeUp 0.6s ease-out both",
        "slide-in":   "slideIn 0.4s ease-out both",
        "pulse-slow": "pulse 3s ease-in-out infinite",
        "float":      "float 4s ease-in-out infinite",
        "stamp":      "stamp 0.6s cubic-bezier(0.175,0.885,0.32,1.275) both",
        "spin-slow":  "spin 12s linear infinite",
      },
      keyframes: {
        fadeIn:  { "0%": { opacity: "0" },                                "100%": { opacity: "1" } },
        fadeUp:  { "0%": { opacity: "0", transform: "translateY(20px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        slideIn: { "0%": { opacity: "0", transform: "translateX(-10px)" }, "100%": { opacity: "1", transform: "translateX(0)" } },
        float:   { "0%,100%": { transform: "translateY(0px)" },           "50%":  { transform: "translateY(-10px)" } },
        stamp:   { "0%": { opacity: "0", transform: "scale(1.4) rotate(-8deg)" }, "100%": { opacity: "1", transform: "scale(1) rotate(0deg)" } },
      },
    },
  },
  plugins: [],
};

export default config;
