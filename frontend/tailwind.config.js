/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        gray: {
          850: '#1f2937', // gray-800과 gray-900 사이의 중간 색상
        },
        orange: {
          950: '#431407', // 매우 어두운 오렌지 배경
        }
      },
    },
  },
  plugins: [],
};
