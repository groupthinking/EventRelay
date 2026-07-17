import { useDashboardStore } from '@/store/dashboard-store';

/** Search + agent dispatch state — only used in the video detail (SplitView) chunk. */
export function useDashboardDetail() {
  const searchQuery = useDashboardStore((s) => s.searchQuery);
  const setSearchQuery = useDashboardStore((s) => s.setSearchQuery);
  const performSearch = useDashboardStore((s) => s.performSearch);
  const searchResults = useDashboardStore((s) => s.searchResults);
  const searchLoading = useDashboardStore((s) => s.searchLoading);
  const dispatchToAgents = useDashboardStore((s) => s.dispatchToAgents);
  const refreshAgentStatus = useDashboardStore((s) => s.refreshAgentStatus);

  return {
    searchQuery,
    setSearchQuery,
    performSearch,
    searchResults,
    searchLoading,
    dispatchToAgents,
    refreshAgentStatus,
  };
}