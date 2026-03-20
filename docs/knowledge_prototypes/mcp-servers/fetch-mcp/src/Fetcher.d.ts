import { RequestPayload } from "./types.js";
export declare class Fetcher {
    private static _fetch;
    static html(requestPayload: RequestPayload): Promise<{
        content: {
            type: string;
            text: string;
        }[];
        isError: boolean;
    }>;
    static json(requestPayload: RequestPayload): Promise<{
        content: {
            type: string;
            text: string;
        }[];
        isError: boolean;
    }>;
    static txt(requestPayload: RequestPayload): Promise<{
        content: {
            type: string;
            text: any;
        }[];
        isError: boolean;
    }>;
    static markdown(requestPayload: RequestPayload): Promise<{
        content: {
            type: string;
            text: any;
        }[];
        isError: boolean;
    }>;
}
