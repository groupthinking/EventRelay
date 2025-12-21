// Mock API service for testing
export const apiService = {
  async fetchVideos() {
    // Mock implementation for testing
    return { videos: [] };
  },

  async fetchVideoById(id: string) {
    // Mock implementation for testing
    return {
      id,
      title: 'Test Video',
      url: 'https://youtube.com/watch?v=test',
      thumbnail: 'test-thumbnail.jpg',
      duration: '10:00',
      views: '1000',
      uploadedAt: '2023-01-01'
    };
  },

  async createVideo(video: any) {
    // Mock implementation for testing
    return { id: 'new-1', ...video };
  },

  async updateVideo(id: string, video: any) {
    // Mock implementation for testing
    return { id, ...video };
  },

  async deleteVideo(id: string) {
    // Mock implementation for testing
    return { message: 'Video deleted successfully' };
  },

  async connectToMCPServer() {
    // Mock implementation for testing
    return {
      status: 'connected',
      server: 'mcp-server',
      version: '1.0.0'
    };
  },

  async sendMessageToMCP(message: any) {
    // Mock implementation for testing
    return { status: 'sent', messageId: 'msg-123' };
  }
};
