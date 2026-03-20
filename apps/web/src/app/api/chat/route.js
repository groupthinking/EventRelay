"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.POST = POST;
const server_1 = require("next/server");
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
async function POST(request) {
    try {
        const body = await request.json();
        const response = await fetch(`${BACKEND_URL}/api/v1/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: body.query,
                video_url: body.video_url || '',
                video_id: body.video_id || '',
                conversation_history: body.history || [],
            }),
        });
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Chat API error:', response.status, errorText);
            return server_1.NextResponse.json({ answer: 'The AI assistant is temporarily unavailable. Please try again.' }, { status: response.status });
        }
        const data = await response.json();
        return server_1.NextResponse.json({
            answer: data.response || data.answer || data.message || 'No response generated.',
        });
    }
    catch (error) {
        console.error('Chat proxy error:', error);
        return server_1.NextResponse.json({ answer: 'Failed to connect to the AI assistant. Please ensure the backend is running.' }, { status: 502 });
    }
}
//# sourceMappingURL=route.js.map