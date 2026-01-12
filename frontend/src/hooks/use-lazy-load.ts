'use client';

import { useEffect, useRef, useState, useCallback, type RefObject } from 'react';

interface UseIntersectionObserverOptions {
  /** Root element for intersection testing */
  root?: Element | null;
  /** Margin around the root */
  rootMargin?: string;
  /** Threshold(s) at which callback is invoked */
  threshold?: number | number[];
  /** Only trigger once */
  triggerOnce?: boolean;
  /** Initial state */
  initialInView?: boolean;
  /** Skip observation (useful for conditional lazy loading) */
  skip?: boolean;
}

interface UseIntersectionObserverReturn<T extends Element> {
  /** Ref to attach to the target element */
  ref: RefObject<T>;
  /** Whether the element is in view */
  inView: boolean;
  /** The IntersectionObserverEntry */
  entry: IntersectionObserverEntry | undefined;
}

/**
 * Hook for observing element visibility using Intersection Observer
 * 
 * @example
 * ```tsx
 * function LazyImage() {
 *   const { ref, inView } = useIntersectionObserver<HTMLDivElement>({
 *     triggerOnce: true,
 *     rootMargin: '100px',
 *   });
 * 
 *   return (
 *     <div ref={ref}>
 *       {inView && <img src="/heavy-image.jpg" alt="..." />}
 *     </div>
 *   );
 * }
 * ```
 */
export function useIntersectionObserver<T extends Element = HTMLDivElement>(
  options: UseIntersectionObserverOptions = {}
): UseIntersectionObserverReturn<T> {
  const {
    root = null,
    rootMargin = '0px',
    threshold = 0,
    triggerOnce = false,
    initialInView = false,
    skip = false,
  } = options;

  const ref = useRef<T>(null);
  const [inView, setInView] = useState(initialInView);
  const [entry, setEntry] = useState<IntersectionObserverEntry>();
  const hasTriggered = useRef(false);

  useEffect(() => {
    const element = ref.current;
    
    if (!element || skip) return;
    if (triggerOnce && hasTriggered.current) return;
    
    // Check if IntersectionObserver is supported
    if (typeof IntersectionObserver === 'undefined') {
      setInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        const isIntersecting = entry.isIntersecting;
        
        setInView(isIntersecting);
        setEntry(entry);
        
        if (isIntersecting && triggerOnce) {
          hasTriggered.current = true;
          observer.disconnect();
        }
      },
      { root, rootMargin, threshold }
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [root, rootMargin, threshold, triggerOnce, skip]);

  return { ref, inView, entry };
}

/**
 * Hook for lazy loading images
 * 
 * @example
 * ```tsx
 * function LazyImage({ src, alt }: { src: string; alt: string }) {
 *   const { ref, shouldLoad, isLoaded, onLoad } = useLazyImage();
 * 
 *   return (
 *     <div ref={ref} className={cn('transition-opacity', isLoaded ? 'opacity-100' : 'opacity-0')}>
 *       {shouldLoad && (
 *         <img src={src} alt={alt} onLoad={onLoad} />
 *       )}
 *     </div>
 *   );
 * }
 * ```
 */
export function useLazyImage(options?: UseIntersectionObserverOptions) {
  const { ref, inView } = useIntersectionObserver<HTMLDivElement>({
    triggerOnce: true,
    rootMargin: '200px', // Start loading before it's in view
    ...options,
  });
  
  const [isLoaded, setIsLoaded] = useState(false);

  const onLoad = useCallback(() => {
    setIsLoaded(true);
  }, []);

  return {
    ref,
    shouldLoad: inView,
    isLoaded,
    onLoad,
  };
}

/**
 * Hook for lazy rendering components
 * Only renders children after element is in viewport
 * 
 * @example
 * ```tsx
 * function HeavySection() {
 *   const { ref, shouldRender } = useLazyRender();
 * 
 *   return (
 *     <div ref={ref} style={{ minHeight: 400 }}>
 *       {shouldRender ? <ExpensiveComponent /> : <Skeleton />}
 *     </div>
 *   );
 * }
 * ```
 */
export function useLazyRender(options?: UseIntersectionObserverOptions) {
  const { ref, inView } = useIntersectionObserver<HTMLDivElement>({
    triggerOnce: true,
    rootMargin: '50px',
    ...options,
  });

  return {
    ref,
    shouldRender: inView,
  };
}

/**
 * Hook for infinite scrolling
 * 
 * @example
 * ```tsx
 * function InfiniteList() {
 *   const [items, setItems] = useState([]);
 *   const [hasMore, setHasMore] = useState(true);
 * 
 *   const loadMore = async () => {
 *     const newItems = await fetchMoreItems();
 *     setItems(prev => [...prev, ...newItems]);
 *     setHasMore(newItems.length > 0);
 *   };
 * 
 *   const { ref, isLoading } = useInfiniteScroll({
 *     onLoadMore: loadMore,
 *     hasMore,
 *   });
 * 
 *   return (
 *     <div>
 *       {items.map(item => <ItemCard key={item.id} item={item} />)}
 *       <div ref={ref}>{isLoading && <Spinner />}</div>
 *     </div>
 *   );
 * }
 * ```
 */
export function useInfiniteScroll(options: {
  onLoadMore: () => Promise<void>;
  hasMore: boolean;
  rootMargin?: string;
}) {
  const { onLoadMore, hasMore, rootMargin = '100px' } = options;
  const [isLoading, setIsLoading] = useState(false);
  
  const { ref, inView } = useIntersectionObserver<HTMLDivElement>({
    rootMargin,
    skip: !hasMore || isLoading,
  });

  useEffect(() => {
    if (inView && hasMore && !isLoading) {
      setIsLoading(true);
      onLoadMore().finally(() => setIsLoading(false));
    }
  }, [inView, hasMore, isLoading, onLoadMore]);

  return { ref, isLoading };
}

export default useIntersectionObserver;
