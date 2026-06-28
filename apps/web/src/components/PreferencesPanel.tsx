'use client';

import { useState, useEffect, useCallback, useId } from 'react';
import { ChevronDown } from 'lucide-react';
import {
  type UserPreferences,
  DEFAULT_PREFERENCES,
  INDUSTRY_OPTIONS,
  COMPLEXITY_OPTIONS,
  TONE_OPTIONS,
  BUSINESS_MODEL_OPTIONS,
  loadPreferences,
  savePreferences,
} from '@/lib/preferences';

interface PreferencesPanelProps {
  onPreferencesChange?: (prefs: UserPreferences) => void;
}

/**
 * Provides a collapsible panel for editing and saving pipeline preferences.
 *
 * @param onPreferencesChange - Called whenever the preferences are updated in the UI.
 */
export default function PreferencesPanel({ onPreferencesChange }: PreferencesPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [prefs, setPrefs] = useState<UserPreferences>(DEFAULT_PREFERENCES);
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const baseId = useId();
  const industryId = `${baseId}-industry`;
  const businessModelId = `${baseId}-business-model`;
  const complexityId = `${baseId}-complexity`;
  const toneId = `${baseId}-tone`;
  const audienceId = `${baseId}-audience`;
  const contentId = `${baseId}-content`;

  // Load saved preferences on mount
  useEffect(() => {
    loadPreferences().then((saved) => {
      setPrefs(saved);
      setLoaded(true);
    });
  }, []);

  const handleChange = useCallback(
    (field: keyof UserPreferences, value: string) => {
      const updated = { ...prefs, [field]: value };
      setPrefs(updated);
      onPreferencesChange?.(updated);
    },
    [prefs, onPreferencesChange]
  );

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await savePreferences(prefs);
    } finally {
      setSaving(false);
    }
  }, [prefs]);

  const selectStyle = {
    background: 'rgba(25, 25, 31, 0.8)',
    border: '1px solid rgba(106, 242, 222, 0.15)',
    color: '#f8f5fd',
  };

  return (
    <div
      className="w-full"
      style={{
        background: 'rgba(37, 37, 44, 0.4)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
      }}
    >
      {/* Toggle header */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls={contentId}
        className="w-full flex items-center justify-between px-4 py-3 transition-colors hover:bg-white/[0.02] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40"
      >
        <span
          className="text-[10px] font-heading font-bold uppercase tracking-[0.2em]"
          style={{ color: 'rgba(248, 245, 253, 0.5)' }}
        >
          Pipeline Preferences
        </span>
        <ChevronDown
          className="h-4 w-4 transition-transform duration-200 motion-reduce:transition-none"
          style={{
            color: '#6af2de',
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
          }}
          aria-hidden="true"
        />
      </button>

      {/* Collapsible content */}
      {isOpen && loaded && (
        <div id={contentId} className="px-4 pb-4 space-y-4 animate-fade-in-up motion-reduce:animate-none">
          {/* Row 1: Industry + Business Model */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor={industryId}
                className="block text-[9px] font-heading uppercase tracking-[0.15em] mb-1.5"
                style={{ color: 'rgba(248, 245, 253, 0.35)' }}
              >
                Industry
              </label>
              <select
                id={industryId}
                value={prefs.industry}
                onChange={(e) => handleChange('industry', e.target.value)}
                className="w-full px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40 capitalize"
                style={selectStyle}
              >
                {INDUSTRY_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor={businessModelId}
                className="block text-[9px] font-heading uppercase tracking-[0.15em] mb-1.5"
                style={{ color: 'rgba(248, 245, 253, 0.35)' }}
              >
                Business Model
              </label>
              <select
                id={businessModelId}
                value={prefs.businessModel}
                onChange={(e) => handleChange('businessModel', e.target.value)}
                className="w-full px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40"
                style={selectStyle}
              >
                {BUSINESS_MODEL_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Row 2: Complexity + Tone */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor={complexityId}
                className="block text-[9px] font-heading uppercase tracking-[0.15em] mb-1.5"
                style={{ color: 'rgba(248, 245, 253, 0.35)' }}
              >
                Complexity
              </label>
              <select
                id={complexityId}
                value={prefs.complexity}
                onChange={(e) => handleChange('complexity', e.target.value)}
                className="w-full px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40"
                style={selectStyle}
              >
                {COMPLEXITY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor={toneId}
                className="block text-[9px] font-heading uppercase tracking-[0.15em] mb-1.5"
                style={{ color: 'rgba(248, 245, 253, 0.35)' }}
              >
                Tone
              </label>
              <select
                id={toneId}
                value={prefs.tone}
                onChange={(e) => handleChange('tone', e.target.value)}
                className="w-full px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40"
                style={selectStyle}
              >
                {TONE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Row 3: Target Audience */}
          <div>
            <label
              htmlFor={audienceId}
              className="block text-[9px] font-heading uppercase tracking-[0.15em] mb-1.5"
              style={{ color: 'rgba(248, 245, 253, 0.35)' }}
            >
              Target Audience
            </label>
            <input
              id={audienceId}
              type="text"
              value={prefs.targetAudience}
              onChange={(e) => handleChange('targetAudience', e.target.value)}
              placeholder="e.g. DevOps engineers at Series B startups"
              className="w-full px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40"
              style={selectStyle}
            />
          </div>

          {/* Save button */}
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              aria-busy={saving || undefined}
              className="px-4 py-1.5 font-heading font-bold text-[10px] tracking-wider uppercase transition-[transform,opacity] motion-reduce:transition-none focus:outline-none focus-visible:ring-2 focus-visible:ring-[#6af2de]/40 disabled:opacity-30 active:scale-95 motion-reduce:active:scale-100"
              style={{
                background: 'rgba(16, 183, 165, 0.9)',
                color: '#002b26',
              }}
            >
              {saving ? 'Saving…' : 'Save Preferences'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
