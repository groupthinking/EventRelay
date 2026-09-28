import { defineConfig } from 'drizzle-kit';

export default defineConfig({
  dialect: 'postgresql',
  schema: './src/lib/runs/schema.ts',
  out: './drizzle/runs',
  dbCredentials: { url: process.env.RUN_DATABASE_URL_UNPOOLED ?? '' },
  strict: true,
});
