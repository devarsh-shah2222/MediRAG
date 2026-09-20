import { HTMLAttributes } from "react";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-card border border-ink-100 bg-white p-6 shadow-card transition-all duration-200 ease-out ${className}`}
      {...props}
    />
  );
}
