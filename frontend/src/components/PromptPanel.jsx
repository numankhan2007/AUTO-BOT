// ── Prompt Panel — Syntax-highlighted prompt display with copy ──
// [FIXED: H-1] Eliminated dangerouslySetInnerHTML entirely.
// highlightPrompt() now returns React <span> elements instead of raw HTML strings.

import { useState, useRef, useCallback, useMemo } from "react";
import { PROMPT, SECTIONS } from "../data/prompt";
import "./PromptPanel.css";

/**
 * Syntax-highlight a single line of the XML prompt.
 * [FIXED: H-1] Returns an array of React elements (JSX spans) instead of
 * raw HTML strings. This eliminates the XSS vector from dangerouslySetInnerHTML.
 *
 * Strategy: Split each line into tokens using regex, then map tokens to
 * styled <span> elements. Visual fidelity is preserved — same CSS classes.
 */
function highlightLine(line, lineIndex) {
  // Build an array of { text, className } segments
  const segments = [];
  let remaining = line;
  let segKey = 0;

  // Helper: push a segment and consume the matched text
  const pushSegment = (match, className) => {
    const idx = remaining.indexOf(match);
    if (idx > 0) {
      // Push any text before the match as plain
      segments.push({ text: remaining.slice(0, idx), className: null });
    }
    segments.push({ text: match, className });
    remaining = remaining.slice(idx + match.length);
  };

  // Process patterns in priority order (same as the original regex chain)

  // 1. XML tags: <tag_name> and </tag_name>
  const tagRegex = /<\/?[\w_]+>/g;
  let tagMatch;
  const tagMatches = [];
  while ((tagMatch = tagRegex.exec(line)) !== null) {
    tagMatches.push({
      index: tagMatch.index,
      text: tagMatch[0],
      className: tagMatch[0].startsWith("</") ? "syn-tag-close" : "syn-tag",
    });
  }

  // 2. Backtick code: `code`
  const codeRegex = /`[^`]+`/g;
  let codeMatch;
  const codeMatches = [];
  while ((codeMatch = codeRegex.exec(line)) !== null) {
    codeMatches.push({
      index: codeMatch.index,
      text: codeMatch[0],
      className: "syn-code",
    });
  }

  // 3. Arrows and operators: →, ──, ├──, └──
  const opRegex = /(→|──+|├──|└──)/g;
  let opMatch;
  const opMatches = [];
  while ((opMatch = opRegex.exec(line)) !== null) {
    opMatches.push({
      index: opMatch.index,
      text: opMatch[0],
      className: "syn-operator",
    });
  }

  // Combine all matches, sort by position
  const allMatches = [...tagMatches, ...codeMatches, ...opMatches].sort(
    (a, b) => a.index - b.index
  );

  // Remove overlapping matches (keep first occurrence)
  const filtered = [];
  let lastEnd = -1;
  for (const m of allMatches) {
    if (m.index >= lastEnd) {
      filtered.push(m);
      lastEnd = m.index + m.text.length;
    }
  }

  // Build the final segments array
  let cursor = 0;
  for (const m of filtered) {
    if (m.index > cursor) {
      segments.push({ text: line.slice(cursor, m.index), className: null });
    }
    segments.push({ text: m.text, className: m.className });
    cursor = m.index + m.text.length;
  }
  if (cursor < line.length) {
    segments.push({ text: line.slice(cursor), className: null });
  }
  if (segments.length === 0) {
    segments.push({ text: line, className: null });
  }

  // Check line-level patterns for additional styling
  const trimmed = line.trimStart();
  let lineClass = "";

  // Numbered items (1. or emoji numbers)
  if (/^\d+\.?\s/.test(trimmed) || /^[0-9]️⃣/.test(trimmed)) {
    lineClass = "syn-numbered";
  }
  // Bullet points
  else if (/^[-•]\s/.test(trimmed)) {
    lineClass = "syn-bulleted";
  }
  // Key: Value patterns (key followed by multiple spaces)
  else if (/^[\w\s]+?:\s{2,}/.test(trimmed)) {
    lineClass = "syn-keyed";
  }
  // ALL-CAPS headings (at least 2 uppercase words)
  else if (/^(?:[A-Z][A-Z\s&]+){2,}$/.test(trimmed)) {
    lineClass = "syn-heading";
  }

  // [FIXED: H-1] Return JSX elements, not HTML strings
  return (
    <span
      key={`line-${lineIndex}`}
      className={`prompt-line ${lineClass}`}
      data-line={lineIndex + 1}
    >
      {segments.map((seg, i) =>
        seg.className ? (
          <span key={`${lineIndex}-${i}`} className={seg.className}>
            {seg.text}
          </span>
        ) : (
          <span key={`${lineIndex}-${i}`}>{seg.text}</span>
        )
      )}
      {"\n"}
    </span>
  );
}

/**
 * Highlight the entire prompt text.
 * [FIXED: H-1] Returns React elements array — no HTML strings, no injection.
 */
function highlightPrompt(text) {
  return text.split("\n").map((line, i) => highlightLine(line, i));
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

        {/* [FIXED: H-1] Line numbers + code — NO dangerouslySetInnerHTML */}
        <div className="prompt-body" ref={scrollRef}>
          <div className="prompt-gutter">
            {highlightedLines.map((_, i) => (
              <div key={i} className="gutter-line">
                {i + 1}
              </div>
            ))}
          </div>
          <div className="prompt-code">
            {highlightedLines}
          </div>
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
