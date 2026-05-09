'use client';

import { useEffect } from 'react';
import { clsx } from 'clsx';
import type { RenderedVideo } from '@/lib/types';

interface RenderedVideoCardProps {
  renderedVideo: RenderedVideo;
  className?: string;
}

export default function RenderedVideoCard({
  renderedVideo,
  className,
}: RenderedVideoCardProps) {
  useEffect(() => {
    void import('@hyperframes/player');
  }, []);

  if (renderedVideo.status !== 'complete' || !renderedVideo.download_url) {
    return null;
  }

  return (
    <section
      className={clsx('p-6 rounded-2xl border border-white/[0.08] bg-white/[0.02]', className)}
    >
      <div className="flex items-center justify-between gap-4 mb-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-primary-400">
            Rendered Video
          </p>
          <h3 className="mt-2 text-xl font-heading font-bold text-white">
            HyperFrames Output
          </h3>
        </div>
        <a
          href={renderedVideo.download_url}
          target="_blank"
          rel="noreferrer"
          className="px-4 py-2 text-xs font-bold uppercase tracking-widest text-primary-400 border border-primary-500/20 bg-primary-500/10"
        >
          Open MP4
        </a>
      </div>

      <div className="overflow-hidden rounded-xl border border-white/[0.06] bg-black/30">
        <hyperframes-player
          src={renderedVideo.download_url}
          controls
          style={{ width: '100%', aspectRatio: '16 / 9', display: 'block' }}
        />
      </div>

      {renderedVideo.summary && (
        <p className="mt-4 text-sm text-white/55 leading-relaxed">{renderedVideo.summary}</p>
      )}
    </section>
  );
}
