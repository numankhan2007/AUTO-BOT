// ── Header — Main title, badge, and stats ──

import { useInView } from "../hooks/useEffects";
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
        <div className="stat-value">{stat.value}</div>
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
