import { prisma } from './client';
import { getLogger } from '@repo/logger';

const logger = getLogger({ name: 'migrations' });

export async function runMigrations() {
  try {
    logger.info('Running database migrations');

    // Prisma handles migrations via CLI
    // This is for application-level data migrations

    logger.info('Migrations completed');
    return { success: true };
  } catch (error) {
    logger.error('Migration failed', error);
    throw error;
  }
}

export async function checkDatabaseConnection() {
  try {
    await prisma.$queryRaw`SELECT 1`;
    logger.info('Database connection successful');
    return true;
  } catch (error) {
    logger.error('Database connection failed', error);
    return false;
  }
}
