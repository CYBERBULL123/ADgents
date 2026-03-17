# Quickstart

This guide will walk you through starting ADgents and creating your first agent!

## Prerequisites

- **Python 3.10+**
- (Optional) **API keys**: Set up keys for either `OpenAI`, `Google Gemini`, or `Anthropic Claude`. You can use a local provider like Ollama without requiring an API key.

## Installation & Setup

1. **Clone the repository:**
```bash
git clone <your-repository-url>
cd ADgents
```

2. **Run the startup sequence:**
```bash
python start.py
```
*Note: The script will create virtual environments, install dependencies, and launch the web server automatically.*

## Starting the UI Studio

Head over to **`http://localhost:8000/studio`** inside your web browser.

The studio offers an intuitive UI where you can construct an agent, chat with it, run tasks, view memory history, and add custom skills. 

1. Head to the **Settings** tab. Add your LLM keys and choose your preferred provider here.
2. Go to **Build Agent** and spawn one from our built-in templates (e.g. Researcher, Engineer).
3. Try sending it a **Task** to retrieve current data using a search skill!

## Using the CLI

If you prefer doing everything from the terminal:
```bash
# Check statuses
python cli.py status

# List templates
python cli.py templates

# See an interactive chat prompt with the researcher template
python cli.py chat researcher
```

## Running a Fast Task
```bash
python cli.py run engineer "Write a python script that prints 'Hello World!'"
```

Want to run everything programmatically within your own scripts instead? Read our [SDK Guide](sdk.md)!
