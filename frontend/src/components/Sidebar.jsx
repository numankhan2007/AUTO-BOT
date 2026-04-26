// ── Sidebar — Navigation + Model Info ──

import { SECTIONS } from "../data/prompt";
import "./Sidebar.css";

export default function Sidebar({ activeSection, onSectionClick, mobileOpen, onMobileClose }) {
  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div className="sidebar-backdrop" onClick={onMobileClose} />
      )}

      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        {/* Mobile close */}
        <button className="sidebar-close-btn" onClick={onMobileClose} aria-label="Close sidebar">
          ✕
        </button>

        {/* Navigation */}
        <div className="sidebar-section">
          <div className="sidebar-title">
            <span className="sidebar-title-icon">◆</span>
            Prompt Architecture
          </div>

          <nav className="sidebar-nav">
            {SECTIONS.map((s, i) => (
              <button
                key={s.id}
                className={`nav-item ${activeSection === s.id ? "nav-active" : ""}`}
                onClick={() => {
                  onSectionClick(s.id);
                  onMobileClose?.();
                }}
                style={{
                  "--nav-color": s.color,
                  animationDelay: `${i * 60}ms`,
                }}
              >
                <span className="nav-icon">{s.icon}</span>
                <span className="nav-label">{s.label}</span>
                <span className="nav-indicator" />
              </button>
            ))}
          </nav>
        </div>

        <div className="sidebar-divider" />

        {/* Model Badge */}
        <div className="model-card">
          <div className="model-card-glow" />
          <div className="model-header">
            <div className="model-name">CLAUDE OPUS 4.6</div>
            <div className="model-tier">MONARCH TIER</div>
          </div>
          <p className="model-desc">
            Most capable model. Highest reasoning depth. Ideal for complex
            multi-file code generation tasks.
          </p>
          <div className="thinking-badge">
            <span className="thinking-dot" />
            <span>EXTENDED THINKING ON</span>
          </div>
        </div>

        <div className="sidebar-divider" />

        {/* Keyboard Shortcuts */}
        <div className="sidebar-section">
          <div className="sidebar-title">
            <span className="sidebar-title-icon">⌨</span>
            Shortcuts
          </div>
          <div className="shortcuts-list">
            <div className="shortcut-item">
              <kbd>Ctrl</kbd> + <kbd>C</kbd>
              <span>Copy prompt</span>
            </div>
            <div className="shortcut-item">
              <kbd>Esc</kbd>
              <span>Close panels</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
