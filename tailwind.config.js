/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        accent: '#1E3A8A',
        'card-bg': '#FFFFFF',
        'hdr-bg': '#F1F5F9',
        sidebar: '#1E293B',
        muted: '#374151',
        border: '#CBD5E1',
        'chat-bg': '#0F172A',
        'chat-bar': '#1E293B',
      },
    },
  },
  plugins: [],
}
