import React from "react";
import cx from "classnames";

export const Input = (p: React.InputHTMLAttributes<HTMLInputElement>) => (
  <input
    {...p}
    className={cx(
      "w-full px-4 py-2 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500",
      p.className
    )}
  />
);

export const Button = ({
  className,
  ...p
}: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
  <button
    {...p}
    className={cx(
      "px-4 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50",
      className
    )}
  />
);

export const Card: React.FC<{
  children: React.ReactNode;
  className?: string;
}> = ({ children, className }) => (
  <div
    className={cx(
      "bg-white border border-gray-200 rounded-2xl p-4 shadow-sm",
      className
    )}
  >
    {children}
  </div>
); 