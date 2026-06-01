const DEFAULT_CONTACT_EMAIL = 'viralnowsales@gmail.com';

export const CONTACT_EMAIL = (process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? '').trim() || DEFAULT_CONTACT_EMAIL;
