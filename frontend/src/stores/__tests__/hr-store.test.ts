import { useHRStore } from '../hr';
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

describe('hr-store', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useHRStore.getState().stats = null;
    useHRStore.getState().headcount = [];
    useHRStore.getState().expiringCerts = [];
  });

  it('fetchStats should update stats state', async () => {
    const mockStats = { 
      total_employees: 156, 
      open_positions: 8,
      pending_time_off: 12,
      expiring_certifications: 5,
      new_hires_this_month: 3,
      turnover_rate: 4.2
    };
    (apiClient.get as jest.Mock).mockResolvedValue(mockStats);

    await useHRStore.getState().fetchStats();

    expect(apiClient.get).toHaveBeenCalledWith('/hr/stats');
    expect(useHRStore.getState().stats).toEqual(mockStats);
  });

  it('fetchHeadcount should update headcount state', async () => {
    const mockHeadcount = [{ name: 'Ops', count: 50, percentage: 50 }];
    (apiClient.get as jest.Mock).mockResolvedValue(mockHeadcount);

    await useHRStore.getState().fetchHeadcount();

    expect(apiClient.get).toHaveBeenCalledWith('/hr/headcount');
    expect(useHRStore.getState().headcount).toEqual(mockHeadcount);
  });

  it('fetchExpiringCerts should update expiringCerts state', async () => {
    const mockCerts = [{ id: '1', employee: 'John', cert: 'Forklift', expires: '2 days', priority: 'high' }];
    (apiClient.get as jest.Mock).mockResolvedValue(mockCerts);

    await useHRStore.getState().fetchExpiringCerts();

    expect(apiClient.get).toHaveBeenCalledWith('/hr/expiring-certs');
    expect(useHRStore.getState().expiringCerts).toEqual(mockCerts);
  });
});
