
'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { createPortal } from 'react-dom';
import { Loader2, Sparkles, Zap, Brain } from 'lucide-react';
import { TooltipConfig } from '@/lib/types';

interface AITooltipProps {
  children: React.ReactNode;
  content?: string;
  aiPrompt?: string;
  config?: TooltipConfig;
  elementId?: string;
}

interface TooltipPosition {
  x: number;
  y: number;
  placement: 'top' | 'bottom' | 'left' | 'right' | 'top-start' | 'top-end' | 'bottom-start' | 'bottom-end';
}

export function AITooltip({ 
  children, 
  content, 
  aiPrompt, 
  config = {}, 
  elementId 
}: AITooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [aiContent, setAIContent] = useState<string | null>(null);
  const [position, setPosition] = useState<TooltipPosition>({ x: 0, y: 0, placement: 'top' });
  const [hovering, setHovering] = useState(false);
  const [hoverIntent, setHoverIntent] = useState(false);
  
  const triggerRef = useRef<HTMLElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const intentTimeoutRef = useRef<NodeJS.Timeout>();
  const hideTimeoutRef = useRef<NodeJS.Timeout>();
  const mousePosRef = useRef({ x: 0, y: 0 });
  
  const {
    delay = 300,
    fadeTime = 200,
    followMouse = false,
    interactive = false,
    aiGenerated = !!aiPrompt,
    placement: preferredPlacement = 'top'
  } = config;

  // Hover intent detection (inspired by PowerTip)
  const handleMouseEnter = useCallback((e: MouseEvent) => {
    setHovering(true);
    mousePosRef.current = { x: e.clientX, y: e.clientY };
    
    // Start intent detection
    intentTimeoutRef.current = setTimeout(() => {
      const currentPos = mousePosRef.current;
      const distance = Math.sqrt(
        Math.pow(e.clientX - currentPos.x, 2) + 
        Math.pow(e.clientY - currentPos.y, 2)
      );
      
      // If mouse hasn't moved much, show intent
      if (distance < 7) {
        setHoverIntent(true);
      }
    }, delay);
  }, [delay]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    mousePosRef.current = { x: e.clientX, y: e.clientY };
    
    if (followMouse && isVisible) {
      updateTooltipPosition(e);
    }
  }, [followMouse, isVisible]);

  const handleMouseLeave = useCallback(() => {
    setHovering(false);
    setHoverIntent(false);
    
    if (intentTimeoutRef.current) {
      clearTimeout(intentTimeoutRef.current);
    }
    
    if (!interactive) {
      hideTimeoutRef.current = setTimeout(() => {
        setIsVisible(false);
      }, 100);
    }
  }, [interactive]);

  // Calculate optimal position
  const calculatePosition = useCallback((event: MouseEvent): TooltipPosition => {
    if (!triggerRef.current) return { x: 0, y: 0, placement: preferredPlacement };
    
    const rect = triggerRef.current.getBoundingClientRect();
    const tooltipWidth = 300; // Estimated width
    const tooltipHeight = 100; // Estimated height
    const offset = 10;
    
    let x = rect.left + rect.width / 2;
    let y = rect.top;
    let placement: TooltipPosition['placement'] = preferredPlacement;
    
    if (followMouse) {
      x = event.clientX;
      y = event.clientY - tooltipHeight - offset;
      placement = 'top';
    } else {
      // Smart placement logic
      const spaceTop = rect.top;
      const spaceBottom = window.innerHeight - rect.bottom;
      const spaceLeft = rect.left;
      const spaceRight = window.innerWidth - rect.right;
      
      if (preferredPlacement === 'top' && spaceTop < tooltipHeight + offset) {
        placement = 'bottom';
        y = rect.bottom + offset;
      } else if (preferredPlacement === 'bottom' && spaceBottom < tooltipHeight + offset) {
        placement = 'top';
        y = rect.top - tooltipHeight - offset;
      } else if (preferredPlacement === 'left' && spaceLeft < tooltipWidth + offset) {
        placement = 'right';
        x = rect.right + offset;
        y = rect.top + rect.height / 2;
      } else if (preferredPlacement === 'right' && spaceRight < tooltipWidth + offset) {
        placement = 'left';
        x = rect.left - tooltipWidth - offset;
        y = rect.top + rect.height / 2;
      } else {
        // Use preferred placement
        if (placement === 'top') {
          y = rect.top - tooltipHeight - offset;
        } else if (placement === 'bottom') {
          y = rect.bottom + offset;
        } else if (placement === 'left') {
          x = rect.left - tooltipWidth - offset;
          y = rect.top + rect.height / 2;
        } else if (placement === 'right') {
          x = rect.right + offset;
          y = rect.top + rect.height / 2;
        }
      }
    }
    
    return { x, y, placement };
  }, [preferredPlacement, followMouse]);

  const updateTooltipPosition = useCallback((event: MouseEvent) => {
    const newPosition = calculatePosition(event);
    setPosition(newPosition);
  }, [calculatePosition]);

  // Generate AI content
  const generateAIContent = useCallback(async () => {
    if (!aiPrompt || aiContent) return;
    
    setIsLoading(true);
    try {
      const response = await fetch('/api/generate-tooltip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          prompt: aiPrompt,
          elementId,
          context: triggerRef.current?.textContent || ''
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setAIContent(data.content);
      }
    } catch (error) {
      console.error('Failed to generate AI content:', error);
    } finally {
      setIsLoading(false);
    }
  }, [aiPrompt, aiContent, elementId]);

  // Show tooltip when hover intent is detected
  useEffect(() => {
    if (hoverIntent && !isVisible) {
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current);
      }
      
      setIsVisible(true);
      
      if (aiGenerated && !aiContent) {
        generateAIContent();
      }
    }
  }, [hoverIntent, isVisible, aiGenerated, aiContent, generateAIContent]);

  // Set up event listeners
  useEffect(() => {
    const element = triggerRef.current;
    if (!element) return;

    element.addEventListener('mouseenter', handleMouseEnter);
    element.addEventListener('mousemove', handleMouseMove);
    element.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      element.removeEventListener('mouseenter', handleMouseEnter);
      element.removeEventListener('mousemove', handleMouseMove);
      element.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [handleMouseEnter, handleMouseMove, handleMouseLeave]);

  // Clean up timeouts
  useEffect(() => {
    return () => {
      if (intentTimeoutRef.current) clearTimeout(intentTimeoutRef.current);
      if (hideTimeoutRef.current) clearTimeout(hideTimeoutRef.current);
    };
  }, []);

  const displayContent = aiContent || content || 'Loading...';

  return (
    <>
      {React.cloneElement(children as React.ReactElement<any>, {
        ref: triggerRef,
        'data-tooltip-id': elementId
      })}
      {typeof window !== 'undefined' && createPortal(
        (
          <AnimatePresence>
            {isVisible && (
              <motion.div
                ref={tooltipRef}
                initial={{ opacity: 0, scale: 0.95, y: -10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: -10 }}
                transition={{ duration: fadeTime / 1000, ease: 'easeOut' }}
                className="fixed z-50 pointer-events-none"
                style={{
                  left: position.x,
                  top: position.y,
                  transform: followMouse 
                    ? 'translate(-50%, -100%)'
                    : position.placement === 'top' 
                      ? 'translate(-50%, -100%)'
                      : position.placement === 'bottom'
                        ? 'translate(-50%, 0%)'
                        : position.placement === 'left'
                          ? 'translate(-100%, -50%)'
                          : 'translate(0%, -50%)'
                }}
                onMouseEnter={() => interactive && setHovering(true)}
                onMouseLeave={() => interactive && handleMouseLeave()}
              >
                <div className={`
                  max-w-xs p-3 rounded-lg shadow-elegant-lg border backdrop-blur-sm
                  ${interactive ? 'pointer-events-auto' : 'pointer-events-none'}
                  bg-background/95 border-border text-foreground
                  ${aiGenerated ? 'border-primary/20' : ''}
                `}>
                  {aiGenerated && (
                    <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground">
                      {isLoading ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Sparkles className="w-3 h-3 text-primary" />
                      )}
                      <span>{isLoading ? 'Generating...' : 'AI Generated'}</span>
                    </div>
                  )}
                  
                  <div className="text-sm">
                    {isLoading ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Generating intelligent content...</span>
                      </div>
                    ) : (
                      displayContent
                    )}
                  </div>
                  
                  {/* Arrow */}
                  <div 
                    className={`
                      absolute w-2 h-2 bg-background border rotate-45
                      ${position.placement === 'top' ? 'top-full left-1/2 -translate-x-1/2 -translate-y-1/2 border-b border-r' : ''}
                      ${position.placement === 'bottom' ? 'bottom-full left-1/2 -translate-x-1/2 translate-y-1/2 border-t border-l' : ''}
                      ${position.placement === 'left' ? 'left-full top-1/2 -translate-x-1/2 -translate-y-1/2 border-t border-r' : ''}
                      ${position.placement === 'right' ? 'right-full top-1/2 translate-x-1/2 -translate-y-1/2 border-b border-l' : ''}
                    `}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        ) as any,
        document.body
      )}
    </>
  );
}
