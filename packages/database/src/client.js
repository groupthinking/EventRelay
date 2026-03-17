"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.prisma = void 0;
const client_1 = require("@prisma/client");
const logger_1 = require("@repo/logger");
const logger = (0, logger_1.getLogger)({ name: 'database' });
exports.prisma = global.prisma ||
    new client_1.PrismaClient({
        log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
    });
if (process.env.NODE_ENV !== 'production') {
    global.prisma = exports.prisma;
}
// Graceful shutdown
process.on('beforeExit', async () => {
    logger.info('Disconnecting from database');
    await exports.prisma.$disconnect();
});
exports.default = exports.prisma;
//# sourceMappingURL=client.js.map