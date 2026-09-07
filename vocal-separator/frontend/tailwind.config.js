/** @type {import('tailwindcss').Config} */
module.exports = {
	darkMode: 'class',
	content: ['./src/**/*.{js,jsx,ts,tsx}', './public/index.html'],
	theme: {
		extend: {
			colors: {
				primary: {
					50: '#eff6ff',
					100: '#dbeafe',
					500: '#3b82f6',
					600: '#2563eb',
					700: '#1d4ed8',
					900: '#1e3a8a',
				},
				secondary: {
					500: '#8b5cf6',
					600: '#7c3aed',
				},
				accent: {
					500: '#ec4899',
					600: '#db2777',
				},
				success: '#22c55e',
				warning: '#f59e0b',
				error: '#ef4444',
			},
			fontFamily: {
				sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
			},
			keyframes: {
				fadeIn: {
					'0%': { opacity: '0' },
					'100%': { opacity: '1' },
				},
				slideInLeft: {
					'0%': { opacity: '0', transform: 'translateX(-1rem)' },
					'100%': { opacity: '1', transform: 'translateX(0)' },
				},
				slideInRight: {
					'0%': { opacity: '0', transform: 'translateX(1rem)' },
					'100%': { opacity: '1', transform: 'translateX(0)' },
				},
			},
			animation: {
				fadeIn: 'fadeIn 0.5s ease-out',
				slideInLeft: 'slideInLeft 0.5s ease-out',
				slideInRight: 'slideInRight 0.5s ease-out',
			},
			boxShadow: {
				glow: '0 0 40px rgba(59, 130, 246, 0.25)',
			},
		},
	},
	plugins: [require('@tailwindcss/typography'), require('@tailwindcss/forms')],
};
