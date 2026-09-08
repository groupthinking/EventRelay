import 'server-only';

import type { NextAuthOptions } from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';

const allowedDomain = process.env.AUTH_ALLOWED_EMAIL_DOMAIN?.trim().toLowerCase();
const googleClientId = (
  process.env.GOOGLE_OAUTH_CLIENT_ID ||
  process.env.GOOGLE_CLIENT_ID ||
  ''
).trim();
const googleClientSecret = (
  process.env.GOOGLE_OAUTH_CLIENT_SECRET ||
  process.env.GOOGLE_CLIENT_SECRET ||
  ''
).trim();

/**
 * NextAuth configuration (Google OAuth by default).
 *
 * Required env to activate login-gating: NEXTAUTH_SECRET, NEXTAUTH_URL,
 *   GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET.
 * Also accepts NextAuth's common GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET names.
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
        '[auth] Google OAuth client id/secret missing — set GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET or GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET.',
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
  pages: {
    signIn: '/login',
  },
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
    updateAge: 24 * 60 * 60, // refresh session cookie once per day
  },
  secret: process.env.NEXTAUTH_SECRET,
  // Force secure cookies in production regardless of NEXTAUTH_URL's scheme so a
  // stray http:// value cannot silently downgrade cookie security; also enable
  // them whenever NEXTAUTH_URL is explicitly https (e.g. https previews).
  useSecureCookies:
    process.env.NODE_ENV === 'production' ||
    (process.env.NEXTAUTH_URL?.startsWith('https://') ?? false),
  callbacks: {
    async signIn({ user, account }) {
      // Enforce the domain allowlist for every provider, not just Google, so a
      // future provider (see comment above buildProviders) cannot bypass it.
      // emailAllowed() is a no-op when AUTH_ALLOWED_EMAIL_DOMAIN is unset.
      if (!emailAllowed(user.email)) {
        console.warn(
          `[auth] sign-in denied for ${user.email ?? '(no email)'} via ${account?.provider ?? 'unknown'} — domain allowlist is @${allowedDomain}`,
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
     * root-relative paths are allowed; everything else lands on the studio.
     */
    async redirect({ url, baseUrl }) {
      try {
        if (url.startsWith('/')) {
          // protocol-relative //evil.com
          if (url.startsWith('//')) return `${baseUrl}/`;
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
      return `${baseUrl}/`;
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
