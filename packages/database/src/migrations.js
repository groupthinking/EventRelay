"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.runMigrations = runMigrations;
exports.checkDatabaseConnection = checkDatabaseConnection;
const client_1 = require("./client");
const logger_1 = require("@repo/logger");
const logger = (0, logger_1.getLogger)({ name: 'migrations' });
async function runMigrations() {
    try {
        logger.info('Running database migrations');
        // Prisma handles migrations via CLI
        // This is for application-level data migrations
        logger.info('Migrations completed');
        return { success: true };
    }
    catch (error) {
        logger.error('Migration failed', error);
        throw error;
    }
}
async function checkDatabaseConnection() {
    try {
        await client_1.prisma.$queryRaw `SELECT 1`;
        logger.info('Database connection successful');
        return true;
    }
    catch (error) {
        logger.error('Database connection failed', error);
        return false;
    }
}
//# sourceMappingURL=migrations.js.map