from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from .ingestion import SimulinkDocumentIngestor

class VectorIndexManager:
    """
    Manages the lifecycle, ingestion, and retrieval of the vector database.
    Strictly isolated from the LLM reasoning orchestration.
    """
    def __init__(self, embedding_model: Embeddings):
        self.embeddings = embedding_model
        self.vector_store = None
        self.retriever = None

    def build_in_memory_index(self, markdown_path: str, k_results: int = 2):
        """Ingests a document, computes embeddings, and spins up a temporary DB."""
        print("[INDEXER] Triggering ingestion pipeline...")
        ingestor = SimulinkDocumentIngestor()
        chunks = ingestor.load_and_split(markdown_path)
        
        print("[INDEXER] Computing tensor math and loading ChromaDB into RAM...")
        self.vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings
        )
        
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": k_results})
        print("[INDEXER] Vector index secured and retriever initialized.")
        
        return self.retriever