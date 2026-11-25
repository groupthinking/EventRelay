/** Google recommends provider-managed sampling for Gemini 3 and newer. */
export function geminiSampling(model: string, temperature: number): { temperature?: number } {
  const match = /^gemini-(\d+)(?:[.-].*)?$/.exec(model.trim().toLowerCase().split('/').pop() ?? '');
  return match && Number(match[1]) >= 3 ? {} : { temperature };
}
