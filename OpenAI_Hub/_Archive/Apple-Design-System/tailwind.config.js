// ==========================================
// TAILWIND CSS CONFIGURATION
// Merge this with your existing tailwind.config.js
// ==========================================

module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      // Apple System Colors
      colors: {
        apple: {
          blue: '#007AFF',
          green: '#34C759',
          indigo: '#5856D6',
          orange: '#FF9500',
          pink: '#FF2D92',
          purple: '#AF52DE',
          red: '#FF3B30',
          teal: '#5AC8FA',
          yellow: '#FFCC00'
        },
        'apple-gray': {
          DEFAULT: '#8E8E93',
          2: '#AEAEB2',
          3: '#C7C7CC',
          4: '#D1D1D6',
          5: '#E5E5EA',
          6: '#F2F2F7'
        },
        glass: {
          light: 'rgba(255, 255, 255, 0.08)',
          medium: 'rgba(255, 255, 255, 0.12)',
          heavy: 'rgba(255, 255, 255, 0.18)',
          border: 'rgba(255, 255, 255, 0.15)'
        },
        // Theme variants
        claude: 'rgba(138, 43, 226, 0.12)',
        grok: 'rgba(255, 69, 0, 0.10)'
      },
      
      // Apple Typography
      fontFamily: {
        'sf-pro': ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'SF Pro Text', 'system-ui', 'sans-serif']
      },
      
      fontSize: {
        'caption-2': ['11px', { lineHeight: '1.2' }],
        'caption-1': ['12px', { lineHeight: '1.2' }],
        'footnote': ['13px', { lineHeight: '1.3' }],
        'subheadline': ['15px', { lineHeight: '1.3' }],
        'callout': ['16px', { lineHeight: '1.4' }],
        'body': ['17px', { lineHeight: '1.4' }],
        'headline': ['17px', { lineHeight: '1.4', fontWeight: '600' }],
        'title-3': ['20px', { lineHeight: '1.3', fontWeight: '600' }],
        'title-2': ['22px', { lineHeight: '1.3', fontWeight: '700' }],
        'title-1': ['28px', { lineHeight: '1.2', fontWeight: '700' }],
        'large-title': ['34px', { lineHeight: '1.1', fontWeight: '700' }]
      },
      
      // Apple Spacing
      spacing: {
        'apple-xs': '4px',
        'apple-sm': '8px',
        'apple-md': '16px',
        'apple-lg': '24px',
        'apple-xl': '32px',
        'apple-2xl': '48px',
        'apple-3xl': '64px'
      },
      
      // Apple Border Radius
      borderRadius: {
        'apple-sm': '8px',
        'apple-md': '12px',
        'apple-lg': '16px',
        'apple-xl': '20px',
        'apple-2xl': '24px'
      },
      
      // Enhanced Backdrop Filters
      backdropBlur: {
        'apple-light': '16px',
        'apple': '24px',
        'apple-heavy': '32px'
      },
      
      backdropSaturate: {
        'apple-light': '1.3',
        'apple': '1.6',
        'apple-heavy': '2.0'
      },
      
      // Apple Shadows
      boxShadow: {
        'apple-sm': '0 1px 2px rgba(0, 0, 0, 0.05)',
        'apple-md': '0 4px 6px rgba(0, 0, 0, 0.07)',
        'apple-lg': '0 10px 15px rgba(0, 0, 0, 0.1)',
        'apple-xl': '0 20px 25px rgba(0, 0, 0, 0.15)',
        'apple-2xl': '0 25px 50px rgba(0, 0, 0, 0.25)',
        'glass': '0 8px 32px rgba(0, 0, 0, 0.25), inset 0 1px rgba(255, 255, 255, 0.3), inset 0 -1px rgba(0, 0, 0, 0.1)'
      },
      
      // Animation & Transitions
      animation: {
        'apple-scale': 'scale 0.2s ease-in-out',
        'apple-fade': 'fade 0.3s ease-in-out',
        'apple-slide': 'slide 0.3s ease-out'
      },
      
      keyframes: {
        scale: {
          '0%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.05)' },
          '100%': { transform: 'scale(1)' }
        },
        fade: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slide: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        }
      },
      
      // Gradients
      backgroundImage: {
        'apple-gradient': 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f4c75 100%)',
        'glass-gradient': 'linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.03) 50%, rgba(255, 255, 255, 0.08) 100%)',
        'claude-gradient': 'linear-gradient(135deg, rgba(138, 43, 226, 0.2) 0%, rgba(138, 43, 226, 0.05) 100%)',
        'grok-gradient': 'linear-gradient(135deg, rgba(255, 69, 0, 0.2) 0%, rgba(255, 69, 0, 0.05) 100%)'
      }
    }
  },
  plugins: [
    // Custom plugin for Apple HIG utilities
    function({ addUtilities, theme }) {
      const newUtilities = {
        // Liquid Glass Utilities
        '.liquid-glass': {
          backdropFilter: 'blur(24px) saturate(1.6)',
          background: 'rgba(255, 255, 255, 0.08)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: theme('borderRadius.apple-lg'),
          position: 'relative',
          overflow: 'hidden',
          '&::before': {
            content: '""',
            position: 'absolute',
            inset: '0',
            background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.15) 0%, rgba(255, 255, 255, 0.03) 50%, rgba(255, 255, 255, 0.08) 100%)',
            borderRadius: 'inherit',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.25), inset 0 1px rgba(255, 255, 255, 0.3), inset 0 -1px rgba(0, 0, 0, 0.1)',
            pointerEvents: 'none'
          },
          '& > *': {
            position: 'relative',
            zIndex: '1'
          }
        },
        '.liquid-glass-navigation': {
          backdropFilter: 'blur(28px) saturate(1.8)',
          background: 'rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(255, 255, 255, 0.15)'
        },
        '.liquid-glass-content': {
          backdropFilter: 'blur(20px) saturate(1.4)',
          background: 'rgba(255, 255, 255, 0.06)',
          border: '1px solid rgba(255, 255, 255, 0.12)'
        },
        '.liquid-glass-claude': {
          backdropFilter: 'blur(22px) saturate(1.6)',
          background: 'rgba(138, 43, 226, 0.12)',
          border: '1px solid rgba(138, 43, 226, 0.25)'
        },
        '.liquid-glass-grok': {
          backdropFilter: 'blur(18px) saturate(1.8)',
          background: 'rgba(255, 69, 0, 0.10)',
          border: '1px solid rgba(255, 69, 0, 0.20)'
        },
        
        // Apple Button Utilities
        '.apple-button': {
          padding: theme('spacing.apple-md') + ' ' + theme('spacing.apple-lg'),
          borderRadius: theme('borderRadius.apple-md'),
          fontWeight: '500',
          fontSize: theme('fontSize.body')[0],
          fontFamily: theme('fontFamily.sf-pro').join(', '),
          border: 'none',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          '&:hover': {
            transform: 'scale(1.05)'
          },
          '&:active': {
            transform: 'scale(0.95)'
          }
        },
        
        // Apple Typography Utilities
        '.apple-title-1': {
          fontSize: theme('fontSize.title-1')[0],
          lineHeight: theme('fontSize.title-1')[1].lineHeight,
          fontWeight: theme('fontSize.title-1')[1].fontWeight,
          fontFamily: theme('fontFamily.sf-pro').join(', ')
        },
        '.apple-title-2': {
          fontSize: theme('fontSize.title-2')[0],
          lineHeight: theme('fontSize.title-2')[1].lineHeight,
          fontWeight: theme('fontSize.title-2')[1].fontWeight,
          fontFamily: theme('fontFamily.sf-pro').join(', ')
        },
        '.apple-body': {
          fontSize: theme('fontSize.body')[0],
          lineHeight: theme('fontSize.body')[1].lineHeight,
          fontFamily: theme('fontFamily.sf-pro').join(', ')
        },
        
        // Apple Container
        '.apple-container': {
          minHeight: '100vh',
          background: theme('backgroundImage.apple-gradient')
        }
      };
      
      addUtilities(newUtilities);
    }
  ]
};