const DEFAULT_CONTACT_EMAIL = 'viralnowsales@gmail.com';

export const CONTACT_EMAIL =
  process.env.NEXT_PUBLIC_CONTACT_EMAIL && process.env.NEXT_PUBLIC_CONTACT_EMAIL.trim().length > 0
    ? process.env.NEXT_PUBLIC_CONTACT_EMAIL
    : DEFAULT_CONTACT_EMAIL;
