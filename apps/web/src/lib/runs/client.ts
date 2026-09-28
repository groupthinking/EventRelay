import 'server-only';
import { Pool } from 'pg';
import { drizzle } from 'drizzle-orm/node-postgres';
import { attachDatabasePool } from '@vercel/functions';
import * as schema from './schema';
import { createRunStore } from './store';

let store: ReturnType<typeof createRunStore> | undefined;

/** Separate from the Video Pack store and Python runtime's DATABASE_URL. */
export function getRunStore() {
  if (store) return store;
  const connectionString = process.env.RUN_DATABASE_URL;
  if (!connectionString || !/^postgres(?:ql)?:\/\//.test(connectionString)) {
    throw new Error('RUN_DATABASE_URL must configure durable PostgreSQL storage');
  }
  const pool = new Pool({ connectionString, max: 5, connectionTimeoutMillis: 5000 });
  attachDatabasePool(pool);
  store = createRunStore(drizzle(pool, { schema }));
  return store;
}
