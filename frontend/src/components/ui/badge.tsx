import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'border-transparent gradient-bg text-white',
        secondary: 'border-transparent bg-secondary text-secondary-foreground',
        destructive: 'border-transparent bg-red-500/20 text-red-400 border-red-500/30',
        outline: 'text-foreground border-white/20',
        success: 'border-transparent bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
        warning: 'border-transparent bg-amber-500/20 text-amber-400 border-amber-500/30',
        info: 'border-transparent bg-blue-500/20 text-blue-400 border-blue-500/30',
        pending: 'border-transparent bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
