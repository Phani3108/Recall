import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import HeroSection from '@/components/sections/HeroSection';
import ProblemSection from '@/components/sections/ProblemSection';
import ComparisonSection from '@/components/sections/ComparisonSection';
import VisionSection from '@/components/sections/VisionSection';
import AskSection from '@/components/sections/AskSection';
import PilotSection from '@/components/sections/PilotSection';
import FlowSection from '@/components/sections/FlowSection';
import HowItWorksSection from '@/components/sections/HowItWorksSection';
import GovernanceSection from '@/components/sections/GovernanceSection';
import IntegrationsSection from '@/components/sections/IntegrationsSection';
import CTASection from '@/components/sections/CTASection';

export default function LandingPage() {
  return (
    <>
      <Navbar />
      <main>
        {/* Screen 1: Hero */}
        <HeroSection />

        {/* Screen 2: The Problem */}
        <ProblemSection />

        {/* Screen 3: Bolt-on vs AI-Native */}
        <ComparisonSection />

        {/* Screen 4: The Vision — Connect → Understand → Act */}
        <VisionSection />

        {/* Screen 5: Ask — Enterprise AI Assistant */}
        <AskSection />

        {/* Screen 6: Pilot — Personal Delegation Agent */}
        <PilotSection />

        {/* Screen 7: Flow — AI-Native Work Management (teaser) */}
        <FlowSection />

        {/* Screen 8: How It Works — 4-step flow */}
        <HowItWorksSection />

        {/* Screen 9: Governance & Trust */}
        <GovernanceSection />

        {/* Screen 10: Integrations */}
        <IntegrationsSection />

        {/* Screen 11: CTA / Waitlist */}
        <CTASection />
      </main>
      <Footer />
    </>
  );
}
