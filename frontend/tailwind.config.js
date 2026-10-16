/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        display: ['Plus Jakarta Sans', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        background: "#FAFAFA",
        foreground: "#111827",
        surface: {
          DEFAULT: "#FFFFFF",
          subtle: "#F8FAFC",
          muted: "#F0F0F2",
        },
        card: {
          DEFAULT: "#FFFFFF",
          foreground: "#111827",
        },
        popover: {
          DEFAULT: "#FFFFFF",
          foreground: "#111827",
        },
        primary: {
          DEFAULT: "#FF385C",
          hover: "#E0284B",
          foreground: "#FFFFFF",
          subtle: "#FFF1F2",
        },
        secondary: {
          DEFAULT: "#F59E0B",
          hover: "#D97706",
          foreground: "#FFFFFF",
          subtle: "#FEF3C7",
        },
        emerald: {
          50: "#ECFDF5",
          500: "#10B981",
          600: "#059669",
          700: "#047857",
        },
        muted: {
          DEFAULT: "#F3F4F6",
          foreground: "#6B7280",
        },
        accent: {
          DEFAULT: "#FF385C",
          foreground: "#FFFFFF",
        },
        destructive: {
          DEFAULT: "#EF4444",
          foreground: "#FFFFFF",
        },
        border: "#F0F0F2",
        input: "#E5E7EB",
        ring: "#FF385C",
      },
      borderRadius: {
        lg: "1rem",
        md: "0.75rem",
        sm: "0.5rem",
        full: "9999px",
      },
      boxShadow: {
        'card': '0px 4px 16px -2px rgba(17, 24, 39, 0.04), 0px 1px 3px rgba(17, 24, 39, 0.02)',
        'float': '0px 8px 30px rgba(17, 24, 39, 0.08), 0px 2px 6px rgba(17, 24, 39, 0.04)',
        'modal': '0px 20px 40px -4px rgba(17, 24, 39, 0.12), 0px 8px 16px -4px rgba(17, 24, 39, 0.06)',
      },
      aspectRatio: {
        'reel': '9 / 16',
      },
    },
  },
  plugins: [],
}
