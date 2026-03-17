# ADgents Documentation

Welcome to the **ADgents Documentation**.

**[⭐ View the official repository on GitHub](https://github.com/CYBERBULL123/ADgents)**

ADgents is an advanced, lightweight python framework and application platform designed to help you run **autonomous AI agents**. Instead of building from scratch, you can instantiate agents out-of-the-box that have distinct personas, interactive memory, and useful backend skills.

## Table of Contents

1. [Introduction](#introduction)
2. [Quickstart](quickstart.md)
3. [Architecture](architecture.md)
4. [Using the Studio UI](studio.md)
5. [Python SDK](sdk.md)
6. [Creating Custom Skills](skills.md)
7. [Real-World Use Cases](use_cases.md)

---

## Introduction

At its core, ADgents is built upon the idea of the **ReAct (Reasoning + Acting)** loop. An agent doesn't just respond blindly to a user input. It:
1. **Thinks** about the user input.
2. Formulates an **Action** (picking a tool/skill to use).
3. **Observes** the output of that action.
4. **Reflects** to decide if the task is complete, or if it needs to keep thinking and acting.

### Core Components
Every agent instantiated in ADgents relies on the following pillars:
- **Persona:** Defines the agent's behavior, tone, baseline autonomy level, and expertise domain.
- **Memory Engine:** A segmented multi-tier memory system (Working memory for the immediate conversation, Episodic memory for long-term task history, Semantic memory for learned rules).
- **Skill Engine:** A registry of safe, isolated python methods that give the agent agency to affect its environment. (e.g. searching the web, evaluating math calculations, running file IO).

## Supported LLM Providers
ADgents relies on a routing mechanism that allows you to hot-swap LLM engines behind the scenes.
We currently natively support:
- **OpenAI:** `gpt-4o`, `gpt-4o-mini`
- **Anthropic Claude:** `claude-3-5-sonnet-20241022`
- **Google Gemini:** `gemini-1.5-flash`, `gemini-1.5-pro`
- **Ollama (Local):** `llama3`, `mistral`

Check out our [Quickstart Guide](quickstart.md) to initialize your first agent!
