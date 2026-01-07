import { render, screen } from '@testing-library/react';
import { PWAProvider } from '../pwa-provider';

// Mock the usePWA hook
jest.mock('@/hooks/use-pwa', () => ({
  usePWA: () => ({
    isSupported: true,
    isOnline: true,
    isUpdateAvailable: false,
    register: jest.fn(),
    skipWaiting: jest.fn(),
  }),
  useIsPWA: () => false,
}));

describe('PWAProvider', () => {
  it('should render children', () => {
    render(
      <PWAProvider>
        <div>Test Content</div>
      </PWAProvider>
    );
    
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('should be defined', () => {
    expect(PWAProvider).toBeDefined();
  });

  it('should not show any toasts when online and no updates', () => {
    render(
      <PWAProvider>
        <div>Test Content</div>
      </PWAProvider>
    );
    
    // No offline message when online
    expect(screen.queryByText("You're offline")).not.toBeInTheDocument();
    
    // Children should still render
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });
});
