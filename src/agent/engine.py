import os
import sys
import traceback
import certifi
from pathlib import Path
from dotenv import load_dotenv

# LangChain Core and Core Runnables
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma

from .ingestion import SimulinkDocumentIngestor
from .prompts import QA_PROMPT
from .indexer import VectorIndexManager

# Calculate project root dynamically
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    print(f"[INFO] Environmental contract found. Injecting: {ENV_PATH}")
    load_dotenv(dotenv_path=ENV_PATH)
else:
    print(f"[WARN] Environmental contract missing at calculated path: {ENV_PATH}")

# --- STRICT SSL CERTIFICATE BOUNDARY ---
# Force all underlying HTTP and SSL requests to use the deterministic Mozilla CA bundle
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
print(f"[INFO] TLS/SSL Trust Chain secured via certifi at: {certifi.where()}")

# Strict boundary validation for API Key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("[FATAL] GOOGLE_API_KEY environment variable missing or unreadable within .env structure.")
    sys.exit(1)


class SimulinkAgentEngine:
    def __init__(self, markdown_path: str):
        # 1. Strictly pull and validate environment variables
        embed_model = os.getenv("EMBEDDING_MODEL_ID")
        reasoning_model = os.getenv("REASONING_MODEL_ID")
        
        if not embed_model or not reasoning_model:
            raise RuntimeError("[FATAL] Missing model identifiers in .env file.")

        # 2. Initialize Embeddings
        print(f"[INFO] Initializing Gemini Embedding Model ({embed_model})...")
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=embed_model,
            google_api_key=api_key
        )
        
        # 3. Delegate Database Operations to the Indexer
        self.indexer = VectorIndexManager(self.embeddings)
        self.retriever = self.indexer.build_in_memory_index(markdown_path)
        
        # 4. Initialize Reasoning Engine
        print(f"[INFO] Spawning reasoning model ({reasoning_model})...")
        self.llm = ChatGoogleGenerativeAI(
            model=reasoning_model, 
            temperature=0.1,
            google_api_key=api_key
        )
        
        # 5. Build Execution Chain
        self.chain = (
            {"context": self.retriever | self._format_docs, "input": RunnablePassthrough()}
            | QA_PROMPT
            | self.llm
            | StrOutputParser()
        )
        print("[SUCCESS] LangChain Orchestration Layer Secured.")

    def _format_docs(self, docs) -> str:
        """Converts retrieved documents into a clean string block for the context prompt."""
        return "\n\n".join(doc.page_content for doc in docs)

    def query(self, user_question: str) -> str:
        """Invokes the execution chain to resolve a user query."""
        return self.chain.invoke(user_question)


if __name__ == "__main__":
    print("=== Launching Simulink Intelligence Agent Session ===")
    
    target_md = PROJECT_ROOT / "data" / "outputs" / "untitled1_documentation.md"
    
    if not target_md.exists():
        print(f"[FATAL] Target documentation not found at computed path:\n{target_md}")
        print("Ensure Phase 3 (generator) has successfully built this document.")
        sys.exit(1)
        
    try:
        agent = SimulinkAgentEngine(str(target_md))
        print("\n--- Interactive Terminal Active ---")
        
        test_query = "What happens when the 'start' variable equals 1 in the Finite State Machine?"
        print(f"\nUser Query: {test_query}")
        
        response = agent.query(test_query)
        print(f"\nAgent Response:\n{response}\n")
        
    except Exception:
        print("\n[FATAL] Agent pipeline fractured. Stack trace mapped below:")
        traceback.print_exc()
        sys.exit(1)