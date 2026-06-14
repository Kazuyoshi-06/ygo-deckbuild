/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'bg-base': '#08090D',
        'bg-surface': '#111318',
        'bg-elevated': '#1A1C24',
        'bg-overlay': '#22252F',
        gold: {
          DEFAULT: '#C9A449',
          50: '#FFF9EA',
          100: '#FFF0C2',
          200: '#FFE085',
          300: '#F9C94A',
          400: '#D9B860',
          500: '#C9A449',
          600: '#A67A28',
          700: '#855F1E',
        },
        'blue-accent': '#5B8EFF',
        'text-primary': '#ECEDF2',
        'text-secondary': '#8B8FA8',
        'text-tertiary': '#5A5E73',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderColor: {
        subtle: 'rgba(255,255,255,0.06)',
        default: 'rgba(255,255,255,0.10)',
        strong: 'rgba(255,255,255,0.18)',
      },
    },
  },
  plugins: [],
};
