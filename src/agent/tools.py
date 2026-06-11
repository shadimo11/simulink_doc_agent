"""
Agentic Tool Definitions for LangChain.
Planned expansion: Custom @tool functions to allow the LLM to trigger 
MATLAB SIL simulations dynamically or query external engineering docs.
"""
from langchain_core.tools import tool

@tool
def trigger_sil_simulation(model_name: str) -> str:
    """Triggers a Software-In-the-Loop simulation and returns the RMSE of the output."""
    raise NotImplementedError("SIL simulation orchestration not yet implemented.")

# Export available tools
AGENT_TOOLS = [trigger_sil_simulation]