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

from ingestion import SimulinkDocumentIngestor
from prompts import QA_PROMPT

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

# Strict boundary validation
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("[FATAL] GOOGLE_API_KEY environment variable missing or unreadable within .env structure.")
    sys.exit(1)


class SimulinkAgentEngine:
    def __init__(self, markdown_path: str):
        """Initializes the RAG pipeline by embedding documents into a local vector store."""
        print("[INFO] Initializing Gemini Embedding Model (text-embedding-004)...")
        
        # Explicitly passing the API key overrides LangChain's local disk lookup fallback
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=os.getenv("EMBEDDING_MODEL_ID"),
            google_api_key=api_key
        )
        
        # Ingest and chunk the generated documentation
        ingestor = SimulinkDocumentIngestor()
        chunks = ingestor.load_and_split(markdown_path)
        
        print("[INFO] Computing vector math and spinning up in-memory Chroma database...")
        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings
        )
        
        # Configure retriever to gather the top relevant blocks based on cosine similarity
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 2})
        
        print("[INFO] Spawning reasoning model (gemini-1.5-flash)...")
        self.llm = ChatGoogleGenerativeAI(
            model=os.getenv("REASONING_MODEL_ID"), 
            temperature=0.1,
            google_api_key=api_key
        )
        
        # Build the functional execution chain
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