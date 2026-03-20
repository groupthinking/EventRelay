"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const Fetcher_1 = require("./Fetcher");
const jsdom_1 = require("jsdom");
const turndown_1 = __importDefault(require("turndown"));
global.fetch = jest.fn();
jest.mock("jsdom");
jest.mock("turndown");
describe("Fetcher", () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });
    const mockRequest = {
        url: "https://example.com",
        headers: { "Custom-Header": "Value" },
    };
    const mockHtml = `
    <html>
      <head>
        <title>Test Page</title>
        <script>console.log('This should be removed');</script>
        <style>body { color: red; }</style>
      </head>
      <body>
        <h1>Hello World</h1>
        <p>This is a test paragraph.</p>
      </body>
    </html>
  `;
    describe("html", () => {
        it("should return the raw HTML content", async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                text: jest.fn().mockResolvedValueOnce(mockHtml),
            });
            const result = await Fetcher_1.Fetcher.html(mockRequest);
            expect(result).toEqual({
                content: [{ type: "text", text: mockHtml }],
                isError: false,
            });
        });
        it("should handle errors", async () => {
            fetch.mockRejectedValueOnce(new Error("Network error"));
            const result = await Fetcher_1.Fetcher.html(mockRequest);
            expect(result).toEqual({
                content: [
                    {
                        type: "text",
                        text: "Failed to fetch https://example.com: Network error",
                    },
                ],
                isError: true,
            });
        });
    });
    describe("json", () => {
        it("should parse and return JSON content", async () => {
            const mockJson = { key: "value" };
            fetch.mockResolvedValueOnce({
                ok: true,
                json: jest.fn().mockResolvedValueOnce(mockJson),
            });
            const result = await Fetcher_1.Fetcher.json(mockRequest);
            expect(result).toEqual({
                content: [{ type: "text", text: JSON.stringify(mockJson) }],
                isError: false,
            });
        });
        it("should handle errors", async () => {
            fetch.mockRejectedValueOnce(new Error("Invalid JSON"));
            const result = await Fetcher_1.Fetcher.json(mockRequest);
            expect(result).toEqual({
                content: [
                    {
                        type: "text",
                        text: "Failed to fetch https://example.com: Invalid JSON",
                    },
                ],
                isError: true,
            });
        });
    });
    describe("txt", () => {
        it("should return plain text content without HTML tags, scripts, and styles", async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                text: jest.fn().mockResolvedValueOnce(mockHtml),
            });
            const mockTextContent = "Hello World This is a test paragraph.";
            // @ts-expect-error Mocking JSDOM
            jsdom_1.JSDOM.mockImplementationOnce(() => ({
                window: {
                    document: {
                        body: {
                            textContent: mockTextContent,
                        },
                        getElementsByTagName: jest.fn().mockReturnValue([]),
                    },
                },
            }));
            const result = await Fetcher_1.Fetcher.txt(mockRequest);
            expect(result).toEqual({
                content: [{ type: "text", text: mockTextContent }],
                isError: false,
            });
        });
        it("should handle errors", async () => {
            fetch.mockRejectedValueOnce(new Error("Parsing error"));
            const result = await Fetcher_1.Fetcher.txt(mockRequest);
            expect(result).toEqual({
                content: [
                    {
                        type: "text",
                        text: "Failed to fetch https://example.com: Parsing error",
                    },
                ],
                isError: true,
            });
        });
    });
    describe("markdown", () => {
        it("should convert HTML to markdown", async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                text: jest.fn().mockResolvedValueOnce(mockHtml),
            });
            const mockMarkdown = "# Hello World\n\nThis is a test paragraph.";
            turndown_1.default.mockImplementationOnce(() => ({
                turndown: jest.fn().mockReturnValueOnce(mockMarkdown),
            }));
            const result = await Fetcher_1.Fetcher.markdown(mockRequest);
            expect(result).toEqual({
                content: [{ type: "text", text: mockMarkdown }],
                isError: false,
            });
        });
        it("should handle errors", async () => {
            fetch.mockRejectedValueOnce(new Error("Conversion error"));
            const result = await Fetcher_1.Fetcher.markdown(mockRequest);
            expect(result).toEqual({
                content: [
                    {
                        type: "text",
                        text: "Failed to fetch https://example.com: Conversion error",
                    },
                ],
                isError: true,
            });
        });
    });
    describe("error handling", () => {
        it("should handle non-OK responses", async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 404,
            });
            const result = await Fetcher_1.Fetcher.html(mockRequest);
            expect(result).toEqual({
                content: [
                    {
                        type: "text",
                        text: "Failed to fetch https://example.com: HTTP error: 404",
                    },
                ],
                isError: true,
            });
        });
        it("should handle unknown errors", async () => {
            fetch.mockRejectedValueOnce("Unknown error");
            const result = await Fetcher_1.Fetcher.html(mockRequest);
            expect(result).toEqual({
                content: [
                    {
                        type: "text",
                        text: "Failed to fetch https://example.com: Unknown error",
                    },
                ],
                isError: true,
            });
        });
    });
});
//# sourceMappingURL=Fetcher.test.js.map