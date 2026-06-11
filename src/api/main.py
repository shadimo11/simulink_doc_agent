import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

# Calculate absolute paths dynamically
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Inject root into sys.path to allow absolute imports now that __init__ files are present
sys.path.append(str(PROJECT_ROOT))

from src.agent.engine import SimulinkAgentEngine

# Read from environment, fallback to default if not provided
env_md_path = os.getenv("TARGET_MD_PATH")
if env_md_path:
    TARGET_MD = Path(env_md_path)
else:
    TARGET_MD = PROJECT_ROOT / "data" / "outputs" / "untitled1_documentation.md"

# Global memory reference for the singleton Agent
agent_singleton = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Service lifecycle manager.
    Loads the Vector Database and LLM into memory exactly once at server startup.
    """
    global agent_singleton
    if not TARGET_MD.exists():
        raise RuntimeError(f"[FATAL] Target documentation not found at: {TARGET_MD}")
    
    print("[INFO] Booting FastAPI Network Boundary...")
    print(f"[INFO] Initializing Simulink Intelligence Agent from {TARGET_MD}...")
    
    # Instantiate the agent (triggers ChromaDB ingestion and Google API authentication)
    agent_singleton = SimulinkAgentEngine(str(TARGET_MD))
    print("[SUCCESS] Agent loaded into RAM. Awaiting network requests.")
    
    yield # Server is active and accepting connections
    
    # Teardown logic
    print("[INFO] Shutting down service and releasing resources...")

# Initialize the API Application
app = FastAPI(
    title="Simulink Doc Agent API",
    description="Asynchronous MBD Systems Engineering RAG Pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# Enforce strict input schema
class QueryRequest(BaseModel):
    user_query: str

@app.post("/api/v1/query", summary="Query the Simulink AST")
async def ask_agent(request: QueryRequest):
    """
    Accepts a user query, yields the blocking execution to a background thread,
    and returns the systems engineering analysis.
    """
    global agent_singleton
    if not agent_singleton:
        raise HTTPException(status_code=503, detail="Agent logic engine is uninitialized.")
    
    try:
        # Delegate blocking LangChain/Google GenAI calls to the threadpool
        response = await run_in_threadpool(agent_singleton.query, request.user_query)
        return {"response": response, "status": "success"}
    except Exception as e:
        print(f"\n[ERROR] Inference Pipeline Fractured: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Local development server boot configuration
    print("=== Spawning Uvicorn ASGI Server ===")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)