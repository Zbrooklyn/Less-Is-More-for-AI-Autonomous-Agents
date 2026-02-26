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

## What It Covers

- Web page navigation and content extraction
- Form filling and button clicking
- JavaScript execution in page context
- File downloads and uploads
- OAuth and browser-based authentication flows
- Web application testing and validation
- Research, documentation reading, information gathering
- Screenshot capture of web content
