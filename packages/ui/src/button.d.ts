import * as React from "react";
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "outline";
}
export declare const Button: React.FC<ButtonProps>;
