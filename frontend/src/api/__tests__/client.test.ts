import { apiClient } from '../client';

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('ApiClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('initialization', () => {
    it('should export apiClient instance', () => {
      expect(apiClient).toBeDefined();
    });

    it('should have get method', () => {
      expect(typeof apiClient.get).toBe('function');
    });

    it('should have post method', () => {
      expect(typeof apiClient.post).toBe('function');
    });

    it('should have put method', () => {
      expect(typeof apiClient.put).toBe('function');
    });

    it('should have patch method', () => {
      expect(typeof apiClient.patch).toBe('function');
    });

    it('should have delete method', () => {
      expect(typeof apiClient.delete).toBe('function');
    });
  });

  describe('token management', () => {
    it('should have setToken method', () => {
      expect(typeof apiClient.setToken).toBe('function');
    });

    it('should have clearToken method', () => {
      expect(typeof apiClient.clearToken).toBe('function');
    });

    it('should store token in localStorage when setToken is called', () => {
      apiClient.setToken('test-token-123');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'test-token-123');
    });

    it('should remove token from localStorage when clearToken is called', () => {
      apiClient.clearToken();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token');
    });
  });

  describe('API methods interface', () => {
    it('should have loadToken method', () => {
      expect(typeof apiClient.loadToken).toBe('function');
    });

    it('should have refreshToken method', () => {
      expect(typeof apiClient.refreshToken).toBe('function');
    });
  });
});
