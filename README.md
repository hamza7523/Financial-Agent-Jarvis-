# Jarvis — Finance Operations Agent

Jarvis is a finance-focused AI assistant that helps a small business or finance team understand cash collection risk, expense anomalies, reconciliation issues, and general financial health. It combines a lightweight tool layer over Excel-backed financial data with semantic tool routing and an LLM response layer for natural-language summaries.

The project is designed as a practical foundation for an AI finance copilot that can evolve through several phases: first from simple tool execution, then into memory-rich reasoning, and eventually into a multi-agent and MCP-driven architecture.

---

## What Jarvis Does

Jarvis can help answer questions such as:

- Who is overdue and should be chased?
- Are there unusual or duplicate expenses?
- Do our payments and invoices look reconciled?
- What is our current cashflow position?
- How is the month trending overall?

It does this by:

1. Reading financial data from Excel workbooks
2. Exposing finance operations as callable tools
3. Matching the user query to the most relevant tool using semantic similarity
4. Running the tool and turning the result into a concise finance-style response
5. Logging episodes and memory so future sessions can build context

---

## Project Structure

- [agent.py](agent.py) — main runtime loop, semantic dispatch, tool execution, and LLM response generation
- [tools.py](tools.py) — finance operations tools such as aging reports, monthly summaries, anomaly detection, and cashflow analysis
- [data_layer.py](data_layer.py) — Excel data loading layer with typed dataclasses for invoices, expenses, and payments
- [memory.py](memory.py) — multi-tier memory system for conversation, working memory, episodic memory, and persistent facts
- [config.py](config.py) — central configuration for Gemini settings and behaviour thresholds
- [memory.json](memory.json) — persistent key-value memory store
- [episodic_memory.json](episodic_memory.json) — episodic memory log across runs
- [accounts.xlsx](accounts.xlsx) — source workbook for invoices, expenses, and payments

---

## Current Build Status

### Phase 1 — Data Layer and Tool Layer

Completed:

- Structured financial models for invoices, expenses, and payments
- Excel readers for each sheet
- Date normalization and workbook closing after each read
- Finance tools for:
  - aging analysis
  - monthly summary
  - reconciliation checks
  - expense anomaly detection
  - cashflow position

### Phase 2 — Agent Intelligence and Memory

Completed:

- Semantic query-to-tool matching using sentence embeddings
- Confidence-based tool selection guardrail
- Gemini-powered natural-language response generation
- Conversation buffer memory
- Working memory state tracking
- Episodic memory persistence
- Persistent memory store for facts and preferences

### Phase 3 — Planned Enhancements

Planned next steps:

- Replace file-based episodic storage with ChromaDB or another vector database
- Add semantic retrieval of past episodes such as recurring late clients
- Introduce statistical anomaly detection and stronger pattern recognition
- Add robust test coverage for all finance tools and agent flows

### Phase 4 — Action Layer

Planned later:

- Draft and send overdue invoice follow-up emails
- Generate PDF reports for aging, reconciliation, and monthly summaries
- Add observability and execution tracing for tool usage

### Phase 5 — Multi-Agent Architecture

Planned later:

- Split the assistant into specialist agents for collections, expenses, reconciliation, and reporting
- Introduce a supervisor agent to coordinate workflows
- Share working memory between agents

### Phase 6 — LangGraph Refactor

Planned later:

- Rebuild the orchestration logic as a LangGraph state machine
- Improve reliability with branching, retries, and conditional execution

### Phase 7 — MCP Servers

Planned later:

- Expose Jarvis tools through MCP-compatible endpoints
- Allow other agents and systems to call the finance tools directly

---

## Installation

1. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

If a requirements file is not present yet, install the main packages manually:

```bash
pip install python-dotenv sentence-transformers torch openpyxl httpx
```

3. Add your Gemini API key

Create a `.env` file in the project root with:

```env
GEMINI_API_KEY=your_api_key_here
```

---

## Running the Agent

From the project root:

```bash
python agent.py
```

The agent will:

- load the finance datasets
- embed tool descriptions
- wait for a query
- match the query to the right finance tool
- execute it
- generate a human-readable finance summary

---

## Example Queries

You can ask Jarvis things like:

- Who owes us money right now?
- Did anyone double bill us this month?
- Do our books reconcile?
- What is our cashflow position?
- How are we doing this month?

---

## Memory System

Jarvis includes a layered memory system:

- Conversation buffer: recent turns in the current session
- Working memory: task state and flags for the active workflow
- Episodic memory: stored experiences from previous runs
- Persistent memory: durable facts and preferences saved to JSON

This makes the agent more useful over time as it accumulates context and learns from past interactions.

---

## Configuration

The main settings live in [config.py](config.py):

- `GEMINI_API_KEY` — API key for Gemini responses
- `MODEL_NAME` — Gemini model name
- `CONFIDENCE_THRESHOLD` — minimum similarity score for tool selection
- `HIGH_EXPENSE_THRESHOLD` — threshold for flagging expensive expenses
- `STARTING_BALANCE` — baseline balance used in cashflow calculations

---

## Notes

This project is intentionally built as a practical, extensible finance assistant rather than a polished production product. It is a strong base for experimentation, rapid prototyping, and future upgrades into a full financial operations platform.

---

## Roadmap

The current roadmap is:

1. Complete the remaining Phase 2 capabilities such as client-history and month-over-month comparison tools
2. Introduce vector-based episodic memory and more advanced anomaly detection
3. Add action-oriented features such as email drafting and reporting
4. Expand into multi-agent coordination and MCP tooling

---

## Next Step

The next step is to finish the remaining Phase 2 items and make the agent more capable of answering richer finance questions with deeper context.
