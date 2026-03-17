import { HTMLAttributes, ReactNode } from 'react';
export interface CardProps extends HTMLAttributes<HTMLDivElement> {
    variant?: 'default' | 'glass' | 'gradient' | 'elevated';
    padding?: 'none' | 'sm' | 'md' | 'lg';
    hoverable?: boolean;
    glowColor?: 'primary' | 'accent' | 'success' | 'warning' | 'error';
}
declare const Card: import("react").ForwardRefExoticComponent<CardProps & import("react").RefAttributes<HTMLDivElement>>;
export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
    title?: string;
    subtitle?: string;
    action?: ReactNode;
}
declare const CardHeader: import("react").ForwardRefExoticComponent<CardHeaderProps & import("react").RefAttributes<HTMLDivElement>>;
declare const CardContent: import("react").ForwardRefExoticComponent<HTMLAttributes<HTMLDivElement> & import("react").RefAttributes<HTMLDivElement>>;
declare const CardFooter: import("react").ForwardRefExoticComponent<HTMLAttributes<HTMLDivElement> & import("react").RefAttributes<HTMLDivElement>>;
export { Card, CardHeader, CardContent, CardFooter };
