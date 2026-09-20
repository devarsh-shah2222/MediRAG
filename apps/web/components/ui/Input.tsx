import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef } from "react";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = "", ...props }, ref) {
    return (
      <input
        ref={ref}
        className={`focus-ring min-h-[44px] w-full rounded-control border border-ink-200 bg-white px-4 py-2.5 text-base text-ink-900 placeholder:text-ink-500 transition-colors duration-150 hover:border-ink-300 focus:border-brand-500 ${className}`}
        {...props}
      />
    );
  }
);

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className = "", ...props }, ref) {
    return (
      <textarea
        ref={ref}
        className={`focus-ring w-full rounded-control border border-ink-200 bg-white px-4 py-2.5 text-base text-ink-900 placeholder:text-ink-500 transition-colors duration-150 hover:border-ink-300 focus:border-brand-500 ${className}`}
        {...props}
      />
    );
  }
);
