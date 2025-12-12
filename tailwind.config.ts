import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      gridTemplateColumns: {
        '13': 'repeat(13, minmax(0, 1fr))',
      },
      colors: {
        blue: {
          400: '#2589FE',
          500: '#0070F3',
          600: '#2F6FEB',
        },
      },
    },
    keyframes: {
      shimmer: {
        '100%': {
          transform: 'translateX(100%)',
        },
      },
      bubble: {
        '0%': { transform: 'scale(0.8)', opacity: '0.5' },
        '50%': { transform: 'scale(0.9)', opacity: '0.7' },
        '100%': { transform: 'scale(1)', opacity: '1' }
      }
    },
  },
  plugins: [require('@tailwindcss/forms')],
};
export default config;
