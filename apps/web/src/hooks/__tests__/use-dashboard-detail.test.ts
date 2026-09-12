import { vi, describe, it, expect } from 'vitest';
import { useDashboardDetail } from '../use-dashboard-detail';
import { useDashboardStore } from '@/store/dashboard-store';

vi.mock('@/store/dashboard-store', () => ({
  useDashboardStore: vi.fn(),
}));

describe('useDashboardDetail', () => {
  it('should return all required state from the store', () => {
    // We mock the implementation to simulate what zustand does
    // when selector functions are passed to it
    const mockStoreState = {
      searchQuery: 'test query',
      setSearchQuery: vi.fn(),
      performSearch: vi.fn(),
      searchResults: [{ id: '1', title: 'Result 1' }],
      searchLoading: true,
      dispatchToAgents: vi.fn(),
      refreshAgentStatus: vi.fn(),
    };

    (useDashboardStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector: (s: any) => any) => {
      return selector(mockStoreState);
    });

    const result = useDashboardDetail();

    expect(result.searchQuery).toBe('test query');
    expect(result.setSearchQuery).toBe(mockStoreState.setSearchQuery);
    expect(result.performSearch).toBe(mockStoreState.performSearch);
    expect(result.searchResults).toEqual(mockStoreState.searchResults);
    expect(result.searchLoading).toBe(true);
    expect(result.dispatchToAgents).toBe(mockStoreState.dispatchToAgents);
    expect(result.refreshAgentStatus).toBe(mockStoreState.refreshAgentStatus);
  });
});
