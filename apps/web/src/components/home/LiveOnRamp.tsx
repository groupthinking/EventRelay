import Nav from '@/components/Nav';
import HomePasteForm from '@/components/home/HomePasteForm';
import './live-onramp.css';

const STAGES = ['Transcript', 'Chapters', 'Keyframes', 'Tasks', 'Checks', 'Dispatch'] as const;

/** Short on-ramp: one claim, one URL field, one sample button. Everything else lives in Studio. */
export default function LiveOnRamp() {
  return (
    <main className="live-onramp" data-testid="live-onramp">
      <Nav />
      <section aria-labelledby="home-heading" className="live-onramp-hero">
        <p className="live-onramp-kicker">
          <span className="live-onramp-dot" aria-hidden="true" />
          Live Studio · Universal Video Action Intelligence
        </p>
        <h1 id="home-heading" className="live-onramp-title">
          Paste a video. <em>Watch it turn into work.</em>
        </h1>
        <p className="live-onramp-lede">
          UVAI builds a hashed Video Pack in front of you: transcript, chapters, keyframes, and
          timestamped tasks with proposed checks, ready to edit and dispatch.
        </p>
        <HomePasteForm variant="onramp" />
        <ol className="live-onramp-stages" aria-label="What Studio builds, in order">
          {STAGES.map((stage, index) => (
            <li key={stage} style={{ animationDelay: `${index * 0.35}s` }}>
              <span aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
              {stage}
            </li>
          ))}
        </ol>
        <p className="live-onramp-fineprint">
          Transcript quality varies by source. Checks stay proposed until they run.
        </p>
      </section>
    </main>
  );
}
