// ── App.jsx — Shadow System Main Application ──

import { useState, useCallback } from "react";
import { useKeyboardShortcut } from "./hooks/useEffects";
import { PROMPT, SECTIONS } from "./data/prompt";

import BootScreen from "./components/BootScreen";
import { MatrixRain, ParticleField, ScanLines, AmbientOrbs } from "./components/BackgroundEffects";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import PromptPanel from "./components/PromptPanel";
import UsageGuide from "./components/UsageGuide";
import Footer from "./components/Footer";

import "./App.css";

export default function App() {
  const [booted, setBooted] = useState(false);
  const [activeSection, setActiveSection] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [copyFlash, setCopyFlash] = useState(false);

  const handleBootComplete = useCallback(() => {
    setBooted(true);
  }, []);

  const handleSectionClick = useCallback((sectionId) => {
    setActiveSection(sectionId);
    // Auto-clear after 2.5 seconds
    setTimeout(() => setActiveSection(null), 2500);
  }, []);

  const handleCopy = useCallback(() => {
    setCopyFlash(true);
    setTimeout(() => setCopyFlash(false), 300);
  }, []);

  // Keyboard shortcut: Ctrl+C copies prompt
  useKeyboardShortcut("c", () => {
    navigator.clipboard.writeText(PROMPT);
    handleCopy();
  }, { ctrl: true });

  // Keyboard shortcut: Escape closes mobile menu
  useKeyboardShortcut("Escape", () => {
    setMobileMenuOpen(false);
  });

  return (
    <>
      {/* Boot Sequence */}
      {!booted && <BootScreen onComplete={handleBootComplete} />}

      {/* Background Effects */}
      <MatrixRain />
      <ParticleField />
      <ScanLines />
      <AmbientOrbs />

      {/* Copy Flash Overlay */}
      {copyFlash && <div className="copy-flash-overlay" />}

      {/* Main Application */}
      <div className={`app ${booted ? "app-visible" : ""}`}>
        {/* Mobile Menu Button */}
        <button
          className="mobile-menu-btn"
          onClick={() => setMobileMenuOpen(true)}
          aria-label="Open menu"
          id="mobile-menu-btn"
        >
          <span className="hamburger-line" />
          <span className="hamburger-line" />
          <span className="hamburger-line" />
        </button>

        {/* Header */}
        <Header />

        {/* Main Grid: Sidebar + Content */}
        <div className="main-grid">
          <Sidebar
            activeSection={activeSection}
            onSectionClick={handleSectionClick}
            mobileOpen={mobileMenuOpen}
            onMobileClose={() => setMobileMenuOpen(false)}
          />

          <div className="content-area">
            <PromptPanel
              activeSection={activeSection}
              onCopy={handleCopy}
            />
            <UsageGuide />
          </div>
        </div>

        {/* Footer */}
        <Footer />
      </div>
    </>
  );
}
