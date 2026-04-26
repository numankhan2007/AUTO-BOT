// ── CopyToast — Slide-in notification for clipboard copy ──
// [FIXED: L-1] Proper toast component replacing the flash overlay approach.
// Uses the existing .copy-toast CSS from App.css.

import { useState, useEffect } from "react";
import "./CopyToast.css";

export default function CopyToast({ visible, onDone }) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (visible) {
      setShow(true);
      const timer = setTimeout(() => {
        setShow(false);
        onDone?.();
      }, 2500);
      return () => clearTimeout(timer);
    }
  }, [visible, onDone]);

  if (!show) return null;

  return (
    <div className="copy-toast" role="status" aria-live="polite">
      <span className="copy-toast-icon">✅</span>
      <span className="copy-toast-text">PROMPT COPIED TO CLIPBOARD</span>
      <div className="copy-toast-progress" />
    </div>
  );
}
