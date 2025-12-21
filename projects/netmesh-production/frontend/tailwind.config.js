module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  safelist: [
    {
      pattern: /(bg|text|border)-(red|green|yellow|blue|gray)-(100|200|300|400|500|600|700|800)/,
    },
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
