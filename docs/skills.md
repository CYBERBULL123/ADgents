# Creating Custom Skills

ADgents is designed to be highly extensible. The most powerful way to augment your agents is by teaching them entirely new skills (tools) through python code.

## The Skill Layer

Our backend Engine registers Skills dynamically. An Agent's `Persona` explicitly flags which Skills it has access to. When the ReAct loop starts, it hands the Agent a JSON-Schema representation of these Skills. The LLM decides if and when to return a "Tool Call" action, mapped exactly to your parameters.

## Generating Skills With AI

The easiest way to register a skill is entirely from the **Studio UI** (`http://localhost:8000/studio`). Head to the **Skills** tab.
1. Click the `+ Add Skill` menu.
2. Under "Generate with AI", type a description like: "A skill that checks current system info".
3. Click "Generate ✨".
4. The system will write standard-library compliant python code and automatically map the required parameters schema! 
5. Review the snippet, then click "Register". Your Agents can now use it natively!

### Constraints
- The UI generator prompts the LLM to only use built-in standard python libraries (like `urllib`, `re`, `json`) rather than 3rd party ones (`requests`, `beautifulsoup4`) natively, to prevent the `server.py` runtime from crashing due to `ModuleNotFoundError`s on unexpected imports.
- Make sure to restart your `start.py` or manually install packages inside your environment if you manually paste complex imports into the "Handler Code".

## Writing Custom Python Skills

If you write a skill manually, you must conform to this schema structure:

1. The function signature MUST be named `def handler(**kwargs):`
2. It MUST return a dictionary with at least the key `success` (Boolean).

```python
# A simple example:
import urllib.request
import json

def handler(target_url=None, **kwargs):
    if not target_url:
        return {'success': False, 'message': 'No URL provided'}
    
    try:
        # Example fetching data
        req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
        
        return {'success': True, 'extracted_data': data}
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

### Registering Manually
Provide the matching mapping of arguments so the LLM understands when to trigger the payload:

```json
{
  "type": "object",
  "properties": {
    "target_url": {
      "type": "string",
      "description": "The URL to fetch the JSON from"
    }
  },
  "required": [
    "target_url"
  ]
}
```

The system will instantly parse the code mapping and your Agents can begin utilizing this custom implementation in their autonomous tasks right away.
