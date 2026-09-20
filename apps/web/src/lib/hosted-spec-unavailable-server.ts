import 'server-only';

import { buildHostedSpecUnavailableHtmlDocument } from '@/lib/hosted-spec-unavailable-document';
import {
  hostedSpecHealthFromPackResolution,
  type HostedPackResolution,
  type HostedSpecHealthCheck,
} from '@/lib/compiled-spec-host';

/** Enterprise Empty UI HTML when the compiled spec cannot be served (never a raw gateway 503). */
export function hostedSpecUnavailableHtml(
  videoId: string,
  health: HostedSpecHealthCheck,
): string {
  return buildHostedSpecUnavailableHtmlDocument(videoId, health);
}

export function hostedLivePageUnavailableResponse(
  videoId: string,
  resolution: HostedPackResolution,
): Response {
  const health = hostedSpecHealthFromPackResolution(resolution);
  return new Response(hostedSpecUnavailableHtml(videoId, health), {
    status: 200,
    headers: {
      'content-type': 'text/html; charset=utf-8',
      'cache-control': 'no-store',
    },
  });
}
