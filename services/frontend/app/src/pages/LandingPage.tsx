import {
  LandingNav,
  HeroSection,
  StackOverview,
  FeaturesGrid,
  CTASection,
  LandingFooter,
} from "../shared/components/landing";
import { ConnectivityScene } from "../shared/components/landing/ConnectivityScene";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 relative overflow-hidden transition-colors duration-300">
      <ConnectivityScene />
      <LandingNav />
      <HeroSection />
      <StackOverview />
      <FeaturesGrid />
      <CTASection />
      <LandingFooter />
    </div>
  );
}
