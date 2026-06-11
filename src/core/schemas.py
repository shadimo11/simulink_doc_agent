from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PortInterface(BaseModel):
    """Defines the boundaries of a subsystem or block."""
    name: str
    port_type: str = Field(..., description="Must be 'Inport' or 'Outport'")
    data_type: str = Field(default="Inherit: auto", description="Evaluated compile-time data type")
    dimensions: str = Field(default="-1", description="Signal matrix dimensions")

class SimulinkBlock(BaseModel):
    """Represents a discrete functional node (e.g., Gain, Integrator, PID)."""
    name: str
    block_type: str
    path: str
    parameters: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Key-value pairs of block-specific mask parameters"
    )

class StateflowVariable(BaseModel):
    """Represents a data object within a Stateflow chart."""
    name: str
    scope: str = Field(..., description="e.g., 'Input', 'Output', 'Local', 'Constant'")
    data_type: str

class StateflowState(BaseModel):
    """Represents a discrete state node in a finite state machine."""
    name: str
    entry_action: Optional[str] = Field(default=None, description="Code executed upon entering the state")
    during_action: Optional[str] = Field(default=None, description="Code executed while state is active")
    exit_action: Optional[str] = Field(default=None, description="Code executed upon leaving the state")
    child_states: List['StateflowState'] = Field(default_factory=list)

class StateflowTransition(BaseModel):
    """Represents a directional edge between states, containing execution logic."""
    source_state: Optional[str] = Field(default=None, description="Origin state name. Null if default transition.")
    destination_state: str = Field(..., description="Target state name.")
    trigger_event: Optional[str] = Field(default=None, description="Event broadcasting the transition")
    condition: Optional[str] = Field(default=None, description="Boolean logic required to pass, e.g., [speed > 50]")
    condition_action: Optional[str] = Field(default=None, description="Executed immediately when condition is true")
    transition_action: Optional[str] = Field(default=None, description="Executed when transition path is fully taken")

class StateflowChart(BaseModel):
    """Represents the Stateflow engine block and its internal graph."""
    name: str
    path: str
    variables: List[StateflowVariable] = Field(default_factory=list)
    states: List[StateflowState] = Field(default_factory=list)
    transitions: List[StateflowTransition] = Field(default_factory=list)

class SignalLine(BaseModel):
    """Represents a topological connection (wire) between two blocks."""
    source_block: str
    source_port: str
    destination_block: str

class SimulinkSubsystem(BaseModel):
    """
    A recursive container representing architectural hierarchy.
    """
    name: str
    path: str
    ports: List[PortInterface] = Field(default_factory=list)
    blocks: List[SimulinkBlock] = Field(default_factory=list)
    charts: List[StateflowChart] = Field(default_factory=list)
    child_subsystems: List['SimulinkSubsystem'] = Field(default_factory=list)
    lines: List[SignalLine] = Field(default_factory=list)

class ModelAST(BaseModel):
    """The root Abstract Syntax Tree payload exported by the toolchain."""
    toolchain_version: str = "1.0.0"
    target_model: str
    root_hierarchy: SimulinkSubsystem

# Resolve recursive references for Pydantic v2
StateflowState.model_rebuild()
SimulinkSubsystem.model_rebuild()