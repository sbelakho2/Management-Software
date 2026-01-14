import { useExceptionsStore } from '../exceptions';
import { apiClient } from '@/api/client';

// Mock the API client
jest.mock('@/api/client', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  },
}));

describe('exceptions-store', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useExceptionsStore.getState().exceptions = [];
  });

  it('fetchExceptions should call API and update store', async () => {
    const mockExceptions = [
      { id: '1', title: 'Test Exception', severity: 'critical', status: 'open', category: 'andon' },
    ];
    (apiClient.get as jest.Mock).mockResolvedValue({ items: mockExceptions });

    await useExceptionsStore.getState().fetchExceptions();

    expect(apiClient.get).toHaveBeenCalledWith(expect.stringContaining('/exceptions'));
    expect(useExceptionsStore.getState().exceptions).toEqual(mockExceptions);
  });

  it('resolveException should call API and update state', async () => {
    const exceptionId = '1';
    const mockException = { id: '1', title: 'Test', status: 'resolved' };
    (apiClient.post as jest.Mock).mockResolvedValue(mockException);
    
    // Add it to store first
    useExceptionsStore.setState({ 
      exceptions: [{ id: '1', title: 'Test', status: 'open' } as any] 
    });

    await useExceptionsStore.getState().resolveException(exceptionId, 'fixed');

    expect(apiClient.post).toHaveBeenCalledWith(`/exceptions/${exceptionId}/resolve`, { 
      resolution_notes: 'fixed' 
    });
    expect(useExceptionsStore.getState().exceptions[0].status).toBe('resolved');
  });

  it('fetchStats should update stats state', async () => {
    const mockStats = { total_open: 5, critical_count: 2 };
    (apiClient.get as jest.Mock).mockResolvedValue(mockStats);

    await useExceptionsStore.getState().fetchStats();

    expect(apiClient.get).toHaveBeenCalledWith('/exceptions/summary');
    expect(useExceptionsStore.getState().stats).toEqual(mockStats);
  });
});
