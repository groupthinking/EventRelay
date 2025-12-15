# @repo/config

Type-safe environment configuration with Zod validation.

## Features

- ✅ **Type Safety**: Zod schema validation
- ✅ **Runtime Validation**: Catches missing/invalid env vars at startup
- ✅ **Auto-completion**: Full TypeScript support
- ✅ **Constants**: Centralized configuration values

## Usage

### Environment Variables

```typescript
import { env, isDevelopment, isProduction } from '@repo/config';

// Type-safe access to env vars
const supabaseUrl = env.NEXT_PUBLIC_SUPABASE_URL;
const apiKey = env.ANTHROPIC_API_KEY;

// Runtime checks
if (isDevelopment) {
  console.log('Running in development mode');
}
```

### Constants

```typescript
import {
  APP_NAME,
  API_PREFIX,
  CACHE_TTL,
  RATE_LIMITS,
  RETRY_CONFIG,
} from '@repo/config';

// Use in your application
const cacheKey = `${APP_NAME}:user:${userId}`;
const ttl = CACHE_TTL.MEDIUM;

// Rate limiting
const limit = RATE_LIMITS.AUTHENTICATED.requests;
```

## Setup

1. Copy `.env.example` to `.env` in your app root:

```bash
cp packages/config/.env.example .env
```

2. Fill in your environment variables

3. The config package will validate on startup:

```typescript
import '@repo/config'; // Validates env on import

// Or explicitly validate
import { env } from '@repo/config';
```

## Adding New Environment Variables

1. Update `src/env.ts`:

```typescript
const envSchema = z.object({
  // ... existing vars

  // Add your new variable
  MY_NEW_VAR: z.string().min(1),
});
```

2. Update `.env.example`

3. TypeScript will now require this variable

## Environment Variable Types

- **Public** (`NEXT_PUBLIC_*`): Exposed to browser
- **Private**: Server-only, never sent to browser
- **Optional** (`.optional()`): Not required
- **With Default** (`.default(value)`): Fallback value

## Validation

The package will throw an error on startup if:
- Required variables are missing
- Variables don't match the schema (wrong type, invalid URL, etc.)

```typescript
// ❌ Invalid environment variables:
// {
//   "_errors": [],
//   "DATABASE_URL": {
//     "_errors": ["Required"]
//   }
// }
```

## Best Practices

1. **Never commit `.env`**: Add to `.gitignore`
2. **Use Vercel for secrets**: Set in dashboard for production
3. **Rotate keys regularly**: Update in all environments
4. **Type everything**: Use Zod for validation
5. **Document variables**: Update `.env.example`

## Vercel Deployment

Set environment variables in Vercel dashboard:

```bash
# Or use Vercel CLI
vercel env add DATABASE_URL
vercel env add ANTHROPIC_API_KEY
```

## Resources

- [Zod Documentation](https://zod.dev/)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)
- [Next.js Environment Variables](https://nextjs.org/docs/basic-features/environment-variables)
