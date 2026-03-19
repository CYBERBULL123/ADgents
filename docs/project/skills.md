# Creating & Integrating Custom Skills

Learn how to create custom skills and extend agent capabilities.

## What is a Skill?

A skill is a Python function that an agent can call to accomplish tasks. Skills give agents agency to:

- Execute code
- Call APIs
- Read/write files
- Interact with databases
- Perform calculations
- Process data

## Built-in Skills

ADgents comes with these skills ready to use:

| Skill | Description | Returns |
|-------|-------------|---------|
| `web_search` | Search the internet | Search results (str) |
| `code_execute` | Run Python code | Execution result |
| `file_read` | Read file contents | File content (str) |
| `file_write` | Write to files | Success status (bool) |
| `api_call` | Make HTTP requests | Response JSON |
| `list_directory` | Browse directories | File listing (list) |
| `get_datetime` | Get current date/time | Datetime string |
| `calculate` | Evaluate math expressions | Numeric result |
| `json_parse` | Parse JSON data | Parsed object |
| `summarize_text` | Summarize text | Summary (str) |

## Creating a Custom Skill

### Basic Skill Structure

```python
from core.skills import register_skill
from typing import Dict, Any

@register_skill(
    name="my_skill",
    description="What this skill does",
    parameters={
        "param1": "Description of param1",
        "param2": "Description of param2"
    },
    return_type="str"
)
def my_skill(param1: str, param2: int) -> str:
    """Implement the skill."""
    result = f"Processing {param1} with {param2}"
    return result
```

### Complete Example: Email Skill

```python
from core.skills import register_skill
from typing import Dict, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@register_skill(
    name="send_email",
    description="Send an email to recipients",
    parameters={
        "to": "Email address or list of addresses",
        "subject": "Email subject line",
        "body": "Email body content",
        "cc": "(Optional) CC recipients",
        "bcc": "(Optional) BCC recipients"
    },
    return_type="Dict"
)
def send_email(
    to: str | List[str],
    subject: str,
    body: str,
    cc: List[str] = None,
    bcc: List[str] = None
) -> Dict[str, Any]:
    """Send email via SMTP."""
    
    import os
    from_email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    
    if not from_email or not password:
        return {
            "success": False,
            "error": "EMAIL_ADDRESS or EMAIL_PASSWORD not set"
        }
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to if isinstance(to, str) else ', '.join(to)
        if cc:
            msg['Cc'] = ', '.join(cc) if isinstance(cc, list) else cc
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, password)
        
        recipients = to if isinstance(to, list) else [to]
        if cc:
            recipients.extend(cc if isinstance(cc, list) else [cc])
        if bcc:
            recipients.extend(bcc if isinstance(bcc, list) else [bcc])
        
        server.sendmail(from_email, recipients, msg.as_string())
        server.quit()
        
        return {
            "success": True,
            "message": f"Email sent to {to}",
            "recipients": recipients
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

## Skill Categories

### Data Processing Skills

```python
@register_skill(
    name="process_csv",
    description="Process CSV file and return statistics",
    parameters={"file_path": "Path to CSV file"}
)
def process_csv(file_path: str) -> Dict:
    """Process CSV and compute statistics."""
    import pandas as pd
    
    try:
        df = pd.read_csv(file_path)
        return {
            "rows": len(df),
            "columns": list(df.columns),
            "dtypes": df.dtypes.to_dict(),
            "summary": df.describe().to_dict()
        }
    except Exception as e:
        return {"error": str(e)}

@register_skill(
    name="transform_data",
    description="Transform data with custom functions",
    parameters={
        "data": "Input data",
        "transformation": "Type: normalize, standardize, or aggregate"
    }
)
def transform_data(data: List[float], transformation: str) -> List[float]:
    """Transform numerical data."""
    import statistics
    
    if transformation == "normalize":
        min_val = min(data)
        max_val = max(data)
        span = max_val - min_val
        return [(x - min_val) / span for x in data]
    
    elif transformation == "standardize":
        mean = statistics.mean(data)
        stdev = statistics.stdev(data)
        return [(x - mean) / stdev for x in data]
    
    elif transformation == "aggregate":
        return [statistics.mean(data), statistics.median(data), statistics.stdev(data)]
    
    return data
```

### API Integration Skills

```python
@register_skill(
    name="call_external_api",
    description="Call external REST API",
    parameters={
        "url": "API endpoint URL",
        "method": "HTTP method (GET, POST, PUT, DELETE)",
        "headers": "(Optional) Request headers",
        "body": "(Optional) Request body"
    }
)
def call_external_api(
    url: str,
    method: str = "GET",
    headers: Dict = None,
    body: Dict = None
) -> Dict:
    """Call external API and return response."""
    import httpx
    import json
    
    try:
        with httpx.Client() as client:
            if method == "GET":
                response = client.get(url, headers=headers or {})
            elif method == "POST":
                response = client.post(url, headers=headers or {}, json=body)
            elif method == "PUT":
                response = client.put(url, headers=headers or {}, json=body)
            elif method == "DELETE":
                response = client.delete(url, headers=headers or {})
            else:
                return {"error": f"Unsupported method: {method}"}
            
            return {
                "status": response.status_code,
                "headers": dict(response.headers),
                "body": response.json() if response.headers.get('content-type') == 'application/json' else response.text
            }
    
    except Exception as e:
        return {"error": str(e)}

@register_skill(
    name="webhook_notify",
    description="Send notification to webhook",
    parameters={
        "webhook_url": "Webhook endpoint",
        "event": "Event type",
        "data": "Event data"
    }
)
def webhook_notify(webhook_url: str, event: str, data: Dict) -> Dict:
    """Send webhook notification."""
    import httpx
    
    try:
        with httpx.Client() as client:
            response = client.post(
                webhook_url,
                json={"event": event, "data": data}
            )
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Database Skills

```python
@register_skill(
    name="query_database",
    description="Query data from database",
    parameters={
        "db_url": "Database connection URL",
        "query": "SQL query",
        "params": "(Optional) Query parameters"
    }
)
def query_database(db_url: str, query: str, params: Dict = None) -> Dict:
    """Execute database query."""
    import sqlalchemy
    
    try:
        engine = sqlalchemy.create_engine(db_url)
        with engine.connect() as connection:
            result = connection.execute(
                sqlalchemy.text(query),
                params or {}
            )
            rows = [dict(row._mapping) for row in result]
            return {
                "success": True,
                "rows": rows,
                "count": len(rows)
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_skill(
    name="insert_records",
    description="Insert records into database",
    parameters={
        "db_url": "Database connection URL",
        "table": "Table name",
        "records": "List of record dictionaries"
    }
)
def insert_records(db_url: str, table: str, records: List[Dict]) -> Dict:
    """Insert records into database."""
    import sqlalchemy
    
    try:
        engine = sqlalchemy.create_engine(db_url)
        with engine.connect() as connection:
            connection.execute(
                sqlalchemy.insert(sqlalchemy.table(table)),
                records
            )
            connection.commit()
            return {
                "success": True,
                "inserted": len(records)
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Async Skills

```python
from core.skills import register_skill
import asyncio

@register_skill(
    name="async_fetch_data",
    description="Fetch data asynchronously",
    parameters={"urls": "List of URLs to fetch"},
    async_support=True
)
async def async_fetch_data(urls: List[str]) -> Dict:
    """Fetch multiple URLs concurrently."""
    import aiohttp
    
    async def fetch(session, url):
        try:
            async with session.get(url, timeout=10) as response:
                return {
                    "url": url,
                    "status": response.status,
                    "data": await response.text()
                }
        except Exception as e:
            return {"url": url, "error": str(e)}
    
    try:
        async with aiohttp.ClientSession() as session:
            tasks = [fetch(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            return {
                "success": True,
                "results": results
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Conditional Skills

Execute skills only under certain conditions:

```python
@register_skill(
    name="admin_command",
    description="Execute admin command",
    parameters={"command": "Admin command to execute"},
    conditions={
        "requires_permission": "admin",
        "enabled_in": ["production", "staging"],
        "min_autonomy_level": 4
    }
)
def admin_command(command: str) -> Dict:
    """Execute privileged command."""
    # Implementation
    return {"result": "Command executed"}
```

## Skill Validation

### Type Hints

Always use type hints for parameters and return values:

```python
@register_skill(
    name="typed_skill",
    parameters={
        "count": "Integer count",
        "items": "List of items",
        "config": "Configuration dictionary"
    }
)
def typed_skill(count: int, items: List[str], config: Dict) -> Dict:
    """Skill with proper type hints."""
    return {
        "count": count,
        "items_count": len(items),
        "config_keys": list(config.keys())
    }
```

### Error Handling

Always handle errors gracefully:

```python
@register_skill(
    name="safe_skill",
    description="Skill with error handling",
    parameters={"data": "Input data"}
)
def safe_skill(data: Any) -> Dict:
    """Safe skill with error handling."""
    try:
        # Process data
        result = str(data).upper()
        return {
            "success": True,
            "result": result
        }
    except TypeError as e:
        return {
            "success": False,
            "error": f"Type error: {str(e)}",
            "error_type": "TypeError"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
```

## Using Skills in Agents

### Automatic Skill Usage

Agents automatically discover and use registered skills:

```python
from core.agent import Agent
from core.persona import Persona

# Register a skill
from my_skills import send_email

# Agent will automatically use it
agent = Agent(persona=Persona(name="Assistant", role="Helper"))

# Agent calls send_email automatically
response = agent.chat(
    "Send an email to john@example.com with subject 'Hello' and body 'Hi there'"
)
```

### Task-Based Skill Usage

```python
# Agent chooses appropriate skills for the task
result = agent.run_task(
    "Read the data.csv file, calculate statistics for numeric columns, "
    "and send a summary to admin@example.com"
)
# Agent will: file_read → process_csv → send_email
```

### Manual Skill Invocation

```python
from core.skills import get_skill

# Manually call a skill
email_skill = get_skill("send_email")
result = email_skill(
    to="user@example.com",
    subject="Test",
    body="Hello"
)
```

## Skill Organization

### Project Structure

```
project/
├── skills/
│   ├── __init__.py
│   ├── data_processing.py    # Data-related skills
│   ├── api_integration.py    # API-related skills
│   ├── email.py              # Email skills
│   ├── database.py           # Database skills
│   └── custom.py             # Domain-specific skills
└── core/
```

### Register All Skills

```python
# skills/__init__.py
from .data_processing import *
from .api_integration import *
from .email import *
from .database import *
from .custom import *

# In main app
import skills  # This registers all skills
```

## Advanced Skills

### Skill Metadata

Add metadata to skills:

```python
@register_skill(
    name="advanced_skill",
    description="Advanced skill with metadata",
    parameters={"input": "Input data"},
    metadata={
        "version": "1.0.0",
        "author": "Your Name",
        "tags": ["data", "processing"],
        "performance": "high",
        "cost": "low"  # LLM API cost
    }
)
def advanced_skill(input: str) -> str:
    return f"Processed: {input}"
```

### Skill Versioning

```python
# Version 1
@register_skill(name="process_v1")
def process_v1(data: str) -> str:
    return data.upper()

# Version 2 (improved)
@register_skill(
    name="process_v2",
    metadata={"replaces": "process_v1"}
)
def process_v2(data: str) -> str:
    return data.upper().strip()

# Agents will prefer v2
```

### Skill Dependencies

```python
@register_skill(
    name="complex_skill",
    parameters={"data": "Data"},
    dependencies=["skill1", "skill2"]  # Requires these skills
)
def complex_skill(data: str) -> str:
    """Uses other skills internally."""
    # First use skill1
    intermediate = get_skill("skill1")(data)
    # Then use skill2
    result = get_skill("skill2")(intermediate)
    return result
```

### Tool Calling (Model-Native)

For compatible models (GPT-4, Claude, Gemini):

```python
@register_skill(
    name="model_native_skill",
    description="Skill using model-native tool calling",
    parameters={"query": "User query"},
    model_native=True  # Enable for GPT-4, Claude, Gemini
)
def model_native_skill(query: str) -> str:
    """Model can call this as a native tool."""
    return f"Result: {query}"
```

## Testing Skills

### Unit Tests

```python
import pytest
from skills.email import send_email

def test_send_email_success(mocker):
    """Test successful email send."""
    mock_smtp = mocker.patch('smtplib.SMTP')
    
    result = send_email(
        to="test@example.com",
        subject="Test",
        body="Test body"
    )
    
    assert result["success"] == True
    assert "sent to" in result["message"]

def test_send_email_missing_credentials(mocker):
    """Test missing credentials."""
    mocker.patch.dict('os.environ', {}, clear=True)
    
    result = send_email(
        to="test@example.com",
        subject="Test",
        body="Test"
    )
    
    assert result["success"] == False
    assert "not set" in result["error"]
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_skill_with_agent():
    """Test skill integration with agent."""
    from core.agent import Agent
    
    agent = Agent(persona=Persona(name="Test", role="Tester"))
    
    result = agent.chat(
        "Use the send_email skill to send test@example.com a message"
    )
    
    assert result is not None
```

## Best Practices

### 1. Clear Descriptions

```python
# ✅ Good
@register_skill(
    name="extract_emails",
    description="Extract email addresses from text using regex patterns. "
                "Returns a list of valid email addresses found.",
    parameters={"text": "Text to search for email addresses"}
)
def extract_emails(text: str) -> List[str]:
    pass

# ❌ Bad
@register_skill(name="extract", description="Extracts stuff")
def extract(text):
    pass
```

### 2. Comprehensive Error Handling

```python
@register_skill(...)
def safe_operation(data: str) -> Dict:
    try:
        # Main logic
        result = process(data)
        return {"success": True, "result": result}
    except ValueError as e:
        return {"success": False, "error": "Invalid input", "details": str(e)}
    except TimeoutError:
        return {"success": False, "error": "Operation timed out"}
    except Exception as e:
        # Log unexpected errors
        import logging
        logging.error(f"Unexpected error: {e}", exc_info=True)
        return {"success": False, "error": "Unexpected error occurred"}
```

### 3. Performance Optimization

```python
@register_skill(
    name="cached_operation",
    parameters={"query": "Search query"},
    metadata={"cache_results": True}
)
def cached_operation(query: str) -> Dict:
    """Cache results for performance."""
    from functools import lru_cache
    
    @lru_cache(maxsize=128)
    def _cached_search(q: str):
        # Expensive operation
        return search_database(q)
    
    return _cached_search(query)
```

### 4. Security Consideration

```python
@register_skill(
    name="secure_skill",
    parameters={"api_key": "API key (sensitive)"},
    metadata={"sensitive_params": ["api_key"]}
)
def secure_skill(api_key: str) -> Dict:
    """Use sensitive parameters safely."""
    # Don't log sensitive data
    import os
    
    # Use environment variables instead
    key = os.getenv("API_KEY")
    
    # Mask in logs
    masked_key = key[:4] + "..." + key[-4:] if key else "MISSING"
    logging.info(f"Using API key: {masked_key}")
```

## Skill Marketplace (Future)

Share and discover skills:

```python
# Coming soon: ADgents Skills Marketplace
# - Community-contributed skills
# - Verified and tested skills
# - Version management
# - One-click installation
```

## Troubleshooting

### Skill Not Being Called

```python
# Check if skill is registered
from core.skills import SKILL_REGISTRY

if "my_skill" not in SKILL_REGISTRY:
    print("Skill not registered")
else:
    print("Skill is registered")

# Check skill metadata
skill = SKILL_REGISTRY.get("my_skill")
print(f"Name: {skill.name}")
print(f"Description: {skill.description}")
```

### Skill Execution Errors

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test skill directly
from core.skills import get_skill

skill = get_skill("my_skill")
result = skill(param1="test")
print(f"Result: {result}")
```

## Next Steps

- [Integration Guide](integration.md) - Integrate into your projects
- [API Reference](api_reference.md) - Complete API documentation
- [Advanced Features](advanced.md) - Advanced patterns
- [Examples](../../../EXAMPLES.md) - Real-world examples
