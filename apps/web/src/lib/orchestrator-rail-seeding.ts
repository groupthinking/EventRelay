export function seededPromptDispatchKey(
  initialPrompt: string | null | undefined,
  promptNonce: string | null | undefined,
): string | null {
  const prompt = (initialPrompt || '').trim();
  if (!prompt) return null;
  return `${promptNonce || ''}::${prompt}`;
}
