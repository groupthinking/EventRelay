/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
export declare const getYouTubeVideoId: (url: string) => string | null;
export declare function validateYoutubeUrl(url: string): Promise<{
    isValid: boolean;
    error?: string;
}>;
export declare function getYoutubeEmbedUrl(url: string): string;
export declare function getYouTubeVideoTitle(url: string): Promise<any>;
