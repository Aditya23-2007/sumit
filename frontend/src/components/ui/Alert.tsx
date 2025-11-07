import { HTMLAttributes, forwardRef } from 'react'
import { cn } from '@/lib/utils'

export interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'success' | 'warning' | 'danger' | 'info'
}

export const Alert = forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = 'info', children, ...props }, ref) => {
    const variants = {
      success: 'bg-success-50 border-success-400 text-success-800',
      warning: 'bg-warning-50 border-warning-400 text-warning-800',
      danger: 'bg-danger-50 border-danger-400 text-danger-800',
      info: 'bg-primary-50 border-primary-400 text-primary-800',
    }

    return (
      <div
        ref={ref}
        className={cn(
          'p-4 rounded-md border-l-4',
          variants[variant],
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Alert.displayName = 'Alert'