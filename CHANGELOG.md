# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-01-01

### Added
- Initial release of Molten Agents Kit
- 14 Agno tools for full Moltbook API coverage (feed, posts, comments, votes, follows, search, submolts, performance tracking)
- Automatic AI verification (Reverse CAPTCHA) solver using GPT-4o-mini
- Multi-LLM support: OpenAI, Gemini, Groq, Ollama
- Heartbeat loop with configurable interval
- 10 post formats with automatic rotation
- 9 hook strategies for attention-grabbing openers
- Smart submolt targeting via topic-to-community mapping
- State management with persistence across restarts
- Delta-based engagement tracking to prevent double-counting
- Dedup system for seen posts and replied comments
- Suspension and ban detection with graceful shutdown
- CLI: register, run once, check status, run continuously
- Personality system with customization points
- Apache 2.0 license
