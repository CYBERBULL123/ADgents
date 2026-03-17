import json
import time
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000/api"

def test_skill_generation(description):
    print(f"\n🧠 Generating skill for: '{description}'...")
    print("⏳ Waiting for LLM to write the code (this might take a few seconds)...")
    
    start_time = time.time()
    
    req = urllib.request.Request(
        f"{BASE_URL}/skills/generate",
        data=json.dumps({"description": description}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except urllib.error.URLError as e:
        print(f"❌ Error generating skill: {e}")
        return None
        
    code = data.get("code", "")
    print(f"✅ Code generated in {time.time() - start_time:.1f}s!\n")
    print("="*40)
    print(code)
    print("="*40)
    
    return code

def register_generated_skill(name, desc, code):
    print(f"\n🔌 Registering '{name}' to the live Skill Registry...")
    
    # Extract parameters dynamically or set a generic one for testing
    req = urllib.request.Request(
        f"{BASE_URL}/skills/register",
        data=json.dumps({
            "name": name,
            "description": desc,
            "category": "utility",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The input text"}
                },
                "required": ["text"]
            },
            "handler_code": code
        }).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print(f"✅ Success! Skill '{name}' is now live and ready for agents to use.")
            else:
                print(f"❌ Registration failed: {response.read().decode()}")
    except urllib.error.URLError as e:
         print(f"❌ Registration failed: {e}")

if __name__ == "__main__":
    print("🚀 Testing ADgents Dynamic Skill Generation\n")
    
    # Example: Simple math skill
    prompt = "A skill that takes a parameter 'text' which is a string, counts the number of words, and returns the result as 'word_count'."
    
    code = test_skill_generation(prompt)
    if code:
        print("\nAuto-registering this skill live into ADgents...")
        register_generated_skill("word_counter", "Counts the words in a given text string.", code)
