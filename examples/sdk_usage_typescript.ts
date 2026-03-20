/**
 * Example: Using the EventRelay TypeScript SDK
 *
 * This example demonstrates how to use the EventRelay SDK to:
 * 1. Process a YouTube video
 * 2. Extract events from the transcript
 * 3. Dispatch agents to handle events
 * 4. Monitor agent execution
 */

import { EventRelay } from '@groupthinking/eventrelay';
import type {
  VideoProcessJobRequest,
  VideoJobStatusResponse,
  EventExtractRequest,
  AgentDispatchRequest,
} from '@groupthinking/eventrelay';

// Initialize client
const client = new EventRelay({
  apiKey: process.env.EVENTRELAY_API_KEY,
  baseURL: process.env.EVENTRELAY_API_URL || 'https://api.uvai.io',
});

/**
 * Basic example: Process a video and extract events
 */
async function basicExample() {
  console.log('📹 Processing video...');

  // Step 1: Process video
  const job = await client.videos.process({
    video_url: 'https://youtube.com/watch?v=auJzb1D-fag',
    language: 'en',
    options: { enable_cache: true },
  });

  console.log(`✅ Job created: ${job.job_id}`);

  // Step 2: Poll for completion
  console.log('⏳ Waiting for processing to complete...');
  const status = await client.videos.waitForCompletion(job.job_id, {
    timeout: 300000, // 5 minutes
    pollInterval: 5000, // Check every 5 seconds
  });

  if (status.status === 'failed') {
    console.error(`❌ Processing failed: ${status.error}`);
    return;
  }

  console.log('✅ Processing complete!');
  console.log(`   Transcript length: ${status.transcript?.length || 0} characters`);

  // Step 3: Extract events
  console.log('\n🔍 Extracting events from transcript...');
  const events = await client.events.extract({
    transcript: status.transcript!,
    video_metadata: status.metadata,
  });

  console.log(`✅ Found ${events.events.length} events`);
  events.events.slice(0, 5).forEach((event, i) => {
    console.log(`   ${i + 1}. ${event.type}: ${event.description}`);
  });

  // Step 4: Dispatch agents
  console.log('\n🤖 Dispatching agents...');
  const agents = await Promise.all(
    events.events.slice(0, 3).map((event) =>
      client.agents.dispatch({
        event_type: event.type,
        payload: event.payload,
        priority: 1,
      })
    )
  );

  agents.forEach((agent) => {
    console.log(`   ✅ Agent ${agent.agent_id} dispatched: ${agent.status}`);
  });

  // Step 5: Monitor agent execution
  console.log('\n📊 Monitoring agent execution...');
  const finalStatuses = await Promise.all(
    agents.map((agent) => client.agents.waitForCompletion(agent.agent_id))
  );

  finalStatuses.forEach((status) => {
    console.log(`   Agent ${status.agent_id}: ${status.status}`);
  });

  console.log('\n🎉 All done!');
}

/**
 * Streaming example
 */
async function streamingExample() {
  console.log('💬 Streaming chat example...');

  const stream = await client.chat.stream({
    messages: [
      { role: 'user', content: 'Explain quantum computing in simple terms' },
    ],
  });

  for await (const chunk of stream) {
    process.stdout.write(chunk.content);
  }

  console.log('\n\n✅ Stream complete!');
}

/**
 * Pagination example
 */
async function paginationExample() {
  console.log('📄 Pagination example...');

  let videoCount = 0;

  // Auto-paginate through all videos
  for await (const video of client.videos.list()) {
    videoCount++;
    console.log(`   ${videoCount}. ${video.video_id}: ${video.title}`);

    // Stop after 10 for demo purposes
    if (videoCount >= 10) break;
  }

  console.log(`\n✅ Listed ${videoCount} videos`);
}

/**
 * Error handling example
 */
async function errorHandlingExample() {
  console.log('🔍 Error handling example...');

  try {
    // This might fail for various reasons
    await client.videos.process({
      video_url: 'https://youtube.com/watch?v=invalid',
    });
  } catch (error) {
    if (error instanceof EventRelay.AuthenticationError) {
      console.error('❌ Authentication failed:', error.message);
      console.error('   Please check your API key');
    } else if (error instanceof EventRelay.RateLimitError) {
      console.error('❌ Rate limited:', error.message);
      console.error(`   Retry after ${error.retryAfter} seconds`);
    } else if (error instanceof EventRelay.APIError) {
      console.error(`❌ API error (${error.status}):`, error.message);
      if (error.detail) {
        console.error(`   Details: ${error.detail}`);
      }
    } else {
      console.error('❌ Unexpected error:', error);
    }
  }
}

/**
 * Batch processing example
 */
async function batchProcessingExample() {
  console.log('📦 Batch processing example...');

  const videoUrls = [
    'https://youtube.com/watch?v=auJzb1D-fag',
    'https://youtube.com/watch?v=dQw4w9WgXcQ',
    'https://youtube.com/watch?v=9bZkp7q19f0',
  ];

  // Process multiple videos concurrently
  const jobs = await Promise.all(
    videoUrls.map((url) =>
      client.videos.process({
        video_url: url,
        language: 'en',
      })
    )
  );

  console.log(`✅ Created ${jobs.length} jobs`);

  // Wait for all to complete
  const statuses = await Promise.all(
    jobs.map((job) => client.videos.waitForCompletion(job.job_id))
  );

  const successful = statuses.filter((s) => s.status === 'complete').length;
  const failed = statuses.filter((s) => s.status === 'failed').length;

  console.log(`✅ Successful: ${successful}`);
  console.log(`❌ Failed: ${failed}`);
}

/**
 * Webhook integration example
 */
async function webhookExample() {
  console.log('🔔 Webhook example...');

  // Process video with webhook notification
  const job = await client.videos.process({
    video_url: 'https://youtube.com/watch?v=auJzb1D-fag',
    language: 'en',
    options: {
      webhook_url: 'https://your-app.com/webhooks/eventrelay',
      webhook_events: ['job.completed', 'job.failed'],
    },
  });

  console.log(`✅ Job created with webhook: ${job.job_id}`);
  console.log('   You will receive notifications at your webhook URL');
}

/**
 * Main function to run all examples
 */
async function main() {
  console.log('EventRelay SDK Examples\n' + '='.repeat(50) + '\n');

  // Check API key
  if (!process.env.EVENTRELAY_API_KEY) {
    console.error('❌ EVENTRELAY_API_KEY environment variable not set');
    console.error('   Set it with: export EVENTRELAY_API_KEY=your-key-here');
    process.exit(1);
  }

  try {
    console.log('\n1. Basic Example');
    console.log('-'.repeat(50));
    await basicExample();

    console.log('\n\n2. Streaming Example');
    console.log('-'.repeat(50));
    await streamingExample();

    console.log('\n\n3. Pagination Example');
    console.log('-'.repeat(50));
    await paginationExample();

    console.log('\n\n4. Error Handling Example');
    console.log('-'.repeat(50));
    await errorHandlingExample();

    console.log('\n\n5. Batch Processing Example');
    console.log('-'.repeat(50));
    await batchProcessingExample();

    console.log('\n\n6. Webhook Example');
    console.log('-'.repeat(50));
    await webhookExample();
  } catch (error) {
    console.error('Fatal error:', error);
    process.exit(1);
  }
}

// Run examples
if (require.main === module) {
  main().catch((error) => {
    console.error('Unhandled error:', error);
    process.exit(1);
  });
}

// Export for use in other modules
export {
  basicExample,
  streamingExample,
  paginationExample,
  errorHandlingExample,
  batchProcessingExample,
  webhookExample,
};
