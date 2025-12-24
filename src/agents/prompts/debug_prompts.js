import { promptManager } from './src/utils/promptManager.js';
import './src/prompts/LearningAgentPrompts.js';

console.log('🔍 Debugging Prompt Manager...');
console.log('Total prompts:', promptManager.prompts.size);
console.log('Available prompts:', Array.from(promptManager.prompts.keys()));

try {
  const testPrompt = promptManager.getPrompt('VIDEO_TRANSCRIPTION', 'latest', {
    title: 'Test',
    description: 'Test',
    duration: 'PT5M',
    complexity: 'low',
    targetLength: '1000 words'
  });
  console.log('✅ Prompt retrieval successful:', testPrompt.name, testPrompt.version);
} catch (error) {
  console.log('❌ Prompt retrieval failed:', error.message);
  console.log('❌ Error details:', error);
}