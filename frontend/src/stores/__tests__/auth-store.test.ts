import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuthStore } from '../auth-store';

// Mock the auth API
jest.mock('@/api', () => ({
  authApi: {
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
    me: jest.fn(),
  },
}));

import { authApi } from '@/api';

const mockAuthApi = authApi as jest.Mocked<typeof authApi>;

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset the store state before each test
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.logout();
    });
    jest.clearAllMocks();
  });

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const { result } = renderHook(() => useAuthStore());
      
      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  describe('login', () => {
    it('should set loading state during login', async () => {
      const mockUser = { id: '1', email: 'test@test.com', full_name: 'Test User' };
      mockAuthApi.login.mockResolvedValue({ user: mockUser, access_token: 'token' });
      
      const { result } = renderHook(() => useAuthStore());
      
      let loginPromise: Promise<void>;
      act(() => {
        loginPromise = result.current.login('test@test.com', 'password');
      });

      // Check loading state
      expect(result.current.isLoading).toBe(true);
      
      await act(async () => {
        await loginPromise;
      });
      
      expect(result.current.isLoading).toBe(false);
    });

    it('should set user and isAuthenticated on successful login', async () => {
      const mockUser = { id: '1', email: 'test@test.com', full_name: 'Test User' };
      mockAuthApi.login.mockResolvedValue({ user: mockUser, access_token: 'token' });
      
      const { result } = renderHook(() => useAuthStore());
      
      await act(async () => {
        await result.current.login('test@test.com', 'password');
      });
      
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.error).toBeNull();
    });

    it('should set error on failed login', async () => {
      mockAuthApi.login.mockRejectedValue(new Error('Invalid credentials'));
      
      const { result } = renderHook(() => useAuthStore());
      
      await act(async () => {
        try {
          await result.current.login('test@test.com', 'wrongpassword');
        } catch (e) {
          // Expected to throw
        }
      });
      
      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.error).toBe('Invalid credentials');
    });
  });

  describe('logout', () => {
    it('should clear user state on logout', async () => {
      const mockUser = { id: '1', email: 'test@test.com', full_name: 'Test User' };
      mockAuthApi.login.mockResolvedValue({ user: mockUser, access_token: 'token' });
      mockAuthApi.logout.mockResolvedValue(undefined);
      
      const { result } = renderHook(() => useAuthStore());
      
      // First login
      await act(async () => {
        await result.current.login('test@test.com', 'password');
      });
      
      expect(result.current.isAuthenticated).toBe(true);
      
      // Then logout
      await act(async () => {
        await result.current.logout();
      });
      
      expect(result.current.user).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('clearError', () => {
    it('should clear error state', async () => {
      mockAuthApi.login.mockRejectedValue(new Error('Some error'));
      
      const { result } = renderHook(() => useAuthStore());
      
      await act(async () => {
        try {
          await result.current.login('test@test.com', 'password');
        } catch (e) {
          // Expected
        }
      });
      
      expect(result.current.error).toBe('Some error');
      
      act(() => {
        result.current.clearError();
      });
      
      expect(result.current.error).toBeNull();
    });
  });
});
