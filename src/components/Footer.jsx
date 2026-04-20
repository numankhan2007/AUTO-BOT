// ── Footer ──

import "./Footer.css";

export default function Footer() {
  return (
    <footer className="footer" id="footer">
      <div className="footer-content">
        <div className="footer-left">
          <span className="footer-brand">
            <span className="footer-sword">⚔️</span>
            <span className="footer-brand-text">SHADOW SYSTEM</span>
          </span>
          <span className="footer-separator">·</span>
          <span className="footer-tagline">
            Engineered for Claude Opus 4.6 Extended Thinking
          </span>
        </div>

        <div className="footer-right">
          <div className="footer-tech-stack">
            {["Meta Graph API v19.0", "FastAPI", "APScheduler", "ngrok"].map(
              (tech) => (
                <span key={tech} className="footer-tech-badge">
                  {tech}
                </span>
              )
            )}
          </div>
        </div>
      </div>

      {/* Decorative bottom border */}
      <div className="footer-border-glow" />
    </footer>
  );
}
