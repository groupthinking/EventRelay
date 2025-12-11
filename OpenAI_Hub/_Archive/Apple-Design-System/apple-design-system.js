// ==========================================
// PORTABLE APPLE HIG DESIGN SYSTEM
// Complete component library for reuse across projects
// ==========================================

import React, { useState } from 'react';

// 1. DESIGN TOKENS - Copy these values to your project
// ==========================================

export const DesignTokens = {
  // Apple HIG Colors
  colors: {
    // System Colors
    systemBlue: '#007AFF',
    systemGreen: '#34C759',
    systemIndigo: '#5856D6',
    systemOrange: '#FF9500',
    systemPink: '#FF2D92',
    systemPurple: '#AF52DE',
    systemRed: '#FF3B30',
    systemTeal: '#5AC8FA',
    systemYellow: '#FFCC00',
    
    // Gray Scale
    systemGray: '#8E8E93',
    systemGray2: '#AEAEB2',
    systemGray3: '#C7C7CC',
    systemGray4: '#D1D1D6',
    systemGray5: '#E5E5EA',
    systemGray6: '#F2F2F7',
    
    // Background Colors
    primaryBackground: 'rgba(0, 0, 0, 0.9)',
    secondaryBackground: 'rgba(28, 28, 30, 0.85)',
    tertiaryBackground: 'rgba(44, 44, 46, 0.75)',
    
    // Liquid Glass Effects
    liquidGlass: {
      light: 'rgba(255, 255, 255, 0.08)',
      medium: 'rgba(255, 255, 255, 0.12)',
      heavy: 'rgba(255, 255, 255, 0.18)',
      border: 'rgba(255, 255, 255, 0.15)'
    }
  },
  
  // Typography Scale (Apple SF Pro)
  typography: {
    sizes: {
      caption2: '11px',
      caption1: '12px',
      footnote: '13px',
      subheadline: '15px',
      callout: '16px',
      body: '17px',
      headline: '17px',
      title3: '20px',
      title2: '22px',
      title1: '28px',
      largeTitle: '34px'
    },
    weights: {
      ultraLight: '100',
      thin: '200',
      light: '300',
      regular: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
      heavy: '800',
      black: '900'
    },
    fontFamily: {
      system: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif'
    }
  },
  
  // Spacing Scale
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
    '2xl': '48px',
    '3xl': '64px'
  },
  
  // Border Radius
  borderRadius: {
    sm: '8px',
    md: '12px',
    lg: '16px',
    xl: '20px',
    '2xl': '24px',
    full: '9999px'
  },
  
  // Shadows
  shadows: {
    sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px rgba(0, 0, 0, 0.07)',
    lg: '0 10px 15px rgba(0, 0, 0, 0.1)',
    xl: '0 20px 25px rgba(0, 0, 0, 0.15)',
    '2xl': '0 25px 50px rgba(0, 0, 0, 0.25)'
  }
};

// 2. CORE LIQUID GLASS COMPONENT
// ==========================================

export const LiquidGlass = ({ 
  children, 
  intensity = 0.8, 
  className = '', 
  edgeEffect = 'soft', 
  variant = 'default',
  style = {} 
}) => {
  const variants = {
    default: {
      backdropFilter: `blur(${intensity * 24}px) saturate(${1 + intensity * 0.6})`,
      background: `rgba(255, 255, 255, ${intensity * 0.08})`,
      border: `1px solid rgba(255, 255, 255, ${intensity * 0.18})`
    },
    navigation: {
      backdropFilter: `blur(${intensity * 28}px) saturate(${1 + intensity * 0.8})`,
      background: `rgba(0, 0, 0, ${intensity * 0.3})`,
      border: `1px solid rgba(255, 255, 255, ${intensity * 0.15})`
    },
    content: {
      backdropFilter: `blur(${intensity * 20}px) saturate(${1 + intensity * 0.4})`,
      background: `rgba(255, 255, 255, ${intensity * 0.06})`,
      border: `1px solid rgba(255, 255, 255, ${intensity * 0.12})`
    },
    claude: {
      backdropFilter: `blur(${intensity * 22}px) saturate(${1 + intensity * 0.6})`,
      background: `rgba(138, 43, 226, ${intensity * 0.12})`,
      border: `1px solid rgba(138, 43, 226, ${intensity * 0.25})`
    },
    grok: {
      backdropFilter: `blur(${intensity * 18}px) saturate(${1 + intensity * 0.8})`,
      background: `rgba(255, 69, 0, ${intensity * 0.10})`,
      border: `1px solid rgba(255, 69, 0, ${intensity * 0.20})`
    }
  };

  const glassStyle = variants[variant] || variants.default;
  const borderRadius = edgeEffect === 'soft' ? '16px' : '8px';

  return (
    <div 
      className={`relative ${className}`}
      style={{
        ...glassStyle,
        borderRadius,
        ...style
      }}
    >
      {/* Material Layer */}
      <div 
        className="absolute inset-0"
        style={{
          background: `linear-gradient(135deg, 
            rgba(255, 255, 255, ${intensity * 0.15}) 0%, 
            rgba(255, 255, 255, ${intensity * 0.03}) 50%,
            rgba(255, 255, 255, ${intensity * 0.08}) 100%)`,
          borderRadius: 'inherit',
          boxShadow: `
            0 8px 32px rgba(0, 0, 0, ${intensity * 0.25}),
            inset 0 1px rgba(255, 255, 255, ${intensity * 0.3}),
            inset 0 -1px rgba(0, 0, 0, ${intensity * 0.1})
          `
        }}
      />
      
      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};

// 3. BUTTON COMPONENTS
// ==========================================

export const AppleButton = ({ 
  children, 
  variant = 'primary', 
  size = 'medium',
  disabled = false,
  onClick,
  className = '',
  ...props 
}) => {
  const variants = {
    primary: {
      background: DesignTokens.colors.systemBlue,
      color: 'white',
      hover: 'rgba(0, 122, 255, 0.8)'
    },
    secondary: {
      background: 'rgba(255, 255, 255, 0.1)',
      color: 'white',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      hover: 'rgba(255, 255, 255, 0.15)'
    },
    destructive: {
      background: DesignTokens.colors.systemRed,
      color: 'white',
      hover: 'rgba(255, 59, 48, 0.8)'
    },
    ghost: {
      background: 'transparent',
      color: 'white',
      hover: 'rgba(255, 255, 255, 0.1)'
    }
  };

  const sizes = {
    small: { padding: '8px 16px', fontSize: '14px' },
    medium: { padding: '12px 24px', fontSize: '16px' },
    large: { padding: '16px 32px', fontSize: '18px' }
  };

  const variantStyle = variants[variant];
  const sizeStyle = sizes[size];

  return (
    <button
      className={`rounded-lg font-medium transition-all duration-200 ${
        disabled ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105 active:scale-95'
      } ${className}`}
      style={{
        ...variantStyle,
        ...sizeStyle,
        borderRadius: DesignTokens.borderRadius.md
      }}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
};

// 4. CARD COMPONENT
// ==========================================

export const AppleCard = ({ 
  children, 
  intensity = 0.8, 
  hover = true,
  className = '',
  style = {} 
}) => {
  return (
    <LiquidGlass
      intensity={intensity}
      className={`p-6 ${hover ? 'hover:scale-105 cursor-pointer' : ''} transition-all duration-300 ${className}`}
      style={style}
    >
      {children}
    </LiquidGlass>
  );
};

// 5. NAVIGATION COMPONENTS
// ==========================================

export const AppleNavigation = ({ 
  children, 
  title,
  leftButton,
  rightButton,
  intensity = 0.9 
}) => {
  return (
    <LiquidGlass 
      intensity={intensity} 
      variant="navigation" 
      className="border-b border-white/10"
    >
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center space-x-3">
          {leftButton}
          {title && <h1 className="text-lg font-semibold text-white">{title}</h1>}
        </div>
        <div className="flex items-center space-x-2">
          {rightButton}
        </div>
      </div>
      {children}
    </LiquidGlass>
  );
};

export const AppleTabBar = ({ items, activeIndex = 0, onTabChange }) => {
  return (
    <LiquidGlass intensity={0.9} className="border-t border-white/10">
      <div className="flex justify-around py-3">
        {items.map((item, index) => {
          const IconComponent = item.icon;
          const isActive = index === activeIndex;
          
          return (
            <button
              key={index}
              onClick={() => onTabChange?.(index)}
              className={`flex flex-col items-center space-y-1 px-4 py-2 rounded-xl transition-all duration-200 ${
                isActive 
                  ? 'text-blue-400 bg-blue-400/20 scale-110' 
                  : 'text-white/60 hover:text-white/80 hover:bg-white/10'
              }`}
            >
              <IconComponent className="w-6 h-6" />
              <span className="text-xs font-medium">{item.label}</span>
            </button>
          );
        })}
      </div>
    </LiquidGlass>
  );
};

// 6. FORM COMPONENTS
// ==========================================

export const AppleInput = ({ 
  placeholder, 
  value, 
  onChange, 
  type = 'text',
  icon,
  className = '' 
}) => {
  return (
    <LiquidGlass intensity={0.6} className={`relative ${className}`}>
      <div className="flex items-center p-3">
        {icon && (
          <div className="mr-3 text-white/60">
            {icon}
          </div>
        )}
        <input
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          className="flex-1 bg-transparent text-white placeholder-white/50 focus:outline-none"
          style={{ fontSize: DesignTokens.typography.sizes.body }}
        />
      </div>
    </LiquidGlass>
  );
};

export const AppleToggle = ({ checked, onChange, label }) => {
  return (
    <div className="flex items-center justify-between">
      {label && <span className="text-white font-medium">{label}</span>}
      <button
        onClick={() => onChange?.(!checked)}
        className={`w-12 h-6 rounded-full transition-colors duration-200 ${
          checked ? 'bg-blue-500' : 'bg-gray-600'
        }`}
      >
        <div 
          className={`w-5 h-5 bg-white rounded-full transition-transform duration-200 ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  );
};

// 7. LAYOUT COMPONENTS
// ==========================================

export const AppleContainer = ({ children, className = '' }) => {
  return (
    <div className={`min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 ${className}`}>
      {children}
    </div>
  );
};

export const AppleGrid = ({ 
  children, 
  columns = 'auto', 
  gap = 'md',
  className = '' 
}) => {
  const gapSizes = {
    sm: 'gap-2',
    md: 'gap-4',
    lg: 'gap-6',
    xl: 'gap-8'
  };

  const gridCols = typeof columns === 'number' 
    ? `grid-cols-${columns}` 
    : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';

  return (
    <div className={`grid ${gridCols} ${gapSizes[gap]} ${className}`}>
      {children}
    </div>
  );
};

// 8. EXAMPLE USAGE COMPONENT
// ==========================================

export const ExampleUsage = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [toggleState, setToggleState] = useState(false);
  
  const tabItems = [
    { icon: () => <div>🏠</div>, label: 'Home' },
    { icon: () => <div>🔍</div>, label: 'Search' },
    { icon: () => <div>⚙️</div>, label: 'Settings' }
  ];

  return (
    <AppleContainer>
      <AppleNavigation 
        title="Apple Design System Demo"
        leftButton={<div className="text-white">←</div>}
        rightButton={<div className="text-white">•••</div>}
      />
      
      <div className="p-6 space-y-6">
        <AppleGrid columns={2} gap="lg">
          <AppleCard intensity={0.8}>
            <h3 className="text-white font-semibold mb-2">Liquid Glass Card</h3>
            <p className="text-white/80 mb-4">This card demonstrates the liquid glass effect.</p>
            <AppleButton variant="primary" onClick={() => alert('Hello!')}>
              Primary Button
            </AppleButton>
          </AppleCard>
          
          <AppleCard intensity={0.6}>
            <h3 className="text-white font-semibold mb-4">Form Controls</h3>
            <div className="space-y-4">
              <AppleInput 
                placeholder="Enter text..." 
                icon={<div>🔍</div>}
              />
              <AppleToggle 
                label="Enable notifications"
                checked={toggleState}
                onChange={setToggleState}
              />
            </div>
          </AppleCard>
        </AppleGrid>
        
        <LiquidGlass intensity={0.7} className="p-6">
          <h2 className="text-white text-xl font-bold mb-4">Design Token Examples</h2>
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-500 rounded-lg mx-auto mb-2"></div>
              <div className="text-white text-sm">System Blue</div>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-green-500 rounded-lg mx-auto mb-2"></div>
              <div className="text-white text-sm">System Green</div>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-red-500 rounded-lg mx-auto mb-2"></div>
              <div className="text-white text-sm">System Red</div>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-purple-500 rounded-lg mx-auto mb-2"></div>
              <div className="text-white text-sm">System Purple</div>
            </div>
          </div>
        </LiquidGlass>
      </div>
      
      <AppleTabBar 
        items={tabItems}
        activeIndex={activeTab}
        onTabChange={setActiveTab}
      />
    </AppleContainer>
  );
};

// Export everything for easy importing
export default {
  DesignTokens,
  LiquidGlass,
  AppleButton,
  AppleCard,
  AppleNavigation,
  AppleTabBar,
  AppleInput,
  AppleToggle,
  AppleContainer,
  AppleGrid,
  ExampleUsage
};