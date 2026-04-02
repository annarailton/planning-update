import { Link, useLocation } from "react-router-dom";
import { UserButton, useUser } from "@clerk/clerk-react";
import {
  LayoutDashboard,
  MessageSquare,
  Bot,
  Upload,
  Menu,
  X,
  Code2,
  Radio,
  Workflow,
  Layers,
  Map,
} from "lucide-react";
import { useState, useEffect, useMemo } from "react";
import { ThemeToggle } from "../ThemeToggle";
import { useFeatures } from "../../providers/FeaturesProvider";
import { config } from "../../lib/config";

function HeaderUserSection() {
  const { user } = useUser();

  return (
    <div className="flex items-center gap-3 pl-2">
      <div className="text-right hidden sm:block">
        <div className="text-sm font-semibold text-gray-900 dark:text-white">
          {user?.fullName || "User"}
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-500">Pro Plan</div>
      </div>
      <UserButton
        appearance={{
          elements: {
            avatarBox:
              "w-10 h-10 border-2 border-gray-200 dark:border-white/10 ring-2 ring-indigo-500/20",
          },
        }}
      />
    </div>
  );
}

function HeaderDevModeBadge() {
  return (
    <div className="rounded-full border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-amber-800">
      No auth
    </div>
  );
}

export function AppHeader() {
  const { isRedisEnabled, isTemporalEnabled } = useFeatures();
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navLinks = useMemo(() => {
    const links = [
      { name: "Overview", path: "/", icon: LayoutDashboard },
      { name: "Chat", path: "/chat", icon: MessageSquare },
      { name: "Agent", path: "/agent", icon: Bot },
      { name: "Realtime", path: "/realtime", icon: Radio },
      { name: "Files", path: "/file-upload", icon: Upload },
      { name: "Planning", path: "/planning-applications", icon: Map },
    ];

    // Only show Jobs if Redis is enabled
    if (isRedisEnabled) {
      links.push({ name: "Jobs", path: "/jobs", icon: Workflow });
    }

    // Only show Temporal if Temporal is enabled
    if (isTemporalEnabled) {
      links.push({ name: "Temporal", path: "/temporal-job", icon: Layers });
    }

    return links;
  }, [isRedisEnabled, isTemporalEnabled]);

  return (
    <header
      className={`fixed top-0 w-full z-50 transition-all duration-300 ${
        isScrolled
          ? "bg-white/80 dark:bg-slate-950/80 backdrop-blur-xl border-b border-gray-200 dark:border-white/5 py-3"
          : "bg-transparent py-5"
      }`}
    >
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between">
          {/* Logo Area */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="absolute -inset-1 bg-indigo-500 rounded-lg blur opacity-20 group-hover:opacity-40 transition-opacity" />
              <div className="relative w-10 h-10 bg-white/50 dark:bg-slate-900 border border-gray-200 dark:border-white/10 rounded-xl flex items-center justify-center shadow-xl">
                <Code2 className="w-6 h-6 text-indigo-600 dark:text-indigo-500" />
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold text-gray-900 dark:text-white leading-none tracking-tight">
                Tomoro
              </span>
              <span className="text-xs font-medium text-gray-500 dark:text-gray-500">
                Fullstack Kit
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1 p-1 bg-white/50 dark:bg-white/5 border border-gray-200 dark:border-white/5 rounded-full backdrop-blur-md">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`relative px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
                    isActive
                      ? "text-indigo-600 dark:text-white shadow-sm bg-white dark:bg-white/10"
                      : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-white/5"
                  }`}
                >
                  <link.icon
                    className={`w-4 h-4 ${isActive ? "text-indigo-600 dark:text-indigo-400" : "opacity-70"}`}
                  />
                  {link.name}
                </Link>
              );
            })}
          </nav>

          {/* Right Area */}
          <div className="flex items-center gap-4">
            <div className="hidden md:block">
              <ThemeToggle />
            </div>
            <div className="h-8 w-[1px] bg-gray-200 dark:bg-white/10 hidden md:block" />

            {config.isClerkConfigured ? (
              <HeaderUserSection />
            ) : (
              <HeaderDevModeBadge />
            )}

            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/5 rounded-lg transition-colors"
            >
              {isMobileMenuOpen ? <X /> : <Menu />}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

export default AppHeader;
