/******** Framework-friendly Tailwind config; styling will be reintroduced later ********/
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      borderRadius: {
        lg: "10px",
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgba(0,0,0,0.04)",
      },
    },
  },
  plugins: [],
};
