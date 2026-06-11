import os
import sys
import uvicorn
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import json

from src.core.extractor import SimulinkExtractionEngine
from src.generator.engine import MarkdownGenerator

# Define root paths
PROJECT_ROOT = Path(__file__).resolve().parent

def select_target_model() -> str:
    """Invokes OS dialog to select the .slx file."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True) 
    file_path = filedialog.askopenfilename(
        title="Select Simulink Target Model",
        filetypes=[("Simulink Models", "*.slx")]
    )
    root.destroy()
    return file_path

def execute_pipeline():
    print("\n=======================================================")
    print("      SIMULINK DOC AGENT - END-TO-END PIPELINE")
    print("=======================================================\n")
    
    # --- PHASE 1: EXTRACTION ---
    print(">>> PHASE 1: AST Extraction via MATLAB Engine")
    target_filepath = select_target_model()
    if not target_filepath:
        print("[WARN] Pipeline aborted: No target model selected.")
        sys.exit(0)
        
    model_dir = os.path.dirname(target_filepath)
    model_name = os.path.splitext(os.path.basename(target_filepath))[0]
    
    extractor = SimulinkExtractionEngine(model_name, model_dir)
    ast_payload = extractor.extract_model()
    
    # Ensure output directories exist
    out_dir = PROJECT_ROOT / "data" / "outputs"
    os.makedirs(out_dir, exist_ok=True)
    json_path = out_dir / f"{model_name}_ast.json"
    
    # Serialize the Pydantic AST
    with open(json_path, "w") as f:
        json.dump(ast_payload, f, indent=4, default=lambda o: o.model_dump() if hasattr(o, 'model_dump') else o.__dict__)
    
    print(f"[SUCCESS] AST serialized to: {json_path}\n")

    # --- PHASE 2: GENERATION ---
    print(">>> PHASE 2: RAG Document Generation")
    template_dir = PROJECT_ROOT / "src" / "generator" / "templates"
    generator = MarkdownGenerator(template_dir=str(template_dir))
    
    md_path = generator.generate(str(json_path), output_dir=str(out_dir))
    print(f"[SUCCESS] Markdown documentation rendered to: {md_path}\n")

    # --- PHASE 3: ORCHESTRATION ---
    print(">>> PHASE 3: Booting Agent API Service")
    # Dynamically inject the newly generated Markdown path into the environment
    os.environ["TARGET_MD_PATH"] = str(md_path)
    
    # Boot the Uvicorn ASGI server
    # Note: reload=False is required when running programmatically
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    execute_pipeline()