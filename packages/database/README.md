# @repo/database

Prisma ORM + Supabase PostgreSQL database package.

## Features

- ✅ **Prisma ORM**: Type-safe database access
- ✅ **Supabase**: Managed PostgreSQL + real-time + auth
- ✅ **Migrations**: Version-controlled schema changes
- ✅ **Seed Data**: Development data utilities
- ✅ **TypeScript**: Full type safety

## Setup

### 1. Create Supabase Project

```bash
# Visit https://supabase.com/dashboard
# Create new project and get connection details
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Fill in your Supabase credentials
```

### 3. Generate Prisma Client

```bash
npm run db:generate
```

### 4. Push Schema to Database

```bash
# Development (creates tables without migrations)
npm run db:push

# Production (runs migrations)
npm run db:migrate:prod
```

### 5. Seed Database

```bash
npm run db:seed
```

## Usage

### Basic Queries

```typescript
import { prisma } from '@repo/database';

// Create user
const user = await prisma.user.create({
  data: {
    email: 'user@example.com',
    name: 'John Doe',
  },
});

// Find users
const users = await prisma.user.findMany({
  where: {
    emailVerified: { not: null },
  },
  include: {
    sessions: true,
  },
});

// Update user
await prisma.user.update({
  where: { id: user.id },
  data: { name: 'Jane Doe' },
});
```

### With Supabase Real-time

```typescript
import { supabase } from '@repo/database';

// Subscribe to table changes
const subscription = supabase
  .channel('users')
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'users',
  }, (payload) => {
    console.log('Change received!', payload);
  })
  .subscribe();
```

### Server-side with Service Role

```typescript
import { getServerSupabase } from '@repo/database';

// Use in API routes for admin operations
const supabase = getServerSupabase();

const { data, error } = await supabase
  .from('users')
  .select('*')
  .eq('id', userId);
```

## Database Scripts

```bash
# Generate Prisma client
npm run db:generate

# Push schema changes (dev)
npm run db:push

# Create migration
npm run db:migrate

# Deploy migrations (prod)
npm run db:migrate:prod

# Seed database
npm run db:seed

# Open Prisma Studio
npm run db:studio

# Reset database
npm run db:reset
```

## Schema

Current schema includes:
- **User**: User accounts
- **Session**: User sessions
- **ApiKey**: API authentication keys
- **AuditLog**: Activity logging

Add your models to `prisma/schema.prisma`:

```prisma
model Post {
  id        String   @id @default(cuid())
  title     String
  content   String?
  published Boolean  @default(false)
  authorId  String
  author    User     @relation(fields: [authorId], references: [id])
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@map("posts")
}
```

Then run:
```bash
npm run db:generate
npm run db:migrate
```

## Supabase Features

### Authentication

```typescript
import { supabase } from '@repo/database';

// Sign up
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'password',
});

// Sign in
await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password',
});

// Get session
const { data: { session } } = await supabase.auth.getSession();
```

### Storage

```typescript
// Upload file
const { data, error } = await supabase.storage
  .from('avatars')
  .upload('public/avatar.png', file);

// Get public URL
const { data } = supabase.storage
  .from('avatars')
  .getPublicUrl('public/avatar.png');
```

## Production Checklist

- [ ] Set `DATABASE_URL` and `DIRECT_URL` in production
- [ ] Run `db:migrate:prod` on deployment
- [ ] Enable Row Level Security (RLS) in Supabase
- [ ] Set up database backups
- [ ] Configure connection pooling
- [ ] Monitor query performance

## Resources

- [Prisma Docs](https://www.prisma.io/docs)
- [Supabase Docs](https://supabase.com/docs)
- [Prisma + Supabase Guide](https://supabase.com/docs/guides/integrations/prisma)
