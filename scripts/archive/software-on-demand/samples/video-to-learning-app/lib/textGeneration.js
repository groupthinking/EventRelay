"use strict";
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
/* tslint:disable */
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateText = generateText;
const genai_1 = require("@google/genai");
const GEMINI_API_KEY = globalThis.process.env.GEMINI_API_KEY || globalThis.process.env.GEMINI_API_KEY;
/**
 * Generate text content using the Gemini API, optionally including video data.
 *
 * @param options - Configuration options for the generation request.
 * @returns The response from the Gemini API.
 */
async function generateText(options) {
    const { modelName, prompt, videoUrl, temperature = 0.75 } = options;
    if (!GEMINI_API_KEY) {
        throw new Error('Gemini API key is missing or empty');
    }
    const ai = new genai_1.GoogleGenAI({ apiKey: GEMINI_API_KEY });
    const parts = [{ text: prompt }];
    if (videoUrl) {
        try {
            parts.push({
                fileData: {
                    mimeType: 'video/mp4',
                    fileUri: videoUrl,
                },
            });
        }
        catch (error) {
            console.error('Error processing video input:', error);
            throw new Error(`Failed to process video input from URL: ${videoUrl}`);
        }
    }
    const generationConfig = {
        temperature,
    };
    const request = {
        model: modelName,
        contents: [{ role: 'user', parts }],
        config: generationConfig,
    };
    try {
        const response = await ai.models.generateContent(request);
        // Check for prompt blockage
        if (response.promptFeedback?.blockReason) {
            throw new Error(`Content generation failed: Prompt blocked (reason: ${response.promptFeedback.blockReason})`);
        }
        // Check for response blockage
        if (!response.candidates || response.candidates.length === 0) {
            throw new Error('Content generation failed: No candidates returned.');
        }
        const firstCandidate = response.candidates[0];
        // Check for finish reasons other than STOP
        if (firstCandidate.finishReason &&
            firstCandidate.finishReason !== genai_1.FinishReason.STOP) {
            if (firstCandidate.finishReason === genai_1.FinishReason.SAFETY) {
                throw new Error('Content generation failed: Response blocked due to safety settings.');
            }
            else {
                throw new Error(`Content generation failed: Stopped due to ${firstCandidate.finishReason}.`);
            }
        }
        return response.text;
    }
    catch (error) {
        console.error('An error occurred during Gemini API call or response processing:', error);
        throw error;
    }
}
//# sourceMappingURL=textGeneration.js.map