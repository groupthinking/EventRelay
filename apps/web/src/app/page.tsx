import HeroSection from '@/components/landing/HeroSection';
import BentoFeatures from '@/components/landing/BentoFeatures';
import WorkflowSection from '@/components/landing/WorkflowSection';
import TemplatesSection from '@/components/landing/TemplatesSection';
import DeveloperSection from '@/components/landing/DeveloperSection';
import LandingNav from '@/components/landing/LandingNav';
import LandingFooter from '@/components/landing/LandingFooter';
import ContactSection from '@/components/landing/ContactSection';

export default function Home() {
  return (
    <div className="min-h-screen bg-void text-ink overflow-x-hidden">
      <LandingNav />
      <main id="main">
        <HeroSection />
        <BentoFeatures />
        <WorkflowSection />
        <TemplatesSection />
        <DeveloperSection />
        <ContactSection />
      </main>
      <LandingFooter />
    </div>
  );
}
