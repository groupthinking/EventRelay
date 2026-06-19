/**
 * User Preferences persistence layer.
 *
 * Stores user preferences that customize agent behavior — industry context,
 * complexity level, tone, and target audience get injected into every agent
 * prompt so outputs are relevant to the user's domain.
 *
 * Think of it like tuning a radio: same signal (video), but the preferences
 * determine which frequency you hear (healthcare vs fintech vs education).
 */

export interface UserPreferences {
  industry: string;
  complexity: 'simple' | 'moderate' | 'complex';
  tone: 'technical' | 'professional' | 'casual' | 'executive';
  targetAudience: string;
  businessModel: string;
}

export const DEFAULT_PREFERENCES: UserPreferences = {
  industry: 'technology',
  complexity: 'moderate',
  tone: 'professional',
  targetAudience: '',
  businessModel: 'SaaS',
};

const PREFERENCES_API = '/api/v1/preferences';

/**
 * Save user preferences to the backend (which persists to Supabase).
 */
export async function savePreferences(prefs: UserPreferences): Promise<void> {
  try {
    const res = await fetch(PREFERENCES_API, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prefs),
    });

    if (!res.ok) {
      throw new Error(`Preferences API returned ${res.status}`);
    }
  } catch (err) {
    console.warn('Preferences save failed:', err);
    // Cache in memory for current session
    cachedPreferences = { ...prefs };
  }
}

/**
 * Load user preferences from the backend.
 */
export async function loadPreferences(): Promise<UserPreferences> {
  try {
    const res = await fetch(PREFERENCES_API);
    if (!res.ok) return cachedPreferences || DEFAULT_PREFERENCES;

    const data = await res.json();
    const preferences = data.preferences || DEFAULT_PREFERENCES;
    cachedPreferences = preferences;
    return preferences;
  } catch {
    return cachedPreferences || DEFAULT_PREFERENCES;
  }
}

// In-memory cache for the current session
let cachedPreferences: UserPreferences | null = null;

export const INDUSTRY_OPTIONS = [
  'technology',
  'healthcare',
  'finance',
  'education',
  'e-commerce',
  'media',
  'manufacturing',
  'consulting',
  'government',
  'nonprofit',
  'other',
] as const;

export const COMPLEXITY_OPTIONS = [
  { value: 'simple', label: 'Simple — Single app, minimal infra' },
  { value: 'moderate', label: 'Moderate — Modular, containerized' },
  { value: 'complex', label: 'Complex — Microservices, distributed' },
] as const;

export const TONE_OPTIONS = [
  { value: 'technical', label: 'Technical — Developer-focused' },
  { value: 'professional', label: 'Professional — Business stakeholders' },
  { value: 'casual', label: 'Casual — Team internal' },
  { value: 'executive', label: 'Executive — C-suite summary' },
] as const;

export const BUSINESS_MODEL_OPTIONS = [
  'SaaS',
  'Marketplace',
  'API/Platform',
  'E-commerce',
  'Content/Media',
  'Consulting',
  'Open Source',
  'Other',
] as const;
