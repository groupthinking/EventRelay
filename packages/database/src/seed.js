"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const client_1 = require("./client");
const logger_1 = require("@repo/logger");
const logger = (0, logger_1.getLogger)({ name: 'seed' });
async function main() {
    logger.info('Starting database seed');
    // Create demo user
    const user = await client_1.prisma.user.upsert({
        where: { email: 'demo@example.com' },
        update: {},
        create: {
            email: 'demo@example.com',
            name: 'Demo User',
            emailVerified: new Date(),
        },
    });
    logger.info('Created demo user', { userId: user.id });
    // Create demo API key
    const apiKey = await client_1.prisma.apiKey.upsert({
        where: { key: 'demo_api_key_12345' },
        update: {},
        create: {
            name: 'Demo API Key',
            key: 'demo_api_key_12345',
            userId: user.id,
            expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000), // 1 year
        },
    });
    logger.info('Created demo API key', { apiKeyId: apiKey.id });
    logger.info('Database seed completed');
}
main()
    .catch((e) => {
    logger.error('Seed failed', e);
    process.exit(1);
})
    .finally(async () => {
    await client_1.prisma.$disconnect();
});
//# sourceMappingURL=seed.js.map