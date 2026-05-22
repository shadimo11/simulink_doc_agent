import os
from typing import List
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Initialize environment variables (API Keys)
load_dotenv()

class SimulinkDocumentIngestor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        """
        Initializes the chunking engine with Markdown-aware recursive splitting.
        """
        # We prioritize structural Markdown separators to keep tables and FSM states intact
        self.text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def load_and_split(self, markdown_path: str) -> List[Document]:
        """Loads a generated Simulink Markdown file and splits it into semantic chunks."""
        if not os.path.exists(markdown_path):
            raise FileNotFoundError(f"[FATAL] Documentation not found at: {markdown_path}")

        print(f"[INFO] Ingesting architectural document: {markdown_path}")
        loader = TextLoader(markdown_path, encoding='utf-8')
        raw_documents = loader.load()

        print("[INFO] Executing structural chunking algorithm...")
        chunks = self.text_splitter.split_documents(raw_documents)
        
        print(f"[SUCCESS] Document partitioned into {len(chunks)} semantic chunks.")
        
        # Diagnostic printing for the first chunk to verify structural integrity
        if chunks:
            print("\n--- CHUNK 0 DIAGNOSTIC ---")
            print(repr(chunks[0].page_content[:200] + "..."))
            print("--------------------------\n")
            
        return chunks

if __name__ == "__main__":
    # Smoke test the ingestion layer
    ingestor = SimulinkDocumentIngestor()
    
    # Target the Markdown file generated from your previous pipeline execution
    target_md = "data/outputs/untitled1_documentation.md"
    
    try:
        document_chunks = ingestor.load_and_split(target_md)
    except Exception as e:
        print(f"[FATAL] Ingestion fractured: {e}")