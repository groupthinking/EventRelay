import { renderToStaticMarkup } from 'react-dom/server';

import {
  HostedSpecUnavailablePage,
  type HostedSpecUnavailableHealth,
} from '@/components/hosted/HostedSpecUnavailablePage';

/** Server-rendered enterprise Empty UI for /d when the compiled spec cannot be served. */
export function renderHostedSpecUnavailableHtml(
  videoId: string,
  health: HostedSpecUnavailableHealth,
): string {
  const markup = renderToStaticMarkup(
    <HostedSpecUnavailablePage videoId={videoId} health={health} />,
  );
  return `<!DOCTYPE html>${markup}`;
}
