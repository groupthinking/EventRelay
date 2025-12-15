import * as React from "react";

export interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className }) => {
  return (
    <div className={`rounded-lg border bg-white p-6 shadow-sm ${className || ""}`}>
      {children}
    </div>
  );
};
