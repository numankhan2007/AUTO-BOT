// ── Custom hooks for the Shadow System ──

import { useState, useEffect, useRef, useCallback } from "react";

/**
 * Intersection Observer hook — triggers animation when element enters viewport.
 */
export function useInView(options = {}) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.unobserve(el);
        }
      },
      { threshold: 0.1, ...options }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return [ref, inView];
}

/**
 * Typewriter effect — reveals text character-by-character.
 * [FIXED: H-2] Interval cleanup is now in the useEffect return,
 * not inside the setTimeout callback. The `interval` variable is
 * declared in the outer scope so the cleanup function can access it.
 */
export function useTypewriter(text, speed = 40, startDelay = 0, enabled = true) {
  const [displayed, setDisplayed] = useState("");
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    setDisplayed("");
    setIsDone(false);

    let interval; // [FIXED: H-2] Declared in outer scope for cleanup access
    const timeout = setTimeout(() => {
      let i = 0;
      interval = setInterval(() => { // [FIXED: H-2] Assigned in outer scope
        if (i < text.length) {
          setDisplayed(text.slice(0, i + 1));
          i++;
        } else {
          setIsDone(true);
          clearInterval(interval);
        }
      }, speed);
    }, startDelay);

    // [FIXED: H-2] Both timeout AND interval are cleared on unmount
    return () => {
      clearTimeout(timeout);
      clearInterval(interval);
    };
  }, [text, speed, startDelay, enabled]);

  return { displayed, isDone };
}

/**
 * Counter animation — counts from 0 to target value.
 */
export function useCountUp(target, duration = 1500, enabled = true) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!enabled) return;

    const num = parseInt(target);
    if (isNaN(num)) {
      setCount(target); // Non-numeric values pass through as-is
      return;
    }

    const startTime = Date.now();
    let animId;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // easeOutExpo — fast start, smooth deceleration
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      const current = Math.round(eased * num);
      setCount(current);

      if (progress < 1) {
        animId = requestAnimationFrame(animate);
      }
    };

    animId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animId); // [FIXED: L-2] Proper cleanup
  }, [target, duration, enabled]);

  return count;
}

/**
 * Mouse-tracking glow effect for cards.
 */
export function useMouseGlow() {
  const ref = useRef(null);

  const handleMouseMove = useCallback((e) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    el.style.setProperty("--glow-x", `${x}px`);
    el.style.setProperty("--glow-y", `${y}px`);
  }, []);

  return { ref, onMouseMove: handleMouseMove };
}

/**
 * Keyboard shortcut hook.
 * [FIXED: H-3] Destructured modifiers into primitive deps (ctrl, shift, alt)
 * instead of using the object reference. This prevents the effect from
 * re-registering the event listener on every render cycle.
 */
export function useKeyboardShortcut(key, callback, { ctrl = false, shift = false, alt = false } = {}) {
  useEffect(() => {
    const handler = (e) => {
      if (
        e.key.toLowerCase() === key.toLowerCase() &&
        e.ctrlKey === ctrl && // [FIXED: H-3] Primitive boolean comparison
        e.shiftKey === shift &&
        e.altKey === alt
      ) {
        e.preventDefault();
        callback();
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [key, callback, ctrl, shift, alt]); // [FIXED: H-3] All primitive deps
}
