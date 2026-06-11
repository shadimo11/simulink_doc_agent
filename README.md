# Simulink Doc Agent ⚙️🤖

An AI-driven systems engineering orchestration pipeline that bridges deterministic physical modeling (MATLAB/Simulink) with probabilistic reasoning (Large Language Models).

This tool acts as a "Systems Engineering Copilot," allowing engineers to semantically query complex Simulink architectures, Stateflow finite state machines (FSMs), and hardware deployment configurations through an interactive conversational interface.

---

## ✨ Key Features & Capabilities

### 1. Deep Semantic Extraction (MATLAB Engine)
* **Topological Graph Mapping:** Extracts not just disconnected blocks, but the actual Directed Acyclic Graph (DAG) by evaluating `PortConnectivity` edges to map signal flows across the entire system.
* **Hardware Support Package Awareness:** Dynamically queries custom `MaskNames` and `MaskValues` to extract specific configurations for embedded hardware blocks (e.g., Arduino Pin mappings, ROS2 nodes) rather than falling back to generic `MATLABSystem` types.
* **Global Configuration Context:** Captures the deployment environment, including Solver settings, Hardware Board targets, and MATLAB Workspace lifecycle callbacks (`InitFcn`, `StopFcn`).

### 2. Stateflow FSM Parsing
* Uses MATLAB's `sfroot` API to penetrate Stateflow charts.
* Extracts internal variables, hierarchical states (with Entry/During/Exit actions), and strict transition logic (Conditions, Triggers, and Transition Actions).

### 3. Deterministic RAG Presentation
* Converts the highly nested JSON Abstract Syntax Tree (AST) into clean, LLM-optimized Markdown using a deterministic **Jinja2** templating engine.
* Employs structural Markdown chunking to ensure data tables and state machine logic are never fractured during vector embedding.

### 4. High-Fidelity Intelligence Layer
* **Vector Store:** In-memory 3072-dimensional ChromaDB powered by the 2026-generation `gemini-embedding-001` model.
* **Reasoning Engine:** LangChain orchestration utilizing `gemini-2.5-flash`, governed by a strict prompt enforcing rigorous systems engineering terminology and preventing physical parameter hallucination.

### 5. Asynchronous Microservice Architecture
* **Backend:** Non-blocking FastAPI/Uvicorn server utilizing the `lifespan` pattern to hold the LLM and ChromaDB in memory, delegating LangChain I/O to background threadpools.
* **Frontend:** A sleek, interactive Streamlit chat interface for real-time querying.

---

## 📌 Architecture Overview

1. **Extraction Layer (`src/core/`):** Headless MATLAB Engine parsing Simulink/Stateflow topologies into strict Pydantic V2 schemas.
2. **Generation Layer (`src/generator/`):** Jinja2 rendering engine for deterministic Markdown formatting.
3. **Intelligence Layer (`src/agent/`):** LangChain RAG architecture integrating ChromaDB and Google GenAI APIs.
4. **Service Layer (`src/api/` & `app.py`):** Asynchronous FastAPI backend coupled with a Streamlit chat frontend.

## 🛠️ Tech Stack
* **Language:** Python 3.11+, MATLAB R2024b
* **AI/ML:** LangChain, Google GenAI API, ChromaDB
* **API/Web:** FastAPI, Uvicorn, Streamlit
* **Validation:** Pydantic V2

---

## 🚀 Quickstart

**1. Environment Setup**
Ensure MATLAB R2024b is installed and properly licensed. Clone the repository and install the dependencies:
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