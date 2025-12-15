import { PrismaClient } from '@prisma/client';
import { getLogger } from '@repo/logger';

const logger = getLogger({ name: 'database' });

declare global {
  var prisma: PrismaClient | undefined;
}

export const prisma =
  global.prisma ||
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
  });

if (process.env.NODE_ENV !== 'production') {
  global.prisma = prisma;
}

// Graceful shutdown
process.on('beforeExit', async () => {
  logger.info('Disconnecting from database');
  await prisma.$disconnect();
});

export default prisma;
