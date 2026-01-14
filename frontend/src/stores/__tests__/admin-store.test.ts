import { useAdminStore } from '../admin';
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

describe('admin-store', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAdminStore.setState({
      gates: [],
      approvals: [],
      templates: [],
      learningCadences: [],
      featureFlags: [],
      roles: [],
      isLoading: false,
      error: null,
    });
  });

  it('fetchGates should call API and update state', async () => {
    const mockGates = [{ id: '1', name: 'Gate 1', phase: 'Plan', order: 1 }];
    (apiClient.get as jest.Mock).mockResolvedValue({ items: mockGates });

    await useAdminStore.getState().fetchGates();

    expect(apiClient.get).toHaveBeenCalledWith('/admin/gates');
    expect(useAdminStore.getState().gates).toEqual(mockGates);
  });

  it('createApproval should call API and update state', async () => {
    const approvalData = { name: 'New Approval', type: 'quote' };
    const mockResponse = { id: 'new-id', ...approvalData };
    (apiClient.post as jest.Mock).mockResolvedValue(mockResponse);

    await useAdminStore.getState().createApproval(approvalData as any);

    expect(apiClient.post).toHaveBeenCalledWith('/admin/approvals', approvalData);
    expect(useAdminStore.getState().approvals).toContainEqual(mockResponse);
  });

  it('updateTemplate should call API and update state', async () => {
    const templateId = '1';
    const updates = { name: 'Updated Name' };
    const mockResponse = { id: templateId, name: 'Updated Name', type: 'a3' };
    (apiClient.patch as jest.Mock).mockResolvedValue(mockResponse);
    
    useAdminStore.setState({
      templates: [{ id: templateId, name: 'Old Name', type: 'a3' } as any]
    });

    await useAdminStore.getState().updateTemplate(templateId, updates);

    expect(apiClient.patch).toHaveBeenCalledWith(`/admin/templates/${templateId}`, updates);
    expect(useAdminStore.getState().templates[0].name).toBe('Updated Name');
  });

  it('deleteApproval should call API and update state', async () => {
    const approvalId = '1';
    (apiClient.delete as jest.Mock).mockResolvedValue({ success: true });
    
    useAdminStore.setState({
      approvals: [{ id: approvalId, name: 'To Delete' } as any]
    });

    await useAdminStore.getState().deleteApproval(approvalId);

    expect(apiClient.delete).toHaveBeenCalledWith(`/admin/approvals/${approvalId}`);
    expect(useAdminStore.getState().approvals).toHaveLength(0);
  });
});
