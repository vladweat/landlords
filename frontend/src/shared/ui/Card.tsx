import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <div className={`rounded-xl bg-white shadow-sm border border-gray-200 p-6 ${className || ''}`}>
      {children}
    </div>
  );
}
