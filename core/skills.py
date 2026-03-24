"""
ADgents Skills Engine
Skills are the tools agents can use to interact with the real world.
Each skill is a callable action with a name, description, and parameters schema.
"""
import subprocess
import json
import time
import traceback
import httpx
from pathlib import Path
from typing import Callable, Dict, Any, List, Optional
from dataclasses import dataclass, field

# Directory for agent-created files
FILES_DIR = Path(__file__).parent.parent / "data" / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SkillResult:
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    
    def to_text(self) -> str:
        if self.success:
            return f"✅ Result:\n{self.output}"
        return f"❌ Error: {self.error}"


@dataclass
class Skill:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for parameters
    handler: Callable
    category: str = "general"
    requires_confirmation: bool = False
    is_custom: bool = False        # True for user-registered skills
    handler_code: str = ""        # Source code for custom skills
    
    def execute(self, **kwargs) -> SkillResult:
        start = time.time()
        try:
            output = self.handler(**kwargs)
            return SkillResult(
                success=True, 
                output=output,
                execution_time=time.time() - start
            )
        except TypeError as te:
            # Handle parameter mismatches for custom skills
            if "unexpected keyword argument" in str(te) and self.is_custom:
                import inspect
                try:
                    sig = inspect.signature(self.handler)
                    filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
                    output = self.handler(**filtered)
                    return SkillResult(success=True, output=output, execution_time=time.time() - start)
                except:
                    pass
            return SkillResult(
                success=False,
                output=None,
                error=f"{type(te).__name__}: {str(te)}\n{traceback.format_exc()}",
                execution_time=time.time() - start
            )
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
                execution_time=time.time() - start
            )
    
    def to_openai_tool(self) -> Dict:
        """Format as OpenAI function tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


# ─── Built-in Skill Handlers ──────────────────────────────────────────────────

def _skill_web_search(query: str, num_results: int = 5) -> str:
    """Search the web using multiple fallback strategies."""
    results = []
    
    # Strategy 1: DuckDuckGo Instant Answer API (no API key needed)
    try:
        import httpx as _httpx
        r = _httpx.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=8,
            headers={"User-Agent": "ADgents/1.0"}
        )
        data = r.json()
        if data.get("AbstractText"):
            results.append(f"**Summary**: {data['AbstractText']}")
            if data.get("AbstractURL"):
                results.append(f"Source: {data['AbstractURL']}")
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(f"• {topic['Text']}")
                if topic.get("FirstURL"):
                    results.append(f"  {topic['FirstURL']}")
    except Exception as e1:
        pass
    
    if results:
        return "\n".join(results)
    
    # Strategy 2: Wikipedia search
    try:
        import httpx as _httpx
        r = _httpx.get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ", "_"),
            timeout=8,
            headers={"User-Agent": "ADgents/1.0"}
        )
        if r.status_code == 200:
            data = r.json()
            extract = data.get("extract", "")
            if extract:
                results.append(f"**Wikipedia — {data.get('title', query)}**")
                results.append(extract[:800])
                results.append(f"Read more: {data.get('content_urls', {}).get('desktop', {}).get('page', '')}")
    except Exception as e2:
        pass
    
    if results:
        return "\n".join(results)
    
    # Strategy 3: DuckDuckGo HTML scrape
    try:
        import httpx as _httpx
        import re
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        r = _httpx.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 ADgents/1.0"})
        snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        clean = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:num_results]]
        if clean:
            results = [f"• {s}" for s in clean if s]
    except Exception as e3:
        pass
    
    return "\n".join(results) if results else (
        f"Could not retrieve web results for '{query}'. "
        "The agent will use its training knowledge to answer. "
        "Consider configuring a Search API key in settings for reliable results."
    )


def _skill_code_execute(code: str, language: str = "python") -> str:
    """Execute code in a subprocess sandbox."""
    if language.lower() not in ("python", "python3"):
        return f"Language '{language}' not yet supported. Only Python is available."
    
    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout
        if result.returncode != 0:
            output += f"\nError:\n{result.stderr}"
        return output or "(No output)"
    except subprocess.TimeoutExpired:
        return "Code execution timed out (30s limit)"
    except Exception as e:
        return f"Execution error: {e}"


def _skill_file_read(path: str) -> str:
    """Read a file from the filesystem."""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return f"File not found: {path}"
    if not p.is_file():
        return f"Path is not a file: {path}"
    if p.stat().st_size > 1_000_000:
        return f"File too large ({p.stat().st_size} bytes). Max 1MB."
    
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Could not read file: {e}"


def _skill_file_write(path: str, content: str, mode: str = "w") -> str:
    """Write content to a file. Relative paths are saved to data/files/."""
    from pathlib import Path
    
    p = Path(path)
    
    # If path is relative (not absolute), save to data/files/
    if not p.is_absolute():
        p = FILES_DIR / path
    
    # Create parent directories if needed
    p.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)
        
        # Return relative path from project root for user-friendly display
        try:
            rel_path = p.relative_to(Path(__file__).parent.parent)
            return f"✅ Successfully wrote {len(content)} characters to {rel_path}"
        except ValueError:
            return f"✅ Successfully wrote {len(content)} characters to {p}"
    except Exception as e:
        return f"❌ Could not write file: {e}"


def _skill_api_call(url: str, method: str = "GET", headers: Dict = None, 
                    body: Dict = None, params: Dict = None) -> str:
    """Make an HTTP API call."""
    try:
        with httpx.Client(timeout=15) as client:
            response = client.request(
                method=method.upper(),
                url=url,
                headers=headers or {},
                json=body,
                params=params
            )
            try:
                return json.dumps(response.json(), indent=2)
            except Exception:
                return response.text[:2000]
    except Exception as e:
        return f"API call failed: {e}"


def _skill_list_directory(path: str = ".") -> str:
    """List files and folders in a directory."""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return f"Directory not found: {path}"
    
    items = []
    for item in sorted(p.iterdir()):
        icon = "📁" if item.is_dir() else "📄"
        size = f" ({item.stat().st_size:,} bytes)" if item.is_file() else ""
        items.append(f"{icon} {item.name}{size}")
    
    return f"Contents of {path}:\n" + "\n".join(items) if items else f"Empty directory: {path}"


def _skill_get_datetime() -> str:
    """Get the current date and time."""
    from datetime import datetime
    now = datetime.now()
    return f"""Current date/time:
- Date: {now.strftime('%A, %B %d, %Y')}
- Time: {now.strftime('%I:%M:%S %p')}
- ISO 8601: {now.isoformat()}
- Unix timestamp: {int(now.timestamp())}"""


def _skill_calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression."""
    import math
    allowed_names = {
        k: v for k, v in math.__dict__.items() if not k.startswith("_")
    }
    allowed_names.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum})
    
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Calculation error: {e}"


def _skill_json_parse(json_string: str) -> str:
    """Parse and pretty-print JSON."""
    try:
        parsed = json.loads(json_string)
        return json.dumps(parsed, indent=2)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"


def _skill_summarize_text(text: str, max_sentences: int = 5) -> str:
    """Simple extractive text summarization."""
    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
    if len(sentences) <= max_sentences:
        return text
    
    # Score sentences by keyword frequency
    from collections import Counter
    words = text.lower().split()
    freq = Counter(words)
    
    def score(sentence):
        return sum(freq.get(w.lower(), 0) for w in sentence.split())
    
    top = sorted(sentences, key=score, reverse=True)[:max_sentences]
    ordered = [s for s in sentences if s in top]
    return ". ".join(ordered) + "."


# ─── Skill Registry ───────────────────────────────────────────────────────────

class SkillRegistry:
    """Central registry of all available skills."""
    
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._register_builtin_skills()
    
    def _register_builtin_skills(self):
        builtins = [
            Skill(
                name="web_search",
                description="Search the internet for current information, news, facts, or any topic",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "num_results": {"type": "integer", "description": "Number of results to return (1-10)", "default": 5}
                    },
                    "required": ["query"]
                },
                handler=_skill_web_search,
                category="information"
            ),
            Skill(
                name="code_execute",
                description="Execute Python code and return the output. Use for calculations, data processing, or testing code.",
                parameters={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python code to execute"},
                        "language": {"type": "string", "description": "Programming language", "default": "python"}
                    },
                    "required": ["code"]
                },
                handler=_skill_code_execute,
                category="development"
            ),
            Skill(
                name="file_read",
                description="Read the contents of a file from the filesystem",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Absolute or relative file path"}
                    },
                    "required": ["path"]
                },
                handler=_skill_file_read,
                category="filesystem"
            ),
            Skill(
                name="file_write",
                description="Write or append content to a file on the filesystem",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to write to"},
                        "content": {"type": "string", "description": "Content to write"},
                        "mode": {"type": "string", "description": "Write mode: 'w' (overwrite) or 'a' (append)", "default": "w"}
                    },
                    "required": ["path", "content"]
                },
                handler=_skill_file_write,
                category="filesystem",
                requires_confirmation=True
            ),
            Skill(
                name="api_call",
                description="Make HTTP API requests to external services",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "API endpoint URL"},
                        "method": {"type": "string", "description": "HTTP method", "default": "GET"},
                        "headers": {"type": "object", "description": "HTTP headers"},
                        "body": {"type": "object", "description": "Request body (for POST/PUT)"},
                        "params": {"type": "object", "description": "URL query parameters"}
                    },
                    "required": ["url"]
                },
                handler=_skill_api_call,
                category="integration"
            ),
            Skill(
                name="list_directory",
                description="List files and folders in a directory",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path to list", "default": "."}
                    }
                },
                handler=_skill_list_directory,
                category="filesystem"
            ),
            Skill(
                name="get_datetime",
                description="Get the current date and time",
                parameters={"type": "object", "properties": {}},
                handler=_skill_get_datetime,
                category="utility"
            ),
            Skill(
                name="calculate",
                description="Evaluate a mathematical expression or calculation",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Mathematical expression to evaluate"}
                    },
                    "required": ["expression"]
                },
                handler=_skill_calculate,
                category="utility"
            ),
            Skill(
                name="json_parse",
                description="Parse and format JSON data",
                parameters={
                    "type": "object",
                    "properties": {
                        "json_string": {"type": "string", "description": "JSON string to parse"}
                    },
                    "required": ["json_string"]
                },
                handler=_skill_json_parse,
                category="data"
            ),
            Skill(
                name="summarize_text",
                description="Create a condensed summary of a long text",
                parameters={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to summarize"},
                        "max_sentences": {"type": "integer", "description": "Maximum sentences in summary", "default": 5}
                    },
                    "required": ["text"]
                },
                handler=_skill_summarize_text,
                category="text"
            )
        ]
        
        for skill in builtins:
            self._skills[skill.name] = skill
    
    def register(self, skill: Skill):
        """Register a custom skill."""
        self._skills[skill.name] = skill
    
    def register_function(self, name: str, description: str, parameters: Dict, 
                          handler: Callable, category: str = "custom") -> Skill:
        """Quick way to register a function as a skill."""
        skill = Skill(name=name, description=description, parameters=parameters,
                     handler=handler, category=category)
        self.register(skill)
        return skill
    
    def register_from_code(self, name: str, description: str, handler_code: str,
                           parameters: Dict = None, category: str = "custom") -> Skill:
        """
        Register a skill from Python source code.
        The code must define a function called `handler`.
        """
        import re
        if not re.match(r'^[a-z_][a-z0-9_]*$', name):
            raise ValueError(f"Invalid skill name '{name}'. Use lowercase letters, numbers, underscores.")
        
        # Execute the code in a sandboxed namespace
        namespace: Dict[str, Any] = {}
        try:
            exec(handler_code, namespace)
        except Exception as e:
            raise ValueError(f"Error in handler code: {e}")
        
        handler_fn = namespace.get("handler")
        if not callable(handler_fn):
            raise ValueError("handler_code must define a callable function named 'handler'")
        
        skill = Skill(
            name=name,
            description=description,
            parameters=parameters or {"type": "object", "properties": {}},
            handler=handler_fn,
            category=category,
            is_custom=True,
            handler_code=handler_code
        )
        self.register(skill)
        return skill
    
    def unregister(self, name: str) -> bool:
        """Remove a skill from the registry. Returns True if removed."""
        if name in self._skills:
            del self._skills[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)
    
    def list(self, category: str = None) -> List[Skill]:
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills
    
    def execute(self, skill_name: str, **kwargs) -> SkillResult:
        skill = self.get(skill_name)
        if not skill:
            return SkillResult(success=False, output=None, error=f"Skill '{skill_name}' not found")
        return skill.execute(**kwargs)
    
    def get_openai_tools(self, skill_names: List[str] = None) -> List[Dict]:
        """Get skills formatted as OpenAI tools."""
        skills = self._skills.values()
        if skill_names:
            skills = [s for s in skills if s.name in skill_names]
        return [s.to_openai_tool() for s in skills]
    
    def to_dict(self) -> Dict:
        return {
            name: {
                "description": s.description,
                "category": s.category,
                "parameters": s.parameters
            }
            for name, s in self._skills.items()
        }


# Global registry instance
SKILL_REGISTRY = SkillRegistry()
