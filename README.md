# ⚔️ Shadow System — Monarch-Level Engineering Prompt

A stunning, production-grade web showcase for a maximum-depth reasoning prompt engineered for **Claude Opus 4.6** with Extended Thinking.

![Shadow System](https://img.shields.io/badge/Claude-Opus%204.6-7c3aed?style=for-the-badge&logo=anthropic&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8.0-646CFF?style=for-the-badge&logo=vite&logoColor=white)

## ✨ Features

- 🎬 **Terminal Boot Sequence** — Cinematic startup with typed output lines
- 🌧️ **Matrix Rain** — Canvas-rendered Japanese katakana in monarch purple
- ✨ **Particle System** — 40 floating particles with randomized physics
- 🔍 **Syntax Highlighting** — XML tags, code blocks, keys, and operators
- 📋 **One-Click Copy** — Copy the full prompt with ripple feedback
- 📱 **Fully Responsive** — Mobile drawer sidebar, adaptive grid
- ⌨️ **Keyboard Shortcuts** — `Ctrl+C` to copy, `Esc` to close panels

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/numankhan2007/AUTO-BOT.git
cd AUTO-BOT

# Install dependencies
npm install

# Start dev server
npm run dev
```

## 📁 Project Structure

```
├── index.html              # Entry HTML with SEO meta tags
├── vite.config.js          # Vite build config
├── package.json            # Dependencies + scripts
└── src/
    ├── main.jsx            # React entry point
    ├── App.jsx             # Main app with boot sequence orchestration
    ├── App.css             # Layout styles
    ├── index.css           # Design system (80+ CSS custom properties)
    ├── data/
    │   └── prompt.js       # All prompt content, sections, stats
    ├── hooks/
    │   └── useEffects.js   # Custom hooks (intersection observer, typewriter, etc.)
    └── components/
        ├── BackgroundEffects.jsx/css  # Matrix rain, particles, scanlines, orbs
        ├── BootScreen.jsx/css         # Terminal boot animation
        ├── Header.jsx/css             # Title, stats grid, glitch text
        ├── Sidebar.jsx/css            # Navigation, model card, shortcuts
        ├── PromptPanel.jsx/css        # Syntax-highlighted prompt display
        ├── UsageGuide.jsx/css         # Step-by-step usage cards
        └── Footer.jsx/css             # Tech stack badges
```

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| React 19 | UI framework |
| Vite 8 | Build tool & dev server |
| Vanilla CSS | Design system with custom properties |

## 📜 License

MIT
