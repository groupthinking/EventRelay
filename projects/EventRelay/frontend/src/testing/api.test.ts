import { apiService } from '../testing/__mocks__/api';

describe('API Service', () => {
  describe('fetchVideos', () => {
    test('fetches videos successfully', async () => {
      const result = await apiService.fetchVideos();
      expect(result).toEqual({ videos: [] });
    });
  });

  describe('fetchVideoById', () => {
    test('fetches video by id successfully', async () => {
      const result = await apiService.fetchVideoById('test-1');
      expect(result).toEqual({
        id: 'test-1',
        title: 'Test Video',
        url: 'https://youtube.com/watch?v=test',
        thumbnail: 'test-thumbnail.jpg',
        duration: '10:00',
        views: '1000',
        uploadedAt: '2023-01-01'
      });
    });
  });

  describe('createVideo', () => {
    test('creates video successfully', async () => {
      const newVideo = {
        title: 'New Video',
        url: 'https://youtube.com/watch?v=new',
        thumbnail: 'new-thumbnail.jpg',
        duration: '15:00',
        views: '500',
        uploadedAt: '2023-01-02'
      };

      const result = await apiService.createVideo(newVideo);
      expect(result).toEqual({ id: 'new-1', ...newVideo });
    });
  });

  describe('updateVideo', () => {
    test('updates video successfully', async () => {
      const updatedVideo = {
        title: 'Updated Video',
        url: 'https://youtube.com/watch?v=test1',
        thumbnail: 'updated-thumbnail.jpg',
        duration: '12:00',
        views: '1500',
        uploadedAt: '2023-01-01'
      };

      const result = await apiService.updateVideo('test-1', updatedVideo);
      expect(result).toEqual({ id: 'test-1', ...updatedVideo });
    });
  });

  describe('deleteVideo', () => {
    test('deletes video successfully', async () => {
      const result = await apiService.deleteVideo('test-1');
      expect(result).toEqual({ message: 'Video deleted successfully' });
    });
  });

  describe('MCP Integration', () => {
    test('connects to MCP server successfully', async () => {
      const result = await apiService.connectToMCPServer();
      expect(result).toEqual({
        status: 'connected',
        server: 'mcp-server',
        version: '1.0.0'
      });
    });

    test('sends message to MCP server', async () => {
      const message = { type: 'analysis', content: 'Test message' };
      const result = await apiService.sendMessageToMCP(message);
      expect(result).toEqual({ status: 'sent', messageId: 'msg-123' });
    });
  });
});
