import 'server-only';

import type { NextAuthOptions } from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';
import { PrismaAdapter } from '@auth/prisma-adapter';
import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

function getPrisma(): PrismaClient | undefined {
  if (!process.env.DATABASE_URL) return undefined;
  if (!globalForPrisma.prisma) {
    globalForPrisma.prisma = new PrismaClient();
  }
  return globalForPrisma.prisma;
}

const allowedDomain = process.env.AUTH_ALLOWED_EMAIL_DOMAIN?.trim().toLowerCase();
const prisma = getPrisma();

/**
 * NextAuth configuration (Google OAuth by default).
 *
 * Required env to activate login-gating: NEXTAUTH_SECRET, NEXTAUTH_URL,
 *   GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET.
 * Optional: AUTH_ALLOWED_EMAIL_DOMAIN restricts sign-in to a single domain.
 * Optional: DATABASE_URL enables database-backed sessions via PrismaAdapter.
 *
 * To use a different identity provider, swap GoogleProvider here — the gating
 * in middleware.ts is provider-agnostic (it only checks for a valid session).
 */
export const authOptions: NextAuthOptions = {
  adapter: prisma ? PrismaAdapter(prisma) : undefined,
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_OAUTH_CLIENT_ID ?? '',
      clientSecret: process.env.GOOGLE_OAUTH_CLIENT_SECRET ?? '',
    }),
  ],
  session: { strategy: prisma ? 'database' : 'jwt' },
  secret: process.env.NEXTAUTH_SECRET,
  callbacks: {
    async signIn({ user }) {
      if (!allowedDomain) return true;
      const email = (user.email ?? '').toLowerCase();
      return email.endsWith('@' + allowedDomain);
    },
  },
};
