import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "../../lib/cn";

type ButtonVariant = "default" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const variantClassMap: Record<ButtonVariant, string> = {
  default: "hub-btn-primary",
  secondary: "hub-btn-secondary",
  ghost: "hub-btn-ghost",
  danger: "hub-btn-danger",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "secondary", type = "button", ...props },
  ref,
) {
  return <button ref={ref} type={type} className={cn("action-btn ui-button", variantClassMap[variant], className)} {...props} />;
});

export default Button;
