// ── Background Effects: Matrix Rain, Particles, Scan Lines ──
// [FIXED: M-1] MatrixRain now scales for devicePixelRatio (Retina/HiDPI)

import { useEffect, useRef, useMemo } from "react";
import "./BackgroundEffects.css";

/**
 * Matrix-style falling characters — runs on a <canvas>.
 * [FIXED: M-1] Canvas resolution now accounts for devicePixelRatio.
 * On Retina displays (2x, 3x), the canvas renders at native resolution
 * and is CSS-scaled down, resulting in crisp characters instead of blur.
 */
export function MatrixRain() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let animId;
    let columns;
    let drops;

    const chars = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン01";
    const fontSize = 14;

    const resize = () => {
      // [FIXED: M-1] Scale canvas for HiDPI/Retina displays
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;   // Native pixel width
      canvas.height = window.innerHeight * dpr;  // Native pixel height
      canvas.style.width = window.innerWidth + "px";   // CSS display width
      canvas.style.height = window.innerHeight + "px"; // CSS display height
      ctx.setTransform(1, 0, 0, 1, 0, 0); // Reset any existing transform
      ctx.scale(dpr, dpr); // Scale drawing operations to match native res

      // Column count based on CSS (logical) width, not canvas pixel width
      columns = Math.floor(window.innerWidth / fontSize);
      drops = Array.from({ length: columns }, () => Math.random() * -100);
    };

    resize();
    window.addEventListener("resize", resize);

    const draw = () => {
      // Use CSS dimensions for drawing (ctx.scale handles the rest)
      ctx.fillStyle = "rgba(0, 3, 8, 0.06)";
      ctx.fillRect(0, 0, window.innerWidth, window.innerHeight);

      ctx.font = `${fontSize}px monospace`;

      for (let i = 0; i < drops.length; i++) {
        const char = chars[Math.floor(Math.random() * chars.length)];
        const x = i * fontSize;
        const y = drops[i] * fontSize;

        // Random color between monarch purple and dim
        const brightness = Math.random();
        if (brightness > 0.95) {
          ctx.fillStyle = "rgba(139, 92, 246, 0.9)";
        } else if (brightness > 0.8) {
          ctx.fillStyle = "rgba(124, 58, 237, 0.5)";
        } else {
          ctx.fillStyle = "rgba(76, 29, 149, 0.2)";
        }

        ctx.fillText(char, x, y);

        if (y > window.innerHeight && Math.random() > 0.975) {
          drops[i] = 0;
        }
        drops[i]++;
      }

      animId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="matrix-canvas" />;
}

/**
 * Floating particle field with randomized sizes and speeds.
 */
export function ParticleField() {
  const particles = useMemo(
    () =>
      Array.from({ length: 40 }, (_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 3 + 1,
        duration: Math.random() * 12 + 6,
        delay: Math.random() * 8,
        opacity: Math.random() * 0.5 + 0.1,
        color: Math.random() > 0.7 ? "var(--cyan)" : "var(--monarch)",
      })),
    []
  );

  return (
    <div className="particle-field" aria-hidden="true">
      {particles.map((p) => (
        <div
          key={p.id}
          className="particle"
          style={{
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: `${p.size}px`,
            height: `${p.size}px`,
            animationDuration: `${p.duration}s`,
            animationDelay: `${p.delay}s`,
            "--particle-opacity": p.opacity,
            "--particle-color": p.color,
          }}
        />
      ))}
    </div>
  );
}

/**
 * CRT-style scanline overlay.
 */
export function ScanLines() {
  return (
    <>
      <div className="scanlines-overlay" aria-hidden="true" />
      <div className="scanline-beam" aria-hidden="true" />
    </>
  );
}

/**
 * Ambient glow orbs that float in the background.
 */
export function AmbientOrbs() {
  return (
    <div className="ambient-orbs" aria-hidden="true">
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />
    </div>
  );
}
