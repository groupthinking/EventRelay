import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Loader2, Sparkles, BrainCircuit } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';

export function ThinkingIndicator() {
  const [isExpanded, setIsExpanded] = useState(true);

  // Mock steps for the visual effect
  // "Active Inference" steps - focusing on Code Generation as the differentiator
  const steps = [
    "Analyzing video context...",
    "Extracting coding patterns...",
    "Synthesizing architecture...",
    "Generating executable code..."
  ];

  const [currentStep, setCurrentStep] = useState(2); // Mock progress

  return (
    <div className="border border-border/50 rounded-lg bg-muted/30 overflow-hidden mb-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 p-3 text-sm font-medium hover:bg-muted/50 transition-colors"
      >
        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        <BrainCircuit className="h-4 w-4 text-[#0092b8]" />
        <span className="text-muted-foreground">Reasoning Process</span>
        <span className="ml-auto text-xs text-muted-foreground animate-pulse">Active Inference...</span>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="px-4 pb-4 space-y-3"
          >
            {steps.map((step, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <div className={cn(
                  "h-2 w-2 rounded-full",
                  i < currentStep ? "bg-green-500" :
                    i === currentStep ? "bg-[#0092b8] animate-pulse" : "bg-muted"
                )} />
                <span className={cn(
                  i < currentStep ? "text-muted-foreground line-through opacity-70" :
                    i === currentStep ? "text-foreground font-medium" : "text-muted-foreground opacity-50"
                )}>
                  {step}
                </span>
                {i === currentStep && <Loader2 className="h-3 w-3 animate-spin text-[#0092b8] ml-auto" />}
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}