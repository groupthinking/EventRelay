import { InputHTMLAttributes, ReactNode } from 'react';
export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
    variant?: 'default' | 'ghost' | 'filled';
    inputSize?: 'sm' | 'md' | 'lg';
    error?: boolean;
    errorMessage?: string;
    leftIcon?: ReactNode;
    rightIcon?: ReactNode;
    label?: string;
    helperText?: string;
}
declare const Input: import("react").ForwardRefExoticComponent<InputProps & import("react").RefAttributes<HTMLInputElement>>;
export { Input };
