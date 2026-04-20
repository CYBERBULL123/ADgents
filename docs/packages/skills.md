# Custom Skills Guide

Learn how to create and integrate custom skills into ADgents agents from the pip package.

## Table of Contents

1. [What is a Skill?](#what-is-a-skill)
2. [Built-in Skills](#built-in-skills)
3. [Quick Start](#quick-start)
4. [Skill Structure](#skill-structure)
5. [Skill Categories](#skill-categories)
6. [Using Skills in Agents](#using-skills-in-agents)
7. [Advanced Patterns](#advanced-patterns)
8. [Testing Skills](#testing-skills)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## What is a Skill?

A **skill** is a Python function that an agent can call to accomplish specific tasks. Skills give your agents agency to:

- Execute code
- Call external APIs
- Read/write files
- Interact with databases
- Perform calculations
- Process data
- Send notifications
- And more!

Skills are registered with ADgents and become available to all agents in your application.

## Built-in Skills

ADgents includes these ready-to-use skills:

| Skill | Description | Input | Output |
|-------|-------------|-------|--------|
| `web_search` | Search the internet | `query: str` | `results: str` |
| `code_execute` | Run Python code safely | `code: str` | `result: str` |
| `file_read` | Read file contents | `path: str` | `content: str` |
| `file_write` | Write to files | `path: str, content: str` | `success: bool` |
| `api_call` | Make HTTP requests | `url: str, method: str, data: dict` | `response: dict` |
| `list_directory` | Browse directories | `path: str` | `files: list` |
| `get_datetime` | Get current date/time | - | `timestamp: str` |
| `calculate` | Evaluate math expressions | `expression: str` | `result: float` |
| `json_parse` | Parse JSON data | `data: str` | `parsed: dict` |
| `summarize_text` | Summarize text | `text: str` | `summary: str` |

## Quick Start

### 1. Install ADgents

```bash
pip install adgents
```

### 2. Create Your First Skill

```python
from adgents.core.skills import register_skill

@register_skill(
    name="greet_user",
    description="Greet a user by name",
    parameters={
        "name": "The user's name",
        "tone": "Greeting tone: friendly, formal, or casual"
    },
    return_type="str"
)
def greet_user(name: str, tone: str = "friendly") -> str:
    """Generate a greeting for a user."""
    greetings = {
        "friendly": f"Hey there, {name}! 👋",
        "formal": f"Greetings, {name}.",
        "casual": f"Yo {name}!"
    }
    return greetings.get(tone, greetings["friendly"])
```

### 3. Use the Skill in an Agent

```python
from adgents.core.agent import Agent
from adgents.core.persona import Persona

agent = Agent(
    persona=Persona(
        name="Greeter",
        role="Friendly Assistant",
        expertise_domains=["Greetings"]
    )
)

# Agent can now use the greet_user skill
response = agent.chat("Please greet John in a formal way")
```

## Skill Structure

### Basic Decorator Properties

```python
from adgents.core.skills import register_skill
from typing import Dict, Any

@register_skill(
    name="skill_name",                    # Unique skill identifier
    description="What this skill does",   # Brief description
    parameters={
        "param1": "Description of param1",
        "param2": "Description of param2",
    },
    return_type="str",                    # Return type hint
    category="data_processing",           # Optional: skill category
    version="1.0.0",                      # Optional: skill version
    dependencies=["requests", "pandas"],  # Optional: required packages
    timeout=30                            # Optional: execution timeout in seconds
)
def skill_name(param1: str, param2: int) -> str:
    """Implement your skill logic here."""
    return f"Result: {param1} {param2}"
```

### Complete Skill Template

```python
from adgents.core.skills import register_skill
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

@register_skill(
    name="my_skill",
    description="Complete skill description",
    parameters={
        "input_data": "What the skill accepts",
        "options": "Optional parameters"
    },
    return_type="Dict",
    category="general",
    version="1.0.0"
)
def my_skill(
    input_data: str,
    options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Complete skill implementation.
    
    Args:
        input_data: The main input
        options: Optional configuration dictionary
        
    Returns:
        Dictionary with success, data, and any errors
    """
    try:
        # Validate inputs
        if not input_data:
            return {
                "success": False,
                "error": "input_data is required"
            }
        
        options = options or {}
        
        # Process the input
        result = process_data(input_data, options)
        
        # Return structure
        return {
            "success": True,
            "data": result,
            "metadata": {
                "processed_at": get_timestamp(),
                "source": "my_skill"
            }
        }
    
    except Exception as e:
        logger.error(f"Skill error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }

def process_data(data: str, options: Dict) -> str:
    """Helper function for processing."""
    return f"Processed: {data}"

def get_timestamp() -> str:
    """Get current timestamp."""
    from datetime import datetime
    return datetime.now().isoformat()
```

## Skill Categories

Organize skills by category for better management and discovery.

### 1. Data Processing Skills

Process, transform, and analyze data.

```python
from adgents.core.skills import register_skill
import pandas as pd
import json

@register_skill(
    name="parse_csv",
    description="Parse CSV content and return as JSON",
    parameters={
        "csv_content": "CSV data as string",
        "headers": "Whether first row is headers"
    },
    return_type="Dict",
    category="data_processing"
)
def parse_csv(csv_content: str, headers: bool = True) -> Dict:
    """Parse CSV and return structured data."""
    try:
        from io import StringIO
        df = pd.read_csv(StringIO(csv_content), header=0 if headers else None)
        return {
            "success": True,
            "data": df.to_dict(orient='records'),
            "row_count": len(df)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_skill(
    name="aggregate_data",
    description="Aggregate data by key and calculate statistics",
    parameters={
        "data": "List of dictionaries",
        "group_by": "Key to group by",
        "aggregate_field": "Field to aggregate",
        "method": "Aggregation method: sum, avg, count, min, max"
    },
    return_type="Dict",
    category="data_processing"
)
def aggregate_data(
    data: list,
    group_by: str,
    aggregate_field: str,
    method: str = "sum"
) -> Dict:
    """Aggregate data using pandas."""
    try:
        df = pd.DataFrame(data)
        if method == "sum":
            result = df.groupby(group_by)[aggregate_field].sum()
        elif method == "avg":
            result = df.groupby(group_by)[aggregate_field].mean()
        elif method == "count":
            result = df.groupby(group_by)[aggregate_field].count()
        elif method == "min":
            result = df.groupby(group_by)[aggregate_field].min()
        elif method == "max":
            result = df.groupby(group_by)[aggregate_field].max()
        else:
            return {"success": False, "error": f"Unknown method: {method}"}
        
        return {
            "success": True,
            "data": result.to_dict()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 2. API Integration Skills

Call external APIs and integrate services.

```python
@register_skill(
    name="fetch_weather",
    description="Fetch weather data from OpenWeatherMap API",
    parameters={
        "city": "City name",
        "units": "Temperature units: metric or imperial"
    },
    return_type="Dict",
    category="api_integration"
)
def fetch_weather(city: str, units: str = "metric") -> Dict:
    """Get weather for a city."""
    import requests
    import os
    
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"success": False, "error": "API key not configured"}
    
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "units": units,
            "appid": api_key
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return {
            "success": True,
            "data": {
                "city": data.get("name"),
                "temperature": data["main"].get("temp"),
                "description": data["weather"][0].get("description"),
                "humidity": data["main"].get("humidity")
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_skill(
    name="post_to_slack",
    description="Send a message to a Slack channel",
    parameters={
        "channel": "Slack channel name or ID",
        "message": "Message to send",
        "thread_ts": "Thread timestamp (optional)"
    },
    return_type="Dict",
    category="api_integration"
)
def post_to_slack(channel: str, message: str, thread_ts: str = None) -> Dict:
    """Post message to Slack."""
    import requests
    import os
    
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return {"success": False, "error": "Slack webhook not configured"}
    
    try:
        payload = {
            "channel": channel,
            "text": message
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        
        return {"success": True, "data": "Message posted"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 3. Database Skills

Query, insert, and update data in databases.

```python
@register_skill(
    name="query_database",
    description="Execute SQL query and return results",
    parameters={
        "query": "SQL query to execute",
        "database": "Database identifier",
        "limit": "Max rows to return"
    },
    return_type="Dict",
    category="database"
)
def query_database(query: str, database: str = "default", limit: int = 100) -> Dict:
    """Execute database query."""
    import sqlite3
    import os
    
    try:
        db_path = os.getenv(f"DB_{database.upper()}_PATH", "data.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Prevent SQL injection - basic protection
        if any(keyword in query.upper() for keyword in ["DROP", "DELETE FROM", "TRUNCATE"]):
            return {"success": False, "error": "Destructive queries not allowed"}
        
        cursor.execute(query)
        rows = cursor.fetchall()[:limit]
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        
        # Convert to list of dicts
        results = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        
        return {
            "success": True,
            "data": results,
            "row_count": len(results)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_skill(
    name="insert_record",
    description="Insert a record into the database",
    parameters={
        "table": "Table name",
        "record": "Record data as dictionary",
        "database": "Database identifier"
    },
    return_type="Dict",
    category="database"
)
def insert_record(table: str, record: dict, database: str = "default") -> Dict:
    """Insert record into database."""
    import sqlite3
    import os
    
    try:
        db_path = os.getenv(f"DB_{database.upper()}_PATH", "data.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        columns = ", ".join(record.keys())
        placeholders = ", ".join(["?" for _ in record.keys()])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        cursor.execute(query, list(record.values()))
        conn.commit()
        
        record_id = cursor.lastrowid
        conn.close()
        
        return {
            "success": True,
            "data": {"id": record_id},
            "message": f"Record inserted with ID: {record_id}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 4. Async Skills

Long-running operations with async/await.

```python
from adgents.core.skills import register_skill
import asyncio

@register_skill(
    name="batch_process",
    description="Process items asynchronously",
    parameters={
        "items": "List of items to process",
        "delay": "Delay between items in seconds"
    },
    return_type="Dict",
    category="async"
)
def batch_process(items: list, delay: float = 0.5) -> Dict:
    """Process items with async support."""
    async def process_async():
        results = []
        for i, item in enumerate(items):
            await asyncio.sleep(delay)
            results.append(f"Processed: {item}")
        return results
    
    try:
        # Run async function
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(process_async())
        
        return {
            "success": True,
            "data": results,
            "processed_count": len(results)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 5. Conditional Skills

Skills that execute based on conditions.

```python
@register_skill(
    name="validate_and_process",
    description="Validate input and process if valid",
    parameters={
        "data": "Data to validate",
        "rules": "Validation rules as dictionary"
    },
    return_type="Dict",
    category="conditional"
)
def validate_and_process(data: dict, rules: dict) -> Dict:
    """Validate data against rules before processing."""
    errors = []
    
    # Validate required fields
    for field in rules.get("required", []):
        if field not in data:
            errors.append(f"Required field missing: {field}")
    
    # Validate field types
    for field, expected_type in rules.get("types", {}).items():
        if field in data:
            if not isinstance(data[field], eval(expected_type)):
                errors.append(f"Field {field} has wrong type")
    
    if errors:
        return {
            "success": False,
            "errors": errors,
            "data": None
        }
    
    # Process if valid
    result = process_valid_data(data)
    
    return {
        "success": True,
        "data": result,
        "validated": True
    }

def process_valid_data(data: dict) -> dict:
    """Process validated data."""
    return {
        "processed": True,
        "fields_count": len(data),
        "keys": list(data.keys())
    }
```

## Using Skills in Agents

### Register Skills Globally

```python
from adgents.core.skills import register_skill, SKILL_REGISTRY

# Create your skills
@register_skill(
    name="calculate_total",
    description="Calculate total from list of numbers",
    parameters={"numbers": "List of numbers"}
)
def calculate_total(numbers: list) -> Dict:
    return {"success": True, "total": sum(numbers)}

@register_skill(
    name="format_currency",
    description="Format number as currency",
    parameters={"amount": "Amount to format"}
)
def format_currency(amount: float) -> Dict:
    return {"success": True, "formatted": f"${amount:,.2f}"}

# Skills are now available to all agents
print("Registered skills:", list(SKILL_REGISTRY._skills.keys()))
```

### Use Skills in Agent Tasks

```python
from adgents.core.agent import Agent
from adgents.core.persona import Persona
from adgents.core.crew_manager import CrewManager

# Create agent with persona
agent = Agent(
    persona=Persona(
        name="Calculator",
        role="Financial Analyst",
        expertise_domains=["Finance", "Mathematics"]
    )
)

# Agent can now use registered skills
response = agent.chat(
    "Calculate the total of [100, 200, 300] and format it as currency"
)
print(response)
```

### Get Skill Information in Code

```python
from adgents.core.skills import SKILL_REGISTRY

# Get all skills
all_skills = SKILL_REGISTRY._skills
print(f"Available skills: {list(all_skills.keys())}")

# Get specific skill
skill = SKILL_REGISTRY._skills.get("calculate_total")
if skill:
    print(f"Skill: {skill.name}")
    print(f"Description: {skill.description}")
    print(f"Parameters: {skill.parameters}")
```

## Advanced Patterns

### 1. Skill with State Management

```python
from adgents.core.skills import register_skill
from typing import Dict, Any

class SkillState:
    """Manage skill execution state."""
    def __init__(self):
        self.cache = {}
        self.call_count = 0
    
    def reset(self):
        self.cache.clear()
        self.call_count = 0

state = SkillState()

@register_skill(
    name="cached_lookup",
    description="Lookup with caching",
    parameters={"key": "Key to lookup"}
)
def cached_lookup(key: str) -> Dict:
    """Lookup with caching support."""
    state.call_count += 1
    
    if key in state.cache:
        return {
            "success": True,
            "data": state.cache[key],
            "cached": True
        }
    
    # Perform lookup
    result = expensive_lookup(key)
    state.cache[key] = result
    
    return {
        "success": True,
        "data": result,
        "cached": False
    }

def expensive_lookup(key: str) -> str:
    """Simulate expensive operation."""
    import time
    time.sleep(0.5)
    return f"Result for {key}"
```

### 2. Skill with Retry Logic

```python
from adgents.core.skills import register_skill
import time

@register_skill(
    name="resilient_api_call",
    description="API call with retry logic",
    parameters={
        "url": "URL to call",
        "max_retries": "Max retry attempts"
    }
)
def resilient_api_call(url: str, max_retries: int = 3) -> Dict:
    """Call API with retry logic."""
    import requests
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return {
                "success": True,
                "data": response.json(),
                "attempts": attempt + 1
            }
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                return {
                    "success": False,
                    "error": str(e),
                    "attempts": attempt + 1
                }
            # Exponential backoff
            wait_time = 2 ** attempt
            time.sleep(wait_time)
```

### 3. Skill Composition

```python
from adgents.core.skills import register_skill, SKILL_REGISTRY

@register_skill(
    name="compose_skills",
    description="Compose multiple skills in sequence",
    parameters={"input_data": "Initial input"}
)
def compose_skills(input_data: str) -> Dict:
    """Chain multiple skills together."""
    try:
        # Get skills from registry
        skill1 = SKILL_REGISTRY._skills.get("format_text")
        skill2 = SKILL_REGISTRY._skills.get("validate_text")
        
        # Execute in sequence
        result1 = skill1.func(input_data)
        if not result1["success"]:
            return {"success": False, "error": "Step 1 failed"}
        
        result2 = skill2.func(result1["data"])
        if not result2["success"]:
            return {"success": False, "error": "Step 2 failed"}
        
        return {
            "success": True,
            "data": result2["data"],
            "steps": 2
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 4. Skill Versioning

```python
from adgents.core.skills import register_skill

# Version 1.0
@register_skill(
    name="process_data",
    description="Process data (v1.0 - basic)",
    version="1.0.0",
    parameters={"data": "Input data"}
)
def process_data_v1(data: str) -> Dict:
    """Basic processing."""
    return {"success": True, "data": f"V1: {data}"}

# Version 2.0 (enhanced)
@register_skill(
    name="process_data_v2",
    description="Process data (v2.0 - enhanced)",
    version="2.0.0",
    parameters={"data": "Input data", "options": "Processing options"}
)
def process_data_v2(data: str, options: dict = None) -> Dict:
    """Enhanced processing with options."""
    options = options or {}
    return {"success": True, "data": f"V2: {data}", "options_applied": bool(options)}
```

## Testing Skills

### Unit Testing

```python
import pytest
from adgents.core.skills import register_skill

@register_skill(
    name="add_numbers",
    description="Add two numbers",
    parameters={"a": "First number", "b": "Second number"}
)
def add_numbers(a: float, b: float) -> Dict:
    """Add two numbers."""
    return {"success": True, "result": a + b}

# Test the skill
def test_add_numbers():
    from adgents.core.skills import SKILL_REGISTRY
    skill = SKILL_REGISTRY._skills.get("add_numbers")
    
    result = skill.func(5, 3)
    assert result["success"] is True
    assert result["result"] == 8

def test_add_numbers_with_floats():
    from adgents.core.skills import SKILL_REGISTRY
    skill = SKILL_REGISTRY._skills.get("add_numbers")
    
    result = skill.func(5.5, 3.2)
    assert result["success"] is True
    assert abs(result["result"] - 8.7) < 0.01
```

### Integration Testing

```python
import pytest
from adgents.core.agent import Agent
from adgents.core.persona import Persona

def test_agent_uses_skill():
    """Test that agent can use registered skills."""
    agent = Agent(
        persona=Persona(
            name="Tester",
            role="Test Agent",
            expertise_domains=["Testing"]
        )
    )
    
    # Agent should be able to use registered skills
    response = agent.chat("Please add 5 and 3")
    assert response is not None
    assert "8" in str(response)
```

## Best Practices

### 1. Error Handling

Always return consistent error format:

```python
@register_skill(
    name="safe_operation",
    description="Operation with proper error handling",
    parameters={"input": "Input data"}
)
def safe_operation(input: str) -> Dict:
    """Operation with error handling."""
    try:
        # Validate input
        if not isinstance(input, str):
            return {
                "success": False,
                "error": "Input must be string",
                "error_type": "validation_error"
            }
        
        # Perform operation
        result = perform_operation(input)
        
        return {
            "success": True,
            "data": result,
            "error": None
        }
    
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "value_error"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "unexpected_error"
        }

def perform_operation(data: str) -> str:
    """Perform the operation."""
    return data.upper()
```

### 2. Input Validation

Validate inputs thoroughly:

```python
@register_skill(
    name="validated_skill",
    description="Skill with input validation",
    parameters={
        "email": "Email address",
        "age": "Age in years"
    }
)
def validated_skill(email: str, age: int) -> Dict:
    """Skill with validation."""
    # Validate email
    if not is_valid_email(email):
        return {"success": False, "error": "Invalid email format"}
    
    # Validate age
    if not isinstance(age, int) or age < 0 or age > 150:
        return {"success": False, "error": "Invalid age"}
    
    return {"success": True, "data": "Validation passed"}

def is_valid_email(email: str) -> bool:
    """Simple email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

### 3. Documentation

Provide clear skill descriptions:

```python
@register_skill(
    name="well_documented_skill",
    description="Calculate factorial of a number",
    parameters={
        "number": "Non-negative integer to calculate factorial for"
    },
    return_type="Dict",
    category="math"
)
def well_documented_skill(number: int) -> Dict:
    """
    Calculate the factorial of a number.
    
    Args:
        number: Non-negative integer (0-20 recommended)
    
    Returns:
        Dictionary with:
        - success: bool, operation status
        - data: int, calculated factorial
        - error: str, error message if failed
    
    Examples:
        >>> well_documented_skill(5)
        {'success': True, 'data': 120}
        
        >>> well_documented_skill(-1)
        {'success': False, 'error': 'Number must be non-negative'}
    """
    if not isinstance(number, int) or number < 0:
        return {
            "success": False,
            "error": "Number must be a non-negative integer"
        }
    
    result = 1
    for i in range(2, number + 1):
        result *= i
    
    return {"success": True, "data": result}
```

### 4. Performance Considerations

```python
@register_skill(
    name="performant_skill",
    description="Skill with performance optimization",
    parameters={"data": "Large dataset"}
)
def performant_skill(data: list) -> Dict:
    """Skill with optimization."""
    import time
    start = time.time()
    
    # Use efficient algorithms
    # Set timeouts
    # Implement caching
    
    result = process_efficiently(data)
    
    duration = time.time() - start
    
    return {
        "success": True,
        "data": result,
        "execution_time_ms": round(duration * 1000, 2)
    }

def process_efficiently(data: list) -> list:
    """Process data efficiently."""
    # Use set for O(1) lookups instead of list
    # Use generators for large datasets
    # Avoid nested loops when possible
    return sorted(set(data))
```

## Troubleshooting

### Skill Not Found

**Problem:** Agent can't find your skill

**Solutions:**
- Ensure skill is registered using `@register_skill` decorator
- Import the module containing your skill before creating agents
- Check skill name matches exactly (case-sensitive)

```python
# Make sure to import your skills module
import my_skills  # This registers all skills in the module

from adgents.core.skills import SKILL_REGISTRY
print("Available:", list(SKILL_REGISTRY._skills.keys()))
```

### Skill Exception

**Problem:** Skill throws an error during execution

**Solution:** Add try-except and proper error handling

```python
@register_skill(
    name="safe_skill",
    description="Safe skill with error handling"
)
def safe_skill(data: str) -> Dict:
    try:
        result = risky_operation(data)
        return {"success": True, "data": result}
    except Exception as e:
        import logging
        logging.error(f"Skill error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "tip": "Check input format and parameters"
        }
```

### Skill Performance Issues

**Problem:** Skill runs too slowly

**Solutions:**
- Add timeout parameter
- Implement caching
- Use async/await for I/O operations
- Profile with `time.time()`

```python
@register_skill(
    name="fast_skill",
    description="Optimized skill",
    timeout=5  # 5 second timeout
)
def fast_skill(data: str) -> Dict:
    import time
    start = time.time()
    
    result = quick_operation(data)
    
    duration = time.time() - start
    if duration > 1.0:
        print(f"Warning: Skill took {duration}s")
    
    return {"success": True, "data": result}
```

## Next Steps

- [Integration Guide](integration.md) - Integrate skills into your app
- [API Reference](api_reference.md) - Complete API documentation
- [Advanced Features](advanced.md) - Memory, LLM routing, and more
- [Examples](../../EXAMPLES.md) - Real-world skill examples
