"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.GET = GET;
const server_1 = require("next/server");
async function GET() {
    return server_1.NextResponse.json({
        name: 'EventRelay API',
        version: '2.0.0',
        status: 'operational',
        documentation: '/api/docs',
    });
}
//# sourceMappingURL=route.js.map