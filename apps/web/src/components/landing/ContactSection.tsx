import ContactForm from '@/app/ContactForm';
import Link from 'next/link';

const REPO_URL = 'https://github.com/groupthinking/EventRelay';

export default function ContactSection() {
  return (
    <section
      id="contact"
      className="scroll-mt-24 py-24 px-8"
      style={{ background: 'rgba(8,10,14,0.98)' }}
    >
      <div className="max-w-[1440px] mx-auto">
        <div className="grid lg:grid-cols-2 gap-14 items-start">
          {/* Left: copy */}
          <div>
            <p className="text-xs tracking-[0.3em] uppercase font-bold mb-5" style={{ color: '#6af2de' }}>
              Inbound
            </p>
            <h2 className="font-heading text-[clamp(2rem,4vw,4rem)] font-black tracking-tighter leading-[0.95] text-ink mb-6">
              Send the workflow
              <br />
              you want automated.
            </h2>
            <p className="text-base text-ink/50 leading-relaxed mb-5 max-w-md">
              Share the type of video, the output you need, and where the result should go.
              The draft opens in your mail client for you to review before sending.
            </p>
            <p className="text-sm text-ink/30 leading-relaxed mb-10 max-w-sm">
              Privacy note: this page does not submit to our backend. The draft is handed directly to your local email app.
            </p>

            <div className="flex flex-wrap gap-3">
              <Link
                href="/"
                className="px-6 py-3 rounded-xl font-bold text-sm transition-all duration-200 active:scale-95"
                style={{ background: '#6af2de', color: '#021a18' }}
              >
                Open studio
              </Link>
              <a
                href={REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 rounded-xl font-bold text-sm transition-all duration-200 text-ink/60 hover:text-ink"
                style={{ border: '1px solid rgba(255,255,255,0.1)' }}
              >
                View source
              </a>
            </div>
          </div>

          {/* Right: form */}
          <ContactForm />
        </div>
      </div>
    </section>
  );
}
