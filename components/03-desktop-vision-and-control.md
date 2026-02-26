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

## What It Covers

- Live screen capture and screenshot analysis
- Mouse control — click, double-click, right-click, drag, scroll at specific coordinates
- Keyboard control — type text, press key combinations, special keys
- Accessibility tree reading — identify UI elements by name, role, and state
- Window management — focus, resize, minimize, maximize, close applications
- System dialog interaction — file pickers, permission prompts, installers
- Any native desktop application that has a graphical interface
