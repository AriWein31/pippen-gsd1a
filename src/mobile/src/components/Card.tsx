import React from 'react';
import { cn } from '../utils/helpers';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  variant?: 'default' | 'outlined' | 'active';
}

export const Card: React.FC<CardProps> = ({
  children,
  className,
  onClick,
  variant = 'default',
}) => {
  const variantStyles = {
    default: 'bg-white shadow-sm',
    outlined: 'bg-white border-2 border-[#E5E7EB]',
    active: 'bg-[#315BFF] text-white shadow-md',
  };

  return (
    <div
      className={cn(
        'rounded-2xl p-4 transition-all duration-200',
        variantStyles[variant],
        onClick && 'cursor-pointer hover:scale-[1.02] active:scale-[0.98]',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {children}
    </div>
  );
};

interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({ children, className }) => (
  <div className={cn('font-semibold text-lg mb-3', className)}>
    {children}
  </div>
);

interface CardContentProps {
  children: React.ReactNode;
  className?: string;
}

export const CardContent: React.FC<CardContentProps> = ({ children, className }) => (
  <div className={cn('', className)}>
    {children}
  </div>
);

interface CardFooterProps {
  children: React.ReactNode;
  className?: string;
}

export const CardFooter: React.FC<CardFooterProps> = ({ children, className }) => (
  <div className={cn('mt-4 pt-4 border-t border-[#E5E7EB]', className)}>
    {children}
  </div>
);
