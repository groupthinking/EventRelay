import { ImageResponse } from 'next/og';

export const alt = 'UVAI turns verified video evidence into durable workflows';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: 'stretch',
          background: '#050508',
          color: '#f8f5fd',
          display: 'flex',
          flexDirection: 'column',
          fontFamily: 'Arial, sans-serif',
          height: '100%',
          justifyContent: 'space-between',
          padding: '72px 78px',
          position: 'relative',
          width: '100%',
        }}
      >
        <div
          style={{
            background: 'radial-gradient(circle at 50% 50%, rgba(106,242,222,0.18), rgba(5,5,8,0) 70%)',
            display: 'flex',
            height: 620,
            position: 'absolute',
            right: -120,
            top: -180,
            width: 620,
          }}
        />
        <div style={{ alignItems: 'center', display: 'flex', justifyContent: 'space-between' }}>
          <div style={{ alignItems: 'center', display: 'flex', fontSize: 30, fontWeight: 800, letterSpacing: 6 }}>
            UVAI
          </div>
          <div
            style={{
              border: '1px solid rgba(106,242,222,0.35)',
              color: '#6af2de',
              display: 'flex',
              fontSize: 16,
              fontWeight: 700,
              letterSpacing: 3,
              padding: '12px 18px',
              textTransform: 'uppercase',
            }}
          >
            Evidence first
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', maxWidth: 920 }}>
          <div style={{ color: '#6af2de', display: 'flex', fontSize: 20, fontWeight: 700, letterSpacing: 4, marginBottom: 20, textTransform: 'uppercase' }}>
            Video, verified transcript, durable workflow
          </div>
          <div style={{ display: 'flex', fontSize: 70, fontWeight: 800, letterSpacing: -3, lineHeight: 1.04 }}>
            Build from source evidence, not a model&apos;s best guess.
          </div>
        </div>

        <div style={{ alignItems: 'center', borderTop: '1px solid rgba(248,245,253,0.14)', display: 'flex', justifyContent: 'space-between', paddingTop: 24 }}>
          <div style={{ color: 'rgba(248,245,253,0.62)', display: 'flex', fontSize: 18 }}>
            Captions or speech-to-text required. Provenance included.
          </div>
          <div style={{ color: '#f8f5fd', display: 'flex', fontSize: 18, fontWeight: 700 }}>
            uvai.io
          </div>
        </div>
      </div>
    ),
    size,
  );
}
