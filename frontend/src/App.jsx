// ── App.jsx — Shadow System Main Application ──
// [FIXED: M-2] handleSectionClick timeout uses ref for cleanup
// [FIXED: M-4] ErrorBoundary wraps app + separate boundary for MatrixRain
// [FIXED: L-1] CopyToast replaces flash overlay

import { useState, useCallback, useRef, useEffect } from "react";
import { useKeyboardShortcut } from "./hooks/useEffects";
import { PROMPT, SECTIONS } from "./data/prompt";

import ErrorBoundary from "./components/ErrorBoundary";
import BootScreen from "./components/BootScreen";
import { MatrixRain, ParticleField, ScanLines, AmbientOrbs } from "./components/BackgroundEffects";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import PromptPanel from "./components/PromptPanel";
import UsageGuide from "./components/UsageGuide";
import Footer from "./components/Footer";
import CopyToast from "./components/CopyToast";

import "./App.css";

export default function App() {
  const [booted, setBooted] = useState(false);
  const [activeSection, setActiveSection] = useState(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showToast, setShowToast] = useState(false);

  // [FIXED: M-2] Ref to track the section highlight timeout
  const sectionTimerRef = useRef(null);

  const handleBootComplete = useCallback(() => {
    setBooted(true);
  }, []);

  // [FIXED: M-2] Clear previous timeout before setting a new one.
  // The ref ensures we can always cancel the latest timeout on unmount.
  const handleSectionClick = useCallback((sectionId) => {
    if (sectionTimerRef.current) clearTimeout(sectionTimerRef.current);
    setActiveSection(sectionId);
    sectionTimerRef.current = setTimeout(() => setActiveSection(null), 2500);
  }, []);

  // [FIXED: M-2] Cleanup on unmount — prevents setState on dead component
  useEffect(() => () => clearTimeout(sectionTimerRef.current), []);

  // [FIXED: L-1] Show toast instead of flash overlay
  const handleCopy = useCallback(() => {
    setShowToast(true);
  }, []);

  const handleToastDone = useCallback(() => {
    setShowToast(false);
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

      {/* [FIXED: M-4] MatrixRain in its own ErrorBoundary — canvas crash won't kill main UI */}
      <ErrorBoundary>
        <MatrixRain />
      </ErrorBoundary>

      {/* Background Effects */}
      <ParticleField />
      <ScanLines />
      <AmbientOrbs />

      {/* [FIXED: L-1] Toast notification replaces flash overlay */}
      <CopyToast visible={showToast} onDone={handleToastDone} />

      {/* [FIXED: M-4] Main app wrapped in ErrorBoundary */}
      <ErrorBoundary>
        <div className={booted ? "app app-visible" : "app"}>
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
      </ErrorBoundary>
    </>
  );
}
