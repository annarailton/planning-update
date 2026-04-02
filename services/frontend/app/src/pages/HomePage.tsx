import {
  WelcomeSection,
  ComponentsGrid,
  ResourcesSection,
  QuickStartSection,
} from "../shared/components/home";
import { ConnectivityScene } from "../shared/components/landing/ConnectivityScene";

export function HomePage() {
  return (
    <div className="relative min-h-screen bg-gray-50 dark:bg-slate-950 overflow-hidden transition-colors duration-300">
      {/* 3D Background */}
      <ConnectivityScene />

      {/* Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <WelcomeSection />

        <div className="space-y-20">
          <ComponentsGrid />
          <QuickStartSection />
          <ResourcesSection />
        </div>

        {/* Footer */}
        <footer className="mt-20 py-8 border-t border-white/5 text-center text-gray-400 text-sm">
          <p>
            © {new Date().getFullYear()} Tomoro Fullstack Kit. Built with
            React, Three.js, and Motion.
          </p>
        </footer>
      </div>
    </div>
  );
}

export default HomePage;
