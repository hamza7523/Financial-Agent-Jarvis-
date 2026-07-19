import json
import chromadb
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Literal, Optional, Callable, Any
from uuid import uuid4
import httpx
from config import GEMINI_API_KEY, MODEL_NAME

# ==========================================
# Token Counting Utility
# ==========================================

CONTEXT_WINDOW = 1_000_000  # Gemini Flash max tokens

TOKEN_BUDGET = {
    "system_prompt":    int(CONTEXT_WINDOW * 0.10),  # 100,000
    "working_memory":   int(CONTEXT_WINDOW * 0.10),  # 100,000
    "episodic_context": int(CONTEXT_WINDOW * 0.20),  # 200,000
    "conversation":     int(CONTEXT_WINDOW * 0.40),  # 400,000
    "completion":       int(CONTEXT_WINDOW * 0.20),  # 200,000
}

ROLE_IMPORTANCE = {
    "system":    10,  # never evict
    "user":       7,  # high — user intent always matters
    "assistant":  6,  # medium — responses useful but regeneratable
    "tool_call":  5,  # lowest — raw output lives in episodic memory
}

def count_tokens(text: str) -> int:
    """Count tokens via Gemini REST API."""
    if not GEMINI_API_KEY or not text:
        return 0
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:countTokens?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": text}]}]
        }
        response = httpx.post(url, json=payload, timeout=10.0)
        response.raise_for_status()
        return response.json().get("totalTokens", 0)
    except Exception as e:
        print(f"[WARN] Token count failed, estimating: {e}")
        return len(text) // 4  # fallback: ~4 chars per token


# ==========================================
# Tier 1 — Conversation Buffer (Token-Based)
# ==========================================

Role = Literal["user", "assistant", "tool_call", "system"]


@dataclass
class ToolCall:
    tool_name: str
    tool_output: str


@dataclass
class ConversationTurn:
    role: Role
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_call: Optional[ToolCall] = None
    turn_id: str = field(default_factory=lambda: str(uuid4()))
    token_count: int = 0        # populated on add
    importance: int = 0         # populated on add from ROLE_IMPORTANCE


class ConversationBuffer:
    def __init__(
        self,
        budget: int = TOKEN_BUDGET["conversation"],
        on_evict: Optional[Callable[["ConversationTurn"], None]] = None,
    ):
        self.budget = budget               # max tokens allowed
        self.turns: list[ConversationTurn] = []
        self.on_evict = on_evict
        self._total_tokens = 0             # running token count

    def add_message(self, turn: ConversationTurn) -> None:
        # Count tokens and assign importance before storing
        turn.token_count = count_tokens(turn.content)
        turn.importance = ROLE_IMPORTANCE.get(turn.role, 5)

        self.turns.append(turn)
        self._total_tokens += turn.token_count

        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        """Evict lowest importance turns until under budget."""
        while self._total_tokens > self.budget and len(self.turns) > 1:
            # Sort by importance ascending — evict lowest first
            # Among equal importance, evict oldest first
            evict_idx = self._find_eviction_candidate()
            if evict_idx is None:
                break

            evicted = self.turns.pop(evict_idx)
            self._total_tokens -= evicted.token_count

            if self.on_evict:
                self.on_evict(evicted)  # hand off to episodic memory

    def _find_eviction_candidate(self) -> Optional[int]:
        """Find index of lowest importance, oldest turn. Never evict system turns."""
        candidates = [
            (i, turn) for i, turn in enumerate(self.turns)
            if turn.role != "system"
        ]
        if not candidates:
            return None

        # Sort by importance asc, then by timestamp asc (oldest first)
        candidates.sort(key=lambda x: (x[1].importance, x[1].timestamp))
        return candidates[0][0]

    def get_recent(self, n: int) -> list[ConversationTurn]:
        return self.turns[-n:]

    def get_total_tokens(self) -> int:
        return self._total_tokens

    def get_budget_remaining(self) -> int:
        return self.budget - self._total_tokens

    def graduate_to_episodic(self) -> list[ConversationTurn]:
        """Called at end-of-session — hands all remaining turns to Tier 3."""
        return list(self.turns)


# ==========================================
# Tier 2 — Working Memory (Task State)
# ==========================================

@dataclass
class WorkingMemory:
    task_name: str
    status: Literal["idle", "in_progress", "done"]
    steps_completed: list[str] = field(default_factory=list)
    steps_pending: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return asdict(self)

    def complete_step(self, step: str) -> None:
        if step in self.steps_pending:
            self.steps_completed.append(step)
            self.steps_pending.remove(step)

    def add_flag(self, flag: str) -> None:
        self.flags.append(flag)

    def to_prompt_block(self) -> str:
        stringOutput = ""
        stringOutput += f"WORKING MEMORY\nTask: {self.task_name} | Status: {self.status}\n"
        stringOutput += f"Completed: {', '.join(self.steps_completed) if self.steps_completed else 'None'}\n"
        stringOutput += f"Pending: {', '.join(self.steps_pending) if self.steps_pending else 'None'}\n"
        stringOutput += f"Flags: {', '.join(self.flags) if self.flags else 'None'}\n"
        return stringOutput


def write_working_memory_to_file(memory: WorkingMemory, filename: str) -> None:
    with open(filename, "w") as f:
        json.dump(memory.to_dict(), f, default=str, indent=4)


# ==========================================
# Tier 3 — Episodic Memory (ChromaDB)
# ==========================================

EPISODIC_STORE = "episodic_memory.json"  # kept as archive, never deleted

chroma_client = chromadb.PersistentClient(path="./chroma_store")
episode_collection = chroma_client.get_or_create_collection(
    name="episodes",
    metadata={"hnsw:space": "cosine"}
)


@dataclass
class Episode:
    episode_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    actor: str = ""
    entity: str = ""
    trigger: str = ""
    observation: str = ""
    outcome: str = ""
    importance: int = 5

    def to_dict(self) -> dict:
        return asdict(self)


def write_episode(episode: Episode) -> None:
    """Write episode to ChromaDB."""
    episode_collection.add(
        ids=[episode.episode_id],
        documents=[episode.observation],
        metadatas=[{
            "timestamp": episode.timestamp,
            "actor": episode.actor,
            "entity": episode.entity,
            "trigger": episode.trigger,
            "outcome": episode.outcome,
            "importance": episode.importance
        }]
    )


def recall_episodes(entity: str = None, trigger: str = None, top_n: int = 5, query: str = None) -> list[Episode]:
    """Semantic recall from ChromaDB."""
    try:
        where_filter = {}
        if entity and trigger:
            where_filter = {"$and": [{"entity": {"$eq": entity}}, {"trigger": {"$eq": trigger}}]}
        elif entity:
            where_filter = {"entity": {"$eq": entity}}
        elif trigger:
            where_filter = {"trigger": {"$eq": trigger}}

        search_query = query or entity or trigger or "finance"

        results = episode_collection.query(
            query_texts=[search_query],
            n_results=top_n,
            where=where_filter if where_filter else None
        )

        episodes = []
        if results["ids"] and results["ids"][0]:
            for i, episode_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i]
                doc = results["documents"][0][i]
                episodes.append(Episode(
                    episode_id=episode_id,
                    timestamp=meta["timestamp"],
                    actor=meta["actor"],
                    entity=meta["entity"],
                    trigger=meta["trigger"],
                    observation=doc,
                    outcome=meta["outcome"],
                    importance=meta["importance"]
                ))

        episodes.sort(key=lambda ep: ep.importance, reverse=True)
        return episodes

    except Exception as e:
        print(f"[ChromaDB recall error]: {e}")
        return []


# ==========================================
# Tier 4 — Persistent Key-Value Store
# ==========================================

def get_current_datetime() -> str:
    now = datetime.now()
    return f"Current datetime: {now.strftime('%Y-%m-%d %H:%M:%S')}"


def remember(key: str, value: str) -> str:
    file_path = "memory.json"
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data[key] = value
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)
    return f"Remembered: {key} = {value}"


def list_memories() -> str:
    file_path = "memory.json"
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
        if not data:
            return "No memories stored yet."
        return f"Stored memory keys: {list(data.keys())}"
    except (FileNotFoundError, json.JSONDecodeError):
        return "No memories stored yet."


def recall(key: str) -> str:
    file_path = "memory.json"
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return "You can't recall as no memory file exists yet."
    if key in data:
        return f"Remembered: {key} = {data[key]}"
    else:
        return f"Key '{key}' not found in memories."


# ==========================================
# Tool Definitions for LLM Function Calling
# ==========================================

TOOLS = [
    {
        "name": "get_current_datetime",
        "description": "Get the exact time of the day in the universal format.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "remember",
        "description": "Store factual snippets or user preferences across sessions permanently.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "The unique shorthand label to store the memory under"},
                "value": {"type": "string", "description": "The explicit information to remember"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "recall",
        "description": "Retrieve previously remembered values based on a key identifier.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "The exact label of the memory to look up"}
            },
            "required": ["key"]
        }
    }
]