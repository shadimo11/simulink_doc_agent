import os
import sys
import json
import tkinter as tk
from tkinter import filedialog
from jinja2 import Environment, FileSystemLoader

class MarkdownGenerator:
    def __init__(self, template_dir: str = "src/generator/templates"):
        """Initializes the Jinja2 environment."""
        self.env = Environment(
            loader=FileSystemLoader(os.path.abspath(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.template = self.env.get_template("model_report.md.j2")

    def generate(self, ast_json_path: str, output_dir: str = "data/outputs") -> str:
        """Renders the Markdown file from the AST JSON."""
        if not os.path.exists(ast_json_path):
            raise FileNotFoundError(f"AST payload not found at {ast_json_path}")
            
        with open(ast_json_path, 'r') as f:
            ast_data = json.load(f)

        rendered_md = self.template.render(**ast_data)
        
        os.makedirs(output_dir, exist_ok=True)
        # Safely extract the original model name from the JSON payload
        model_name = ast_data.get('target_model', 'unknown_model')
        output_file = os.path.join(output_dir, f"{model_name}_documentation.md")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(rendered_md)
            
        return output_file

def select_json_file() -> str:
    """Invokes a native OS dialog to select the AST JSON payload."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_path = filedialog.askopenfilename(
        title="Select AST JSON Payload",
        filetypes=[("JSON Files", "*.json")]
    )
    root.destroy()
    return file_path

if __name__ == "__main__":
    print("=== Initiating Markdown Render Engine ===")
    
    target_json = select_json_file()
    if not target_json:
        print("[WARN] Execution aborted: No JSON file selected.")
        sys.exit(0)
        
    try:
        generator = MarkdownGenerator()
        out_path = generator.generate(target_json)
        print(f"[SUCCESS] Documentation rendered at: {out_path}")
    except Exception as e:
        print(f"[FATAL] Render engine failed: {e}")