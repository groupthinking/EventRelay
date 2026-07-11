import { NextResponse } from 'next/server';
import { loadEmbeddings } from '@/lib/embedding-store';
import { generateEmbedding, cosineSimilarity } from '@/lib/gemini-embedding';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const videoId = searchParams.get('videoId');
    const query = searchParams.get('q');
    const limit = parseInt(searchParams.get('limit') || '3', 10);

    if (!videoId) {
      return NextResponse.json({ error: 'Missing videoId parameter' }, { status: 400 });
    }
    if (!query) {
      return NextResponse.json({ error: 'Missing q (search query) parameter' }, { status: 400 });
    }

    const videoData = await loadEmbeddings(videoId);
    if (!videoData || !videoData.chunks || videoData.chunks.length === 0) {
      return NextResponse.json(
        { error: 'No embeddings found for this video. Has it been processed through the pipeline yet?' },
        { status: 404 }
      );
    }

    // Embed the search query
    const queryEmbedding = await generateEmbedding(query);

    // Compute similarity across all chunks
    const scoredChunks = videoData.chunks.map(chunk => {
      const score = cosineSimilarity(queryEmbedding, chunk.embedding);
      return {
        start: chunk.start,
        duration: chunk.duration,
        text: chunk.text,
        score,
      };
    });

    // Sort descending by score
    scoredChunks.sort((a, b) => b.score - a.score);

    // Return the top K results
    const topChunks = scoredChunks.slice(0, limit);

    return NextResponse.json({
      success: true,
      videoId,
      query,
      results: topChunks,
    });
  } catch (error: any) {
    console.error('Video Search Error:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error during vector search' },
      { status: 500 }
    );
  }
}
