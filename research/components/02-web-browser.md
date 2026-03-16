# Web Browser

## Definition

The ability for an AI agent to interact with the web — navigating pages, reading content, clicking buttons, filling forms, extracting data, running JavaScript, and handling downloads. This includes both programmatic browser automation (Playwright, Puppeteer) for precise control and higher-level MCP browser tools for page understanding and research.

## Purpose

The web is where most of the world's information and services live. Without browser access, the agent is limited to its training data and local files. A browser unlocks web research, documentation reading, web app testing, scraping, OAuth authentication flows, and interaction with any web-based service.

An agent without a browser is like a developer who can write code but can't Google anything, read Stack Overflow, check documentation, or test their web app.

## Status: PARTIAL

WebFetch and WebSearch exist as basic tools. MCP browser tools exist as add-ons. Playwright exists as a separate framework requiring manual setup. No AI agent has a fully native, integrated browser that's as seamless as the terminal.

## Key Insight

Two levels of browser are needed: **programmatic** (Playwright-style — precise DOM manipulation, form filling, automated testing) and **semantic** (MCP browser-style — "read this page and understand it"). The first is for interacting with web apps. The second is for research and learning. Both are necessary; neither replaces the other.

---

## What Exists Today

**WebFetch / WebSearch** — basic built-in tools in Claude Code. Can fetch a URL and get its content, or search the web and get results. Good for simple research. Can't click buttons, fill forms, navigate SPAs, or handle complex web apps.

**MCP browser tools** — add-on tools that provide higher-level browsing with page understanding. Better than raw fetch for research. Available but require configuration, not built-in.

**Playwright / Puppeteer** — full programmatic browser automation. Can do everything a human can do in a browser — click, type, navigate, screenshot, extract data, run JavaScript. But these are separate frameworks that require manual setup and aren't integrated into the agent's tool loop natively.

**curl / wget (via terminal)** — can fetch raw HTML. Useless for JavaScript-rendered pages, SPAs, or anything that requires interaction.

## Why It's Only Partial

| Capability | WebFetch/Search | MCP Browser | Playwright | What's Needed |
|-----------|----------------|-------------|------------|---------------|
| Read a static page | Yes | Yes | Yes | Covered |
| Search the web | Yes | Yes | No | Covered |
| Navigate a SPA | No | Partially | Yes | Playwright fills the gap |
| Fill forms / click buttons | No | No | Yes | Only Playwright |
| Handle OAuth flows | No | No | Yes | Only Playwright |
| Test a web app | No | No | Yes | Only Playwright |
| Screenshot capture | No | Partially | Yes | Only Playwright |
| Run JavaScript in page | No | No | Yes | Only Playwright |
| Integrated into agent loop | Yes | Yes (add-on) | No | The gap |

The problem isn't that browser tools don't exist. It's that the **full-featured ones aren't integrated** and the **integrated ones aren't full-featured**.

## The Two Levels

### Level 1: Semantic Browser (for research)

The agent says "read this documentation page and explain the API" or "search for how to fix this error." The browser:
- Fetches the page
- Handles JavaScript rendering
- Extracts meaningful content (not raw HTML)
- Presents it in a format the AI can reason about
- Follows links if needed

This is what MCP browser tools do. It's about understanding web content, not interacting with it.

### Level 2: Programmatic Browser (for interaction)

The agent says "log into the dashboard, check the error rate, and download the log file." The browser:
- Opens a real browser instance
- Navigates to the URL
- Fills in username and password
- Clicks the login button
- Waits for the dashboard to load
- Reads the error rate from a specific element
- Clicks download on the log file
- Returns the result

This is what Playwright does. It's about doing things in a browser, not just reading.

## The Hard Problems

**1. JavaScript rendering.** Modern web pages are SPAs that render client-side. A simple HTTP fetch gets an empty HTML shell. You need a real browser engine (Chromium, Firefox) to see the actual content. This means running a browser process — heavier than a simple fetch.

**2. Authentication persistence.** Many useful pages require login. The agent needs to handle cookies, sessions, OAuth flows, and potentially 2FA. Storing auth state securely connects to the Credential Management component.

**3. Dynamic content.** Pages change — elements load asynchronously, modals pop up, content shifts. The agent needs to wait for elements, handle loading states, and retry when things aren't ready. Timing issues are the #1 source of flaky browser automation.

**4. Anti-bot detection.** Many websites actively detect and block automated browsers. CAPTCHAs, browser fingerprinting, rate limiting. This is an ongoing arms race.

**5. Context cost.** A web page can be huge. Dumping an entire page into the agent's context window wastes space. The browser needs smart content extraction — pull out what's relevant, discard the boilerplate.

## What Would Need to Be Built

1. **Native browser integration** — Playwright or equivalent running as a first-class tool in the agent loop, not a separate framework
2. **Smart content extraction** — Convert web pages to clean, relevant text instead of dumping raw HTML
3. **Session management** — Persistent browser sessions with auth state, cookies, and history
4. **Screenshot + visual understanding** — Take screenshots and reason about what's on the page visually, not just via DOM
5. **Credential integration** — Connect to the credential management system for secure login flows

## The Difference

| | Current State | Full Browser Integration |
|---|--------------|------------------------|
| Static pages | Can read | Can read |
| SPAs / dynamic content | Fails | Full rendering |
| Interaction (click, type) | Can't | Full control |
| Authentication | Manual | Automated with secure credentials |
| Testing web apps | Can't | Full end-to-end testing |
| Research | Basic search + fetch | Deep browsing with page understanding |

## What It Covers

- Web page navigation and content extraction
- Form filling and button clicking
- JavaScript execution in page context
- File downloads and uploads
- OAuth and browser-based authentication flows
- Web application testing and validation
- Research, documentation reading, information gathering
- Screenshot capture of web content
