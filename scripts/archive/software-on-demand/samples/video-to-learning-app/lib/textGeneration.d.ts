/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { SafetySetting } from '@google/genai';
interface GenerateTextOptions {
    modelName: string;
    prompt: string;
    videoUrl?: string;
    temperature?: number;
    safetySettings?: SafetySetting[];
}
/**
 * Generate text content using the Gemini API, optionally including video data.
 *
 * @param options - Configuration options for the generation request.
 * @returns The response from the Gemini API.
 */
export declare function generateText(options: GenerateTextOptions): Promise<string>;
export {};
