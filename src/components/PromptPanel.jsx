// ── Prompt Panel — Syntax-highlighted prompt display with copy ──

import { useState, useRef, useCallback, useMemo } from "react";
import { PROMPT, SECTIONS } from "../data/prompt";
import "./PromptPanel.css";

/**
 * Syntax-highlight the XML prompt with colored tags, keys, and comments.
 */
function highlightPrompt(text) {
  const lines = text.split("\n");

  return lines.map((line, i) => {
    let highlighted = line;

    // XML opening tags: <tag_name>
    highlighted = highlighted.replace(
      /(&lt;|<)([\w_]+)(&gt;|>)/g,
      '<span class="syn-tag">&lt;$2&gt;</span>'
    );

    // XML closing tags: </tag_name>
    highlighted = highlighted.replace(
      /(&lt;|<)\/([\w_]+)(&gt;|>)/g,
      '<span class="syn-tag-close">&lt;/$2&gt;</span>'
    );

    // Backtick code
    highlighted = highlighted.replace(
      /`([^`]+)`/g,
      '<span class="syn-code">`$1`</span>'
    );

    // Key: Value patterns
    highlighted = highlighted.replace(
      /^(\s*)([\w\s]+?):\s{2,}/,
      '$1<span class="syn-key">$2:</span>  '
    );

    // Numbered items (1. or 1️⃣)
    highlighted = highlighted.replace(
      /^(\s*)((?:\d+\.|[0-9]️⃣))\s/,
      '$1<span class="syn-num">$2</span> '
    );

    // Bullet points
    highlighted = highlighted.replace(
      /^(\s*)([-•])\s/,
      '$1<span class="syn-bullet">$2</span> '
    );

    // Uppercase section headers
    highlighted = highlighted.replace(
      /^(\s*)((?:[A-Z][A-Z\s&]+){2,})$/,
      '$1<span class="syn-heading">$2</span>'
    );

    // Arrows and special operators
    highlighted = highlighted.replace(
      /(→|──|├──|└──)/g,
      '<span class="syn-operator">$1</span>'
    );

    // Emojis get a subtle class
    highlighted = highlighted.replace(
      /([\u{1F300}-\u{1FAD6}\u{2600}-\u{27BF}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}]+)/gu,
      '<span class="syn-emoji">$1</span>'
    );

    return `<span class="prompt-line" data-line="${i + 1}">${highlighted}</span>`;
  });
}

export default function PromptPanel({ activeSection, onCopy }) {
  const [copied, setCopied] = useState(false);
  const [ripple, setRipple] = useState(false);
  const scrollRef = useRef(null);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(PROMPT).then(() => {
      setCopied(true);
      setRipple(true);
      onCopy?.();
      setTimeout(() => setCopied(false), 2500);
      setTimeout(() => setRipple(false), 600);
    });
  }, [onCopy]);

  const highlightedLines = useMemo(() => highlightPrompt(PROMPT), []);

  // Find section in prompt for highlighting
  const activeSectionTag = activeSection
    ? SECTIONS.find((s) => s.id === activeSection)?.tag
    : null;

  return (
    <main className="prompt-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-title-row">
          <span className="panel-dot" />
          <h2 className="panel-title">SHADOW_SYSTEM_PROMPT.xml</h2>
          <span className="panel-size">~2,400 tokens</span>
        </div>

        <div className="panel-actions">
          <button
            className={`copy-btn ${copied ? "copy-success" : ""}`}
            onClick={handleCopy}
            id="copy-prompt-btn"
          >
            {ripple && <span className="copy-ripple" />}
            <span className="copy-icon">{copied ? "✅" : "⚔️"}</span>
            <span className="copy-text">
              {copied ? "COPIED TO CLIPBOARD" : "COPY FULL PROMPT"}
            </span>
          </button>
        </div>
      </div>

      {/* Section Label */}
      <div className="section-divider">
        <span className="section-divider-text">PROMPT PREVIEW</span>
      </div>

      {/* Prompt Container */}
      <div className={`prompt-container ${activeSection ? "prompt-highlight-active" : ""}`}>
        {/* Terminal-style top bar */}
        <div className="prompt-topbar">
          <div className="prompt-dots">
            <span className="p-dot p-dot-r" />
            <span className="p-dot p-dot-y" />
            <span className="p-dot p-dot-g" />
          </div>
          <span className="prompt-filename">shadow_system_prompt.xml</span>
          <div className="prompt-topbar-actions">
            <span className="prompt-lang-badge">XML</span>
          </div>
        </div>

        {/* Line numbers + code */}
        <div className="prompt-body" ref={scrollRef}>
          <div className="prompt-gutter">
            {highlightedLines.map((_, i) => (
              <div key={i} className="gutter-line">
                {i + 1}
              </div>
            ))}
          </div>
          <div
            className="prompt-code"
            dangerouslySetInnerHTML={{
              __html: highlightedLines.join("\n"),
            }}
          />
        </div>

        {/* Bottom info bar */}
        <div className="prompt-bottombar">
          <span className="prompt-info">
            {highlightedLines.length} lines · UTF-8 · LF
          </span>
          <span className="prompt-info">
            {SECTIONS.length} sections · Production Ready
          </span>
        </div>
      </div>
    </main>
  );
}
