# Desktop Vision + Control

## Definition

The ability for an AI agent to see the desktop screen (via screenshots or live capture), understand what's displayed, and interact with it using mouse clicks, keyboard input, dragging, and scrolling. This also includes reading the accessibility tree — the structured data layer that describes UI elements (button names, text fields, menus) without needing to visually interpret pixels.

## Purpose

Not everything is a terminal or a web browser. Desktop applications — Photoshop, Excel, email clients, system dialogs, installers, IDE GUIs, file managers — all require visual interaction. Without desktop vision and control, an entire category of software is completely inaccessible to the agent.

This is the component that bridges the gap between "things the terminal can reach" and "everything else with a UI."

## Status: DON'T HAVE

Anthropic's "computer use" exists as a separate product. `pyautogui`, `pywinauto`, and Windows UI Automation API exist as external libraries. Can read static screenshots that are manually provided. None of these are integrated into any AI agent framework as a native capability.

## Key Insight

There are two approaches to desktop control: **pixel-based** (screenshot → identify coordinates → click) and **accessibility-based** (read the UI tree → find the element by name → interact). Pixel-based is universal but brittle (breaks when the UI changes). Accessibility-based is robust but only works with apps that expose accessibility data. A complete solution needs both.

---

## What Exists Today

**Anthropic's "computer use"** — a separate capability that lets Claude take screenshots of the desktop, understand what's on screen, and issue mouse/keyboard actions. Exists as a product feature, not as an integrated tool in Claude Code or other agent frameworks.

**pyautogui** — Python library for programmatic mouse/keyboard control. Can move the mouse, click coordinates, type text, take screenshots. No understanding of what's on screen — just raw coordinate-based interaction. You have to tell it exactly where to click.

**pywinauto** — Python library specifically for Windows UI automation. Can read the accessibility tree, find buttons by name, interact with dialogs. More intelligent than pyautogui but Windows-only and only works with apps that expose accessibility data.

**Windows UI Automation API** — Microsoft's native accessibility framework. Every standard Windows control exposes its name, type, state, and available actions. Very powerful for standard apps. Useless for custom-rendered UIs (games, Electron apps with custom controls).

**Static screenshot reading** — AI agents can read image files, including screenshots. But someone has to take the screenshot first and provide it. There's no live screen capture integrated into the agent loop.

## Why This Is a Hard Gap

| Task | Can Terminal Do It? | Can Browser Do It? | Needs Desktop Control? |
|------|--------------------|--------------------|----------------------|
| Edit code in VS Code via GUI | No | No | Yes |
| Use Photoshop to resize an image | No | No | Yes |
| Click "Allow" on a system permission dialog | No | No | Yes |
| Run an installer that has a GUI wizard | No | No | Yes |
| Manage files in Windows Explorer | Partially (CLI) | No | Yes (for drag/drop, context menus) |
| Configure system settings in Settings app | No | No | Yes |
| Use a desktop email client | No | No | Yes |
| Interact with a desktop database GUI | No | No | Yes |
| Dismiss a popup notification | No | No | Yes |

None of these can be done through the terminal or browser. They require seeing the screen and clicking on things.

## The Two Approaches

### Approach 1: Pixel-Based (screenshot → reason → click)

1. Take a screenshot of the desktop
2. The AI analyzes the image — identifies buttons, text fields, menus, icons
3. The AI decides what to click and at what coordinates
4. A mouse/keyboard controller executes the click
5. Take another screenshot to verify the result
6. Repeat

**Pros:** Universal — works with any app, any UI, any platform. Doesn't require the app to expose accessibility data.

**Cons:** Brittle — if the UI moves, changes resolution, or looks different than expected, the coordinates are wrong. Slow — screenshot-analyze-act loop takes seconds per action. Error-prone — visual identification of UI elements isn't perfect.

### Approach 2: Accessibility-Based (read UI tree → find element → interact)

1. Query the OS accessibility API for the current window's UI tree
2. Get structured data: button "Save" at (120, 450), text field "Search" at (300, 80), menu "File" at (10, 30)
3. Find the element by name or role, not by coordinates
4. Interact with it through the accessibility API (click, type, select)
5. Query the UI tree again to verify the result

**Pros:** Robust — finds elements by name, not position. Fast — no screenshot-analyze loop. Reliable — uses the same APIs screen readers use.

**Cons:** Not universal — only works with apps that expose accessibility data. Custom UIs, games, and some Electron apps don't expose their elements. Platform-specific APIs (Windows UIA, macOS Accessibility, Linux AT-SPI).

### The Complete Solution: Both

Use accessibility-based interaction as the primary approach (faster, more reliable). Fall back to pixel-based when the app doesn't expose accessibility data (universal coverage). The agent decides which approach to use based on what's available.

## The Hard Problems

**1. Screen resolution and DPI scaling.** Different monitors, different DPI settings, different scaling factors. Coordinates that work on one screen fail on another. Multi-monitor setups add another dimension. The agent needs to handle all of this transparently.

**2. Timing and animation.** UI elements don't appear instantly — they animate, fade in, slide. Clicking before an element is fully rendered fails. The agent needs wait-for-element logic similar to what Playwright provides for web pages.

**3. Foreground/focus management.** The agent needs to bring the right window to the front before interacting with it. Windows can overlap, minimize, or lose focus. Managing window state is prerequisite to interacting with content.

**4. Security and trust.** A tool that can see your screen and control your mouse has access to everything — passwords being typed, private messages, financial data. The authority boundary model from the daemon component applies here heavily. What is the agent allowed to see? What is it allowed to click?

**5. Cross-platform abstraction.** Windows, macOS, and Linux all have different accessibility APIs, different window management, and different UI paradigms. Building a unified abstraction layer is significant work.

## What Would Need to Be Built

1. **A screen capture engine** — live screenshots on demand, or continuous screen monitoring at configurable intervals
2. **A UI tree reader** — cross-platform accessibility API abstraction (Windows UIA, macOS Accessibility, Linux AT-SPI)
3. **A mouse/keyboard controller** — cross-platform input simulation with DPI-aware coordinate handling
4. **An element finder** — given "click the Save button," find it via accessibility tree first, fall back to visual identification
5. **A window manager** — focus windows, manage overlapping apps, handle multi-monitor layouts
6. **Integration with agent tools** — expose desktop control as first-class tools in the agent loop (like Read, Edit, Bash)

## The Difference

| | Current State | Full Desktop Vision + Control |
|---|--------------|-------------------------------|
| Seeing the screen | Static screenshots, manually provided | Live capture on demand |
| Clicking | Can't | Full mouse control — click, drag, scroll |
| Typing | Can't (outside terminal) | Full keyboard input into any app |
| Finding UI elements | Can't | Accessibility tree + visual identification |
| Desktop apps | Completely inaccessible | Full interaction |
| System dialogs | Can't dismiss or respond | Full interaction |

## What It Covers

- Live screen capture and screenshot analysis
- Mouse control — click, double-click, right-click, drag, scroll at specific coordinates
- Keyboard control — type text, press key combinations, special keys
- Accessibility tree reading — identify UI elements by name, role, and state
- Window management — focus, resize, minimize, maximize, close applications
- System dialog interaction — file pickers, permission prompts, installers
- Any native desktop application that has a graphical interface
