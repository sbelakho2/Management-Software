import { renderHook, act } from '@testing-library/react';
import { usePipelineStore } from '../pipeline';
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

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('usePipelineStore', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { getState } = usePipelineStore;
    act(() => {
      // Manually reset state since persist might keep it
      getState().clearError();
    });
  });

  it('should have initial state', () => {
    const { result } = renderHook(() => usePipelineStore());
    expect(result.current.rfqs).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  describe('fetchRFQs', () => {
    it('should fetch RFQs and update stats', async () => {
      const mockRFQs = [
        {
          id: '1',
          rfq_number: 'RFQ-001',
          status: 'new',
          estimated_value: 1000,
          due_date: new Date(Date.now() + 86400000).toISOString(),
          received_date: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        {
          id: '2',
          rfq_number: 'RFQ-002',
          status: 'won',
          estimated_value: 2000,
          due_date: new Date(Date.now() - 86400000).toISOString(),
          received_date: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ];

      mockApiClient.get.mockResolvedValue({ items: mockRFQs });

      const { result } = renderHook(() => usePipelineStore());

      await act(async () => {
        await result.current.fetchRFQs();
      });

      expect(result.current.rfqs).toEqual(mockRFQs);
      expect(result.current.stats.totalRFQs).toBe(2);
      expect(result.current.stats.activeRFQs).toBe(1); // 'new' is active, 'won' is not
      expect(result.current.stats.totalValue).toBe(3000);
      expect(result.current.stats.overdueCount).toBe(1);
    });

    it('should handle fetch error', async () => {
      // Ensure cache is bypassed
      usePipelineStore.setState({ lastFetchedAt: null });
      
      mockApiClient.get.mockRejectedValue(new Error('Failed to fetch'));

      const { result } = renderHook(() => usePipelineStore());

      await act(async () => {
        await result.current.fetchRFQs();
      });

      expect(result.current.error).toBe('Failed to fetch');
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('updateRFQ', () => {
    it('should update RFQ and sync with state', async () => {
      const initialRFQ = { id: '1', rfq_number: 'RFQ-001', status: 'new' };
      const updatedRFQ = { id: '1', rfq_number: 'RFQ-001', status: 'quoting' };

      // Set initial state
      usePipelineStore.setState({ rfqs: [initialRFQ as any] });

      mockApiClient.patch.mockResolvedValue(updatedRFQ);

      const { result } = renderHook(() => usePipelineStore());

      await act(async () => {
        await result.current.updateRFQ('1', { status: 'quoting' });
      });

      expect(result.current.rfqs[0].status).toBe('quoting');
      expect(mockApiClient.patch).toHaveBeenCalledWith('/rfqs/1', { status: 'quoting' });
    });
  });
});
