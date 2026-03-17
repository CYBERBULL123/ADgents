"""
ADgents Startup Script
Validates the environment and starts the server.
"""
import sys
import os
from pathlib import Path

def check_environment():
    """Pre-flight checks."""
    print("🔍 Checking environment...")
    
    # Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Required packages
    packages = ["fastapi", "uvicorn", "pydantic", "httpx", "sqlalchemy", "aiofiles"]
    missing = []
    for pkg in packages:
        try:
            __import__(pkg.replace("-","_"))
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print(f"   Run: python -m pip install {' '.join(missing)}")
        sys.exit(1)
    print(f"✅ All required packages installed")
    
    # Create data directories
    for d in ["data", "data/db", "data/files"]:
        Path(d).mkdir(exist_ok=True)
    print("✅ Data directories ready")
    
    # Check .env
    env_file = Path(".env")
    if not env_file.exists():
        example = Path(".env.example")
        if example.exists():
            import shutil
            shutil.copy(example, env_file)
            print("📝 Created .env from .env.example — please add your API keys!")
    
    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment loaded")
    except ImportError:
        pass
    
    # Check API keys
    has_key = any([
        os.getenv("OPENAI_API_KEY"),
        os.getenv("GEMINI_API_KEY"),
        os.getenv("ANTHROPIC_API_KEY")
    ])
    
    if not has_key:
        print("⚠️  No LLM API keys found. Running in MOCK mode (responses will be placeholder text)")
        print("   Add OPENAI_API_KEY or GEMINI_API_KEY to your .env file for real AI responses")
    else:
        print("✅ LLM API key found")
    
    print("\n🚀 Environment OK!\n")


if __name__ == "__main__":
    import uvicorn
    
    os.chdir(Path(__file__).parent)
    check_environment()
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    print("=" * 50)
    print("⚡ ADgents — Autonomous Agent Platform")
    print("=" * 50)
    print(f"🌐 API:    http://localhost:{port}")
    print(f"🎨 Studio: http://localhost:{port}/studio")
    print(f"📚 Docs:   http://localhost:{port}/docs")
    print("=" * 50)
    print("Press Ctrl+C to stop\n")
    
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
