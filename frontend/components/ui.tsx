"use client";
import * as React from "react";
import clsx from "classnames";

export function Card({
  children,
  className,
}: React.PropsWithChildren<{ className?: string }>) {
  return (
    <div className={clsx("rounded-2xl border bg-white p-4", className)}>
      {children}
    </div>
  );
}

export function Button({
  children,
  className,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-medium",
        "bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-600",
        className
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={clsx(
        "w-full rounded-xl border px-3 py-2 text-sm outline-none",
        "focus:ring-2 focus:ring-blue-200",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
