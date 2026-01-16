import '@testing-library/jest-dom';

// Mock Next.js Image to avoid src parsing errors in tests
jest.mock('next/image', () => {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const React = require('react');
  return {
    __esModule: true,
    default: (props: any) => {
      const { unoptimized, priority, placeholder, blurDataURL, ...rest } = props;
      return React.createElement('img', rest);
    },
  };
});

// Mock next/link to behave like Next.js client navigation:
// prevent default browser navigation and delegate to router.push.
jest.mock('next/link', () => {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const React = require('react');
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { useRouter } = require('next/navigation');

  function toHrefString(href: unknown): string {
    if (typeof href === 'string') return href;
    if (href && typeof href === 'object' && 'pathname' in href && typeof href.pathname === 'string') {
      return href.pathname;
    }
    return '#';
  }

  return {
    __esModule: true,
    default: ({ href, onClick, children, ...rest }: any) => {
      const router = typeof useRouter === 'function' ? useRouter() : null;
      const hrefString = toHrefString(href);
      return React.createElement(
        'a',
        {
          href: hrefString,
          ...rest,
          onClick: (e: any) => {
            e?.preventDefault?.();
            onClick?.(e);
            router?.push?.(hrefString);
          },
        },
        children
      );
    },
  };
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock ResizeObserver
class ResizeObserverMock {
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
}

window.ResizeObserver = ResizeObserverMock;

// Mock IntersectionObserver
class IntersectionObserverMock {
  root: Element | null = null;
  rootMargin: string = '';
  thresholds: ReadonlyArray<number> = [];
  
  constructor(private callback: IntersectionObserverCallback) {}
  
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
  takeRecords = jest.fn();
}

window.IntersectionObserver = IntersectionObserverMock;

// Mock scrollTo
window.scrollTo = jest.fn();

// JSDOM does not implement full navigation. Some tests/components trigger
// anchor navigation side-effects; keep clicks functional without navigating.
const originalAnchorClick = HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click = function click(): void {
  const event = new MouseEvent('click', { bubbles: true, cancelable: true });
  event.preventDefault();
  this.dispatchEvent(event);
};

const preventAnchorNavigation = (e: MouseEvent) => {
  const target = e.target as Element | null;
  const anchor = target?.closest?.('a[href]') as HTMLAnchorElement | null;
  if (!anchor) return;

  const href = anchor.getAttribute('href');
  if (!href || href.startsWith('#')) return;

  e.preventDefault();
};

document.addEventListener('click', preventAnchorNavigation, true);

afterAll(() => {
  document.removeEventListener('click', preventAnchorNavigation, true);
  HTMLAnchorElement.prototype.click = originalAnchorClick;
});

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}));
