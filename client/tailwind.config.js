/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "primary": "#2463eb",
        "background-light": "#f6f6f8",
        "background-dark": "#111621",
        "navy": "#0f172a",
      },
      fontFamily: {
        "display": ["Lexend", "sans-serif"],
        "sans": ["Lexend", "sans-serif"]
      },
      borderRadius: {
        "DEFAULT": "0.5rem",
        "lg": "1rem",
        "xl": "1.5rem",
        "full": "9999px"
      },
      boxShadow: {
        "glow": "0 0 40px -10px rgba(36, 99, 235, 0.5)",
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
