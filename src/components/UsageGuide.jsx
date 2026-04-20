// ── Usage Guide — Step-by-step cards ──

import { useInView } from "../hooks/useEffects";
import { USAGE_STEPS } from "../data/prompt";
import "./UsageGuide.css";

function StepCard({ step, index }) {
  const [ref, inView] = useInView();

  return (
    <div
      ref={ref}
      className={`usage-card ${inView ? "usage-visible" : ""}`}
      style={{ animationDelay: `${index * 100}ms` }}
    >
      {/* Step number badge */}
      <div className="usage-step-badge">
        <span className="usage-step-num">{step.step}</span>
      </div>

      {/* Icon */}
      <div className="usage-icon">{step.icon}</div>

      {/* Content */}
      <h3 className="usage-title">{step.title}</h3>
      <p className="usage-desc">{step.desc}</p>

      {/* Accent tag */}
      <div className="usage-accent">
        <span className="usage-accent-dot" />
        {step.accent}
      </div>

      {/* Hover glow */}
      <div className="usage-card-glow" />
    </div>
  );
}

export default function UsageGuide() {
  const [ref, inView] = useInView();

  return (
    <section ref={ref} className={`usage-section ${inView ? "usage-section-visible" : ""}`}>
      {/* Section header */}
      <div className="section-divider usage-divider">
        <span className="section-divider-text">HOW TO USE</span>
      </div>

      {/* Steps grid */}
      <div className="usage-grid">
        {USAGE_STEPS.map((step, i) => (
          <StepCard key={step.step} step={step} index={i} />
        ))}
      </div>

      {/* Bottom note */}
      <div className="usage-note">
        <span className="usage-note-icon">💡</span>
        <span className="usage-note-text">
          Pro tip: The prompt works best with <strong>Extended Thinking</strong> at maximum budget.
          Expect ~60-120 seconds of deep reasoning before the code output begins.
        </span>
      </div>
    </section>
  );
}
