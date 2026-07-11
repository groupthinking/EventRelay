import 'server-only';

import type { NextAuthOptions } from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';

const allowedDomain = process.env.AUTH_ALLOWED_EMAIL_DOMAIN?.trim().toLowerCase();

/**
 * NextAuth configuration (Google OAuth by default).
 *
 * Required env to activate login-gating: NEXTAUTH_SECRET, NEXTAUTH_URL,
 *   GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET.
 * Optional: AUTH_ALLOWED_EMAIL_DOMAIN restricts sign-in to a single domain.
 *
 * To use a different identity provider, swap GoogleProvider here — the gating
 * in middleware.ts is provider-agnostic (it only checks for a valid session).
 */
export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_OAUTH_CLIENT_ID ?? '',
      clientSecret: process.env.GOOGLE_OAUTH_CLIENT_SECRET ?? '',
    }),
  ],
  session: { strategy: 'jwt' },
  secret: process.env.NEXTAUTH_SECRET,
  callbacks: {
    async signIn({ user }) {
      if (!allowedDomain) return true;
      const email = (user.email ?? '').toLowerCase();
      return email.endsWith('@' + allowedDomain);
    },
  },
};
