import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from engine import SimulinkAgentEngine
from pathlib import Path

# Load settings
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TARGET_MD = PROJECT_ROOT / "data" / "outputs" / "untitled1_documentation.md"

# Global variable for the agent instance
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the Agent and load the Vector Store into memory
    global agent
    if not TARGET_MD.exists():
        raise RuntimeError(f"Target MD not found at {TARGET_MD}")
    
    print("[INFO] Initializing Agent API Engine...")
    agent = SimulinkAgentEngine(str(TARGET_MD))
    yield
    # Shutdown logic if needed

app = FastAPI(title="Simulink Doc Agent API", lifespan=lifespan)

class QueryRequest(BaseModel):
    user_query: str

@app.post("/api/v1/query")
async def ask_agent(request: QueryRequest):
    try:
        # Pass the request to the engine
        # We use run_in_executor to ensure blocking I/O doesn't hang the event loop
        response = await run_in_threadpool(agent.query, request.user_query)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Helper to bridge sync engine to async API
from starlette.concurrency import run_in_threadpool