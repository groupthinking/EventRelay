import 'server-only';

import type { NextAuthOptions } from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';

const allowedDomain = process.env.AUTH_ALLOWED_EMAIL_DOMAIN?.trim().toLowerCase();
const googleClientId = process.env.GOOGLE_OAUTH_CLIENT_ID?.trim() ?? '';
const googleClientSecret = process.env.GOOGLE_OAUTH_CLIENT_SECRET?.trim() ?? '';

/**
 * NextAuth configuration (Google OAuth by default).
 *
 * Required env to activate login-gating: NEXTAUTH_SECRET, NEXTAUTH_URL,
 *   GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET.
 * Optional: AUTH_ALLOWED_EMAIL_DOMAIN restricts sign-in to a single domain
 *   (e.g. `yourcompany.com` → only *@yourcompany.com).
 *
 * To use a different identity provider, swap GoogleProvider here — the gating
 * in proxy.ts is provider-agnostic (it only checks for a valid JWT session).
 */
function buildProviders(): NextAuthOptions['providers'] {
  if (!googleClientId || !googleClientSecret) {
    if (process.env.NODE_ENV === 'production') {
      console.error(
        '[auth] GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET missing — Google sign-in will fail.',
      );
    }
  }

  return [
    GoogleProvider({
      clientId: googleClientId,
      clientSecret: googleClientSecret,
      authorization: {
        params: {
          prompt: 'select_account',
          access_type: 'online',
          response_type: 'code',
        },
      },
    }),
  ];
}

function emailAllowed(email: string | null | undefined): boolean {
  if (!allowedDomain) return true;
  if (!email) return false;
  const normalized = email.trim().toLowerCase();
  // Exact domain match only (user@sub.domain.com does NOT match domain.com)
  return normalized.endsWith(`@${allowedDomain}`);
}

export const authOptions: NextAuthOptions = {
  providers: buildProviders(),
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
    updateAge: 24 * 60 * 60, // refresh session cookie once per day
  },
  secret: process.env.NEXTAUTH_SECRET,
  // Use secure cookie names on HTTPS (production / uvai.io)
  useSecureCookies: process.env.NEXTAUTH_URL?.startsWith('https://') ?? process.env.NODE_ENV === 'production',
  pages: {
    // Keep default NextAuth UI for reliability; /login rewrites into this flow.
    signIn: '/api/auth/signin',
    error: '/api/auth/error',
  },
  callbacks: {
    async signIn({ user, account }) {
      if (account?.provider === 'google' && !emailAllowed(user.email)) {
        console.warn(
          `[auth] sign-in denied for ${user.email ?? '(no email)'} — domain allowlist is @${allowedDomain}`,
        );
        return false;
      }
      return true;
    },

    async jwt({ token, user, account }) {
      if (user) {
        token.email = user.email;
        token.name = user.name;
        token.picture = user.image;
      }
      if (account?.provider) {
        token.provider = account.provider;
      }
      return token;
    },

    async session({ session, token }) {
      if (session.user) {
        session.user.email = (token.email as string | undefined) ?? session.user.email;
        session.user.name = (token.name as string | undefined) ?? session.user.name;
        session.user.image = (token.picture as string | undefined) ?? session.user.image;
      }
      return session;
    },

    /**
     * Prevent open redirects after OAuth. Only same-origin absolute URLs or
     * root-relative paths are allowed; everything else lands on /dashboard.
     */
    async redirect({ url, baseUrl }) {
      try {
        if (url.startsWith('/')) {
          // protocol-relative //evil.com
          if (url.startsWith('//')) return `${baseUrl}/dashboard`;
          return `${baseUrl}${url}`;
        }
        const target = new URL(url);
        const base = new URL(baseUrl);
        if (target.origin === base.origin) {
          return url;
        }
      } catch {
        // fall through
      }
      return `${baseUrl}/dashboard`;
    },
  },
  events: {
    async signIn({ user, account }) {
      if (process.env.NODE_ENV !== 'production') {
        console.info(`[auth] signIn ok provider=${account?.provider} email=${user.email ?? '?'}`);
      }
    },
  },
};
