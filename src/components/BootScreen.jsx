// ── Boot Screen — Terminal-style loading sequence ──

import { useState, useEffect } from "react";
import "./BootScreen.css";

const BOOT_LINES = [
  { text: "SHADOW_SYSTEM v4.6.0 — Initializing...", delay: 0, type: "system" },
  { text: "Loading monarch protocol drivers...", delay: 300, type: "info" },
  { text: "├── kernel.shadow.extract .......... OK", delay: 600, type: "success" },
  { text: "├── api.meta.graph.v19 ............. OK", delay: 800, type: "success" },
  { text: "├── security.hmac.sha256 ........... OK", delay: 1000, type: "success" },
  { text: "├── scheduler.apscheduler .......... OK", delay: 1150, type: "success" },
  { text: "└── engine.fastapi.uvicorn ......... OK", delay: 1300, type: "success" },
  { text: "Verifying extended thinking capacity...", delay: 1600, type: "info" },
  { text: "THINKING_DEPTH: ████████████████████ MAX", delay: 1900, type: "monarch" },
  { text: "All systems operational. Arise, Hunter.", delay: 2300, type: "final" },
];

export default function BootScreen({ onComplete }) {
  const [lines, setLines] = useState([]);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState("booting"); // booting | fading | done

  useEffect(() => {
    const timers = [];

    BOOT_LINES.forEach((line, i) => {
      timers.push(
        setTimeout(() => {
          setLines((prev) => [...prev, line]);
          setProgress(((i + 1) / BOOT_LINES.length) * 100);
        }, line.delay)
      );
    });

    // Start fade out
    timers.push(
      setTimeout(() => setPhase("fading"), 2900)
    );

    // Complete
    timers.push(
      setTimeout(() => {
        setPhase("done");
        onComplete?.();
      }, 3500)
    );

    return () => timers.forEach(clearTimeout);
  }, [onComplete]);

  if (phase === "done") return null;

  return (
    <div className={`boot-screen ${phase === "fading" ? "boot-fade-out" : ""}`}>
      {/* Ambient glow */}
      <div className="boot-glow" />

      {/* Logo */}
      <div className="boot-logo-section">
        <div className="boot-sword">⚔️</div>
        <h1 className="boot-title">SHADOW SYSTEM</h1>
        <div className="boot-version">MONARCH PROTOCOL v4.6</div>
      </div>

      {/* Terminal output */}
      <div className="boot-terminal">
        <div className="boot-terminal-header">
          <span className="boot-dot boot-dot-r" />
          <span className="boot-dot boot-dot-y" />
          <span className="boot-dot boot-dot-g" />
          <span className="boot-terminal-title">shadow_init.sh</span>
        </div>
        <div className="boot-terminal-body">
          {lines.map((line, i) => (
            <div key={i} className={`boot-line boot-line-${line.type}`}>
              <span className="boot-line-prefix">
                {line.type === "system" ? "⚡" : line.type === "final" ? "⚔️" : "›"}
              </span>
              <span className="boot-line-text">{line.text}</span>
            </div>
          ))}
          <span className="boot-cursor">█</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="boot-progress-wrap">
        <div className="boot-progress-track">
          <div
            className="boot-progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="boot-progress-text">{Math.round(progress)}%</span>
      </div>
    </div>
  );
}
