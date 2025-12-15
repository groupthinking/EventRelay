'use client';

import React, { useState, useRef, useEffect } from 'react';
import { cn } from '../../lib/utils';

interface DropdownMenuProps {
  children: React.ReactNode;
  className?: string;
}

interface DropdownMenuTriggerProps {
  children: React.ReactNode;
  className?: string;
}

interface DropdownMenuContentProps {
  children: React.ReactNode;
  className?: string;
  align?: 'start' | 'center' | 'end';
}

interface DropdownMenuItemProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
}

interface DropdownMenuLabelProps {
  children: React.ReactNode;
  className?: string;
}

interface DropdownMenuSeparatorProps {
  className?: string;
}

const DropdownMenu: React.FC<DropdownMenuProps> = ({ children, className }) => {
  return (
    <div className={cn("relative", className)}>
      {children}
    </div>
  );
};

const DropdownMenuTrigger: React.FC<DropdownMenuTriggerProps> = ({ children, className }) => {
  const [isOpen, setIsOpen] = useState(false);
  const triggerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (triggerRef.current && !triggerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div
      ref={triggerRef}
      className={cn("cursor-pointer", className)}
      onClick={() => setIsOpen(!isOpen)}
    >
      {children}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 z-50">
          {/* Content will be rendered by DropdownMenuContent */}
        </div>
      )}
    </div>
  );
};

const DropdownMenuContent: React.FC<DropdownMenuContentProps> = ({ 
  children, 
  className,
  align = 'start' 
}) => {
  const alignClasses = {
    start: 'left-0',
    center: 'left-1/2 transform -translate-x-1/2',
    end: 'right-0'
  };

  return (
    <div
      className={cn(
        "absolute top-full mt-1 z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md animate-in data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2",
        alignClasses[align],
        className
      )}
    >
      {children}
    </div>
  );
};

const DropdownMenuItem: React.FC<DropdownMenuItemProps> = ({ 
  children, 
  className,
  onClick,
  disabled = false 
}) => {
  return (
    <div
      className={cn(
        "relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        disabled && "opacity-50 cursor-not-allowed",
        !disabled && "hover:bg-accent hover:text-accent-foreground cursor-pointer",
        className
      )}
      onClick={!disabled ? onClick : undefined}
    >
      {children}
    </div>
  );
};

const DropdownMenuLabel: React.FC<DropdownMenuLabelProps> = ({ children, className }) => {
  return (
    <div
      className={cn(
        "px-2 py-1.5 text-sm font-semibold",
        className
      )}
    >
      {children}
    </div>
  );
};

const DropdownMenuSeparator: React.FC<DropdownMenuSeparatorProps> = ({ className }) => {
  return (
    <div
      className={cn(
        "-mx-1 my-1 h-px bg-muted",
        className
      )}
    />
  );
};

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator
};
