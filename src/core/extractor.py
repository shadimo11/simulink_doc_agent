import os
import sys
import tkinter as tk
from tkinter import filedialog
import matlab.engine
import json

# Ensure you have your Pydantic models defined in schemas.py
from .schemas import (
    SimulinkBlock, 
    SimulinkSubsystem, 
    PortInterface, 
    StateflowChart, 
    StateflowState, 
    StateflowTransition, 
    StateflowVariable
)

class SimulinkExtractionEngine:
    def __init__(self, model_name: str, model_dir: str):
        """Initializes the MATLAB Engine, registers the dynamic path, and loads the target model."""
        self.model_name = model_name
        
        print("[INFO] Booting Headless MATLAB Engine. This may take a moment...")
        self.eng = matlab.engine.start_matlab()
        
        # Inject the path into the *active* engine session before loading the system
        print(f"[INFO] Registering dynamic path in active session: {model_dir}")
        self.eng.addpath(model_dir, nargout=0)
        
        print(f"[INFO] Loading {self.model_name} into memory...")
        self.eng.load_system(self.model_name, nargout=0)
        
        print("[INFO] Forcing compile state to evaluate parameters...")
        self.eng.eval(f"set_param('{self.model_name}', 'SimulationCommand', 'update');", nargout=0)

    def extract_port(self, port_path: str) -> PortInterface:
        """Extracts interface boundaries, prioritizing compile-time evaluations."""
        port_type = str(self.eng.get_param(port_path, "BlockType"))
        name = str(self.eng.get_param(port_path, "Name"))
        
        # Baseline fallback
        data_type = str(self.eng.get_param(port_path, "OutDataTypeStr"))
        dimensions = str(self.eng.get_param(port_path, "PortDimensions"))
        
        try:
            handles = self.eng.get_param(port_path, "PortHandles")
            target_handle = None
            
            if port_type.lower() == "inport" and handles.get("Outport"):
                target_handle = handles["Outport"]
            elif port_type.lower() == "outport" and handles.get("Inport"):
                target_handle = handles["Inport"]
                
            if target_handle:
                if isinstance(target_handle, list) or type(target_handle).__name__ == 'double':
                    handle_id = float(target_handle[0][0] if hasattr(target_handle[0], '__iter__') else target_handle[0])
                else:
                    handle_id = float(target_handle)

                data_type = str(self.eng.get_param(handle_id, "CompiledPortDataType"))
                
                raw_dims = self.eng.get_param(handle_id, "CompiledPortDimensions")
                if hasattr(raw_dims, '__iter__'):
                    flat_dims = [int(dim[0] if hasattr(dim, '__iter__') else dim) for dim in raw_dims]
                    dimensions = str(flat_dims[1:]) if len(flat_dims) > 1 else str(flat_dims)
                else:
                    dimensions = str(int(raw_dims))
                
        except Exception as e:
            print(f"[WARN] Compile-time extraction bypassed for {port_path}. Reason: {e}")
            
        return PortInterface(
            name=name,
            port_type=port_type,
            data_type=data_type,
            dimensions=dimensions
        )

    def extract_block(self, block_path: str) -> SimulinkBlock:
        """
        Extracts standard synchronous parameters and asynchronous dashboard bindings 
        into a validated Pydantic model.
        """
        block_type = str(self.eng.get_param(block_path, "BlockType"))
        name = str(self.eng.get_param(block_path, "Name"))
        
        parameters = {}
        b_type_lower = block_type.lower()
        
        # 1. Standard Synchronous Blocks
        if b_type_lower == "gain":
            parameters["Gain"] = str(self.eng.get_param(block_path, "Gain"))
        elif b_type_lower == "constant":
            parameters["Value"] = str(self.eng.get_param(block_path, "Value"))
            
        # 2. Asynchronous Dashboard / HMI Blocks
        ui_keywords = ["knob", "switch", "lamp", "gauge", "dashboard", "hmi"]
        
        if any(keyword in b_type_lower for keyword in ui_keywords):
            try:
                binding_obj = self.eng.get_param(block_path, "Binding")
                parameters["Bound_Element"] = str(binding_obj)
            except Exception:
                try:
                    state_name = self.eng.get_param(block_path, "StateName")
                    parameters["StateName"] = str(state_name)
                except Exception as e:
                    print(f"[WARN] Dashboard block '{name}' is unbound or inaccessible: {e}")
                    parameters["Binding"] = "Unresolved"
                    
        return SimulinkBlock(
            name=name,
            block_type=block_type,
            path=str(block_path),
            parameters=parameters
        )

    def extract_chart(self, chart_path: str) -> StateflowChart:
        """
        Orchestrates an internal MATLAB workspace query to bypass IPC latency 
        and extract the finite state machine topology via sfroot.
        """
        name = str(self.eng.get_param(chart_path, "Name"))
        print(f"[PARSE] Intercepting Stateflow FSM: {name}")
        
        self.eng.workspace['target_chart_path'] = chart_path
        self.eng.eval("rt = sfroot;", nargout=0)
        self.eng.eval("chartObj = rt.find('-isa', 'Stateflow.Chart', 'Path', target_chart_path);", nargout=0)
        
        # 1. Extract Variables (Data)
        self.eng.eval("dataObjs = chartObj.find('-isa', 'Stateflow.Data');", nargout=0)
        var_count = int(self.eng.eval("length(dataObjs);", nargout=1))
        
        variables = []
        for i in range(1, var_count + 1):
            self.eng.workspace['idx'] = i
            v_name = str(self.eng.eval("dataObjs(idx).Name;", nargout=1))
            v_scope = str(self.eng.eval("dataObjs(idx).Scope;", nargout=1))
            v_type = str(self.eng.eval("dataObjs(idx).DataType;", nargout=1))
            
            variables.append(StateflowVariable(name=v_name, scope=v_scope, data_type=v_type))

        # 2. Extract States & Actions
        self.eng.eval("stateObjs = chartObj.find('-isa', 'Stateflow.State');", nargout=0)
        state_count = int(self.eng.eval("length(stateObjs);", nargout=1))
        
        states = []
        for i in range(1, state_count + 1):
            self.eng.workspace['idx'] = i
            s_name = str(self.eng.eval("stateObjs(idx).Name;", nargout=1))
            entry_act = str(self.eng.eval("stateObjs(idx).EntryAction;", nargout=1)) or None
            during_act = str(self.eng.eval("stateObjs(idx).DuringAction;", nargout=1)) or None
            exit_act = str(self.eng.eval("stateObjs(idx).ExitAction;", nargout=1)) or None
            
            states.append(StateflowState(
                name=s_name, 
                entry_action=entry_act, 
                during_action=during_act, 
                exit_action=exit_act
            ))

        # 3. Extract Transitions (Edge-List Graph)
        self.eng.eval("transObjs = chartObj.find('-isa', 'Stateflow.Transition');", nargout=0)
        trans_count = int(self.eng.eval("length(transObjs);", nargout=1))
        
        transitions = []
        for i in range(1, trans_count + 1):
            self.eng.workspace['idx'] = i
            
            self.eng.eval("if isempty(transObjs(idx).Source), src_res=''; else, src_res=transObjs(idx).Source.Name; end;", nargout=0)
            src = str(self.eng.eval("src_res;", nargout=1)) or None
            
            self.eng.eval("if isempty(transObjs(idx).Destination), dst_res=''; else, dst_res=transObjs(idx).Destination.Name; end;", nargout=0)
            dst = str(self.eng.eval("dst_res;", nargout=1)) or None
            
            label = str(self.eng.eval("transObjs(idx).LabelString;", nargout=1))
            
            condition, cond_act, trans_act = None, None, None
            if label:
                if '[' in label and ']' in label:
                    condition = label.split('[')[1].split(']')[0]
                if '{' in label and '}' in label:
                    cond_act = label.split('{')[1].split('}')[0]
                if '/' in label:
                    trans_act = label.split('/')[-1].strip()

            transitions.append(StateflowTransition(
                source_state=src,
                destination_state=dst,
                trigger_event=label,
                condition=condition,
                condition_action=cond_act,
                transition_action=trans_act
            ))

        self.eng.eval("clear target_chart_path chartObj dataObjs stateObjs transObjs idx res src_res dst_res;", nargout=0)

        return StateflowChart(
            name=name,
            path=chart_path,
            variables=variables,
            states=states,
            transitions=transitions
        )

    def extract_topology(self, current_scope: str) -> list:
        """
        Uses an internal MATLAB script to safely parse PortConnectivity structs
        and serialize the graph edges into a JSON string to bypass IPC limits.
        """
        script = """
        blks = find_system(scope, 'SearchDepth', 1, 'Type', 'block');
        blks = blks(~strcmp(blks, scope)); % Exclude the subsystem root itself
        conns = {};
        for i = 1:length(blks)
            blk = blks{i};
            try
                pc = get_param(blk, 'PortConnectivity');
                blk_name = get_param(blk, 'Name');
                for j = 1:length(pc)
                    port = pc(j);
                    if ~isempty(port.DstBlock)
                        for k = 1:length(port.DstBlock)
                            dst_name = get_param(port.DstBlock(k), 'Name');
                            % Create an edge dictionary
                            edge = struct('source_block', blk_name, 'source_port', port.Type, 'destination_block', dst_name);
                            conns{end+1} = edge;
                        end
                    end
                end
            catch
                % Ignore blocks that do not support standard PortConnectivity
            end
        end
        res_json = jsonencode(conns);
        """
        self.eng.workspace['scope'] = current_scope
        self.eng.eval(script, nargout=0)
        
        raw_json = str(self.eng.workspace['res_json'])
        
        # If the JSON is valid and not empty ('[]'), parse it into Pydantic-ready dicts
        import json
        if raw_json and raw_json != "[]":
            return json.loads(raw_json)
        return []

    def traverse_subsystem(self, current_scope: str) -> SimulinkSubsystem:
        """Recursively maps the directed acyclic graph into Pydantic containers."""
        print(f"[PARSE] Mapping hierarchy: {current_scope}")
        
        all_blocks = self.eng.find_system(current_scope, "SearchDepth", 1, nargout=1)
        if all_blocks and all_blocks[0] == current_scope:
            all_blocks.pop(0)
            
        ports = []
        blocks = []
        charts = []
        child_subsystems = []
        
        for block in all_blocks:
            normalized_b_type = str(self.eng.get_param(block, "BlockType")).lower()
            
            if normalized_b_type == "subsystem":
                # --- DETERMINISTIC FSM DETECTION BOUNDARY ---
                is_stateflow = False
                try:
                    sf_type = str(self.eng.get_param(block, "SFBlockType")).lower()
                    if sf_type in ["chart", "state transition table", "truth table"]:
                        is_stateflow = True
                except Exception:
                    pass
                
                if is_stateflow:
                    charts.append(self.extract_chart(block))
                else:
                    child_subsystems.append(self.traverse_subsystem(block))
                    
            elif normalized_b_type in ["inport", "outport"]:
                ports.append(self.extract_port(block))
            else:
                blocks.append(self.extract_block(block))
                
        topology = self.extract_topology(current_scope)
        return SimulinkSubsystem(
            name=str(self.eng.get_param(current_scope, "Name")),
            path=str(current_scope),
            ports=ports,
            blocks=blocks,
            charts=charts,
            child_subsystems=child_subsystems,
            lines=topology
        )

    def extract_model(self) -> dict:
        """Wraps the recursively traversed root into the final AST payload."""
        root_data = self.traverse_subsystem(self.model_name)
        
        # Updated for Pydantic V2 compliance
        return {
            "toolchain_version": "1.0.0",
            "target_model": self.model_name,
            "root_hierarchy": root_data.model_dump() if hasattr(root_data, 'model_dump') else root_data
        }


def select_model_file() -> str:
    """Invokes a native OS dialog to select a Simulink model."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True) 
    
    file_path = filedialog.askopenfilename(
        title="Select Simulink Target Model",
        filetypes=[("Simulink Models", "*.slx"), ("Legacy Models", "*.mdl")]
    )
    
    root.destroy()
    return file_path


if __name__ == "__main__":
    print("=== Initiating Simulink Extraction Engine ===")
    
    target_filepath = select_model_file()
    if not target_filepath:
        print("[WARN] Execution aborted: No file selected.")
        sys.exit(0)
        
    model_dir = os.path.dirname(target_filepath)
    model_name = os.path.splitext(os.path.basename(target_filepath))[0]
    
    print(f"[INFO] Target acquired: {model_name}")
    print(f"[INFO] Registering dynamic path: {model_dir}")
    
    try:
        # Pass both the name and directory to a single, unified engine session
        extractor = SimulinkExtractionEngine(model_name, model_dir)
        
        # Execute Pipeline
        ast = extractor.extract_model()
        
        out_file = f"{model_name}_ast.json"
        with open(out_file, "w") as f:
            # Updated for Pydantic V2 compliance
            json.dump(ast, f, indent=4, default=lambda o: o.model_dump() if hasattr(o, 'model_dump') else o.__dict__)
            
        print(f"[SUCCESS] AST serialized cleanly and saved to {out_file}")
        
    except Exception as e:
        print(f"\n[FATAL] Pipeline execution fractured: {e}\n")
    finally:
        print("[INFO] Releasing compile lock and terminating engine...")
        if 'extractor' in locals() and hasattr(extractor, 'eng'):
            try:
                extractor.eng.eval(f"set_param('{model_name}', 'SimulationCommand', 'stop');", nargout=0)
                extractor.eng.close_system(model_name, 0, nargout=0)
            except Exception:
                pass
            extractor.eng.quit()
        print("=== Test Sequence Terminated ===")