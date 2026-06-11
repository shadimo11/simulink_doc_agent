# Simulink Doc Agent ⚙️🤖

An AI-driven systems engineering orchestration pipeline that bridges deterministic physical modeling (MATLAB/Simulink) with probabilistic reasoning (Large Language Models).

## 📌 Architecture Overview

This project extracts Abstract Syntax Trees (AST) and topological connections from Simulink block diagrams and Stateflow FSMs, rendering them into structural Markdown. It then utilizes a LangChain-driven RAG pipeline to allow Systems Engineers to semantically query the architecture.

* **Extraction Layer:** Headless MATLAB Engine parsing Simulink/Stateflow topologies into Pydantic models.
* **Generation Layer:** Jinja2 rendering engine for deterministic Markdown formatting.
* **Intelligence Layer:** LangChain RAG architecture using ChromaDB (`gemini-embedding-001` at 3072D) and `gemini-2.5-flash` for reasoning.
* **Service Layer:** Asynchronous FastAPI backend coupled with a Streamlit chat frontend.

## 🛠️ Tech Stack
* **Language:** Python 3.11+, MATLAB R2024b
* **AI/ML:** LangChain, Google GenAI API, ChromaDB
* **API/Web:** FastAPI, Uvicorn, Streamlit
* **Validation:** Pydantic V2

## 🚀 Quickstart

**1. Environment Setup**
Ensure MATLAB R2024b is installed. Clone the repo and install dependencies:
```bash
conda create -n doc-agent python=3.11
conda activate doc-agent
pip install -r requirements.txt
```
**2. Configure API Keys**
Copy the environment template and add your Google API key:
```bash
cp .env.example .env
```

**3. Boot the Pipeline**
Run the root orchestrator. This will prompt you to select a `.slx` file, extract the AST, and boot the FastAPI backend on `localhost:8000`.
```bash
python main.py
```
**4. Launch the Client Interface**
```bash
streamlit run app.py
```