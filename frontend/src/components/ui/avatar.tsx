import * as React from 'react';
import Image from 'next/image';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn, getInitials } from '@/lib/utils';

const avatarVariants = cva(
  'relative flex shrink-0 overflow-hidden rounded-full',
  {
    variants: {
      size: {
        xs: 'h-6 w-6 text-xs',
        sm: 'h-8 w-8 text-xs',
        default: 'h-10 w-10 text-sm',
        lg: 'h-12 w-12 text-base',
        xl: 'h-16 w-16 text-lg',
        '2xl': 'h-24 w-24 text-2xl',
      },
    },
    defaultVariants: {
      size: 'default',
    },
  }
);

// Map size variant to pixel dimensions for Next.js Image
const sizeMap = {
  xs: 24,
  sm: 32,
  default: 40,
  lg: 48,
  xl: 64,
  '2xl': 96,
} as const;

export interface AvatarProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof avatarVariants> {
  src?: string | null;
  alt?: string;
  fallback?: string;
  /** Use native img instead of Next.js Image (for external URLs without domain config) */
  useNativeImg?: boolean;
}

const Avatar = React.forwardRef<HTMLSpanElement, AvatarProps>(
  ({ className, size = 'default', src, alt, fallback, useNativeImg = false, ...props }, ref) => {
    const [hasError, setHasError] = React.useState(false);
    const initials = fallback ? getInitials(fallback) : alt ? getInitials(alt) : '?';
    const pixelSize = sizeMap[size || 'default'];

    React.useEffect(() => {
      setHasError(false);
    }, [src]);

    const renderImage = () => {
      if (!src || hasError) {
        return (
          <span className="flex h-full w-full items-center justify-center rounded-full bg-muted font-medium uppercase text-muted-foreground">
            {initials}
          </span>
        );
      }

      // Use native img for external URLs or when explicitly requested
      if (useNativeImg || src.startsWith('data:') || src.startsWith('blob:')) {
        return (
          <img
            src={src}
            alt={alt || ''}
            className="aspect-square h-full w-full object-cover"
            onError={() => setHasError(true)}
            loading="lazy"
          />
        );
      }

      // Use Next.js Image for optimized loading
      return (
        <Image
          src={src}
          alt={alt || ''}
          width={pixelSize}
          height={pixelSize}
          className="aspect-square h-full w-full object-cover"
          onError={() => setHasError(true)}
          unoptimized={src.startsWith('http')} // Skip optimization for external URLs
        />
      );
    };

    return (
      <span
        ref={ref}
        className={cn(avatarVariants({ size }), className)}
        {...props}
      >
        {renderImage()}
      </span>
    );
  }
);
Avatar.displayName = 'Avatar';

export interface AvatarGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  max?: number;
  size?: 'xs' | 'sm' | 'default' | 'lg' | 'xl';
  children: React.ReactNode;
}

const AvatarGroup = React.forwardRef<HTMLDivElement, AvatarGroupProps>(
  ({ className, max = 4, size = 'default', children, ...props }, ref) => {
    const childArray = React.Children.toArray(children);
    const displayChildren = childArray.slice(0, max);
    const remainingCount = childArray.length - max;

    return (
      <div
        ref={ref}
        className={cn('flex -space-x-2', className)}
        {...props}
      >
        {displayChildren.map((child, index) =>
          React.isValidElement(child)
            ? React.cloneElement(child as React.ReactElement<AvatarProps>, {
                key: index,
                size,
                className: cn(
                  'ring-2 ring-background',
                  (child as React.ReactElement<AvatarProps>).props.className
                ),
              })
            : child
        )}
        {remainingCount > 0 && (
          <span
            className={cn(
              avatarVariants({ size }),
              'flex items-center justify-center bg-muted font-medium text-muted-foreground ring-2 ring-background'
            )}
          >
            +{remainingCount}
          </span>
        )}
      </div>
    );
  }
);
AvatarGroup.displayName = 'AvatarGroup';

// Compatibility exports for pages using AvatarImage/AvatarFallback pattern
const AvatarImage = React.forwardRef<
  HTMLImageElement,
  React.ImgHTMLAttributes<HTMLImageElement>
>(({ className, ...props }, ref) => (
  <img
    ref={ref}
    className={cn('aspect-square h-full w-full object-cover', className)}
    {...props}
  />
));
AvatarImage.displayName = 'AvatarImage';

const AvatarFallback = React.forwardRef<
  HTMLSpanElement,
  React.HTMLAttributes<HTMLSpanElement>
>(({ className, ...props }, ref) => (
  <span
    ref={ref}
    className={cn(
      'flex h-full w-full items-center justify-center rounded-full bg-muted font-medium uppercase text-muted-foreground',
      className
    )}
    {...props}
  />
));
AvatarFallback.displayName = 'AvatarFallback';

export { Avatar, AvatarGroup, AvatarImage, AvatarFallback };
