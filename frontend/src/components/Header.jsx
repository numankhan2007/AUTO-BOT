// ── Header — Main title, badge, and stats ──
// [FIXED: L-2] useCountUp wired to StatCard for animated numeric values.

import { useInView, useCountUp } from "../hooks/useEffects";
import { STATS } from "../data/prompt";
import "./Header.css";

function GlitchText({ text, className = "" }) {
  return (
    <span className={`glitch-text ${className}`} data-text={text}>
      {text}
    </span>
  );
}

function StatCard({ stat, index }) {
  const [ref, inView] = useInView();

  // [FIXED: L-2] Parse numeric value for animation, leave non-numeric as static
  const numericValue = parseInt(stat.value);
  const isNumeric = !isNaN(numericValue) && /^\d+$/.test(stat.value.trim());

  // [FIXED: L-2] useCountUp triggers on viewport entry via inView flag
  const animatedCount = useCountUp(numericValue, 1500, inView && isNumeric);

  // Display: animated number for pure digits, static string for "~2,400", "MAX", "5+", etc.
  const displayValue = isNumeric ? animatedCount : stat.value;

  return (
    <div
      ref={ref}
      className={`stat-card ${inView ? "stat-visible" : ""}`}
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className="stat-icon-wrap">
        <span className="stat-icon">{stat.icon}</span>
      </div>
      <div className="stat-info">
        <div className="stat-value">{displayValue}</div>
        <div className="stat-label">{stat.label}</div>
      </div>
      <div className="stat-detail">{stat.detail}</div>
    </div>
  );
}

export default function Header() {
  const [ref, inView] = useInView();

  return (
    <header ref={ref} className={`header ${inView ? "header-visible" : ""}`} id="header">
      {/* Decorative top border gradient */}
      <div className="header-border-glow" />

      <div className="header-content">
        {/* Badge */}
        <div className="header-badge">
          <span className="badge-pulse" />
          <span className="badge-text">
            OPUS 4.6 · EXTENDED THINKING · SHADOW PROTOCOL
          </span>
        </div>

        {/* Title */}
        <div className="header-title-block">
          <h1 className="header-title">
            <span className="title-line-1">MONARCH-LEVEL</span>
            <GlitchText text="ENGINEERING PROMPT" className="title-line-2" />
          </h1>
          <p className="header-subtitle">
            A <em>maximum-depth reasoning</em> prompt engineered for{" "}
            <em>Claude Opus 4.6</em> with extended thinking — designed to
            produce <em>production-ready</em> Instagram webhook bot code in a
            single pass.
          </p>
        </div>

        {/* Stats */}
        <div className="stats-grid">
          {STATS.map((stat, i) => (
            <StatCard key={stat.label} stat={stat} index={i} />
          ))}
        </div>
      </div>
    </header>
  );
}
