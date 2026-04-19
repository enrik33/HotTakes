import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
}

export default function Card({ children, className = '' }: CardProps) {
  return (
    <div
      className={`bg-slate-800 rounded-xl border border-slate-700 p-5 ${className}`}
    >
      {children}
    </div>
  );
}
