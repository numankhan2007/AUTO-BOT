// ── ErrorBoundary — Shadow System styled crash recovery ──
// [FIXED: M-4] Class-based ErrorBoundary with themed fallback UI.

import { Component } from "react";
import "./ErrorBoundary.css";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("⚔️ Shadow System Error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReboot = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-glitch-bg" aria-hidden="true">
            {Array.from({ length: 8 }, (_, i) => (
              <div key={i} className="glitch-line" style={{ animationDelay: `${i * 0.15}s` }} />
            ))}
          </div>
          <div className="error-content">
            <div className="error-icon">⚔️</div>
            <h1 className="error-title">SYSTEM ERROR</h1>
            <h2 className="error-subtitle">INSTANCE CORRUPTED</h2>
            <div className="error-terminal">
              <div className="error-terminal-bar">
                <span className="et-dot et-r" />
                <span className="et-dot et-y" />
                <span className="et-dot et-g" />
                <span className="et-filename">error_log.sys</span>
              </div>
              <div className="error-terminal-body">
                <span className="et-prefix">ERR</span>
                <span className="et-message">
                  {this.state.error?.message || "Unknown render error"}
                </span>
                {this.state.errorInfo?.componentStack && (
                  <pre className="et-stack">
                    {this.state.errorInfo.componentStack.slice(0, 500)}
                  </pre>
                )}
              </div>
            </div>
            <button className="reboot-btn" onClick={this.handleReboot}>
              <span className="reboot-icon">⟳</span>
              <span className="reboot-text">REBOOT SYSTEM</span>
            </button>
            <p className="error-hint">
              If this error persists, check the browser console for details.
            </p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
