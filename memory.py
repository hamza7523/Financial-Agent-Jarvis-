import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Literal, Optional, Callable
from uuid import uuid4


# ==========================================
# Core Conversational Memory Structure (Tier 1)
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


class ConversationBuffer:
    def __init__(
        self,
        max_size: int,
        on_evict: Optional[Callable[[ConversationTurn], None]] = None,
    ):
        self.max_size = max_size
        self.turns: list[ConversationTurn] = []
        self.on_evict = on_evict  # Tier 3 will register a scoring callback here

    def add_message(self, turn: ConversationTurn) -> None:
        self.turns.append(turn)
        self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        while len(self.turns) > self.max_size:
            evicted = self.turns.pop(0)
            if self.on_evict:
                self.on_evict(evicted)  # hand off, don't discard silently

    def get_recent(self, n: int) -> list[ConversationTurn]:
        return self.turns[-n:]

    def graduate_to_episodic(self) -> list[ConversationTurn]:
        """Called at end-of-session — hands all remaining turns to Tier 3."""
        return list(self.turns)


# ==========================================
# Tier 2 — Working Memory (Task State)
# ==========================================

from typing import Any

@dataclass
class WorkingMemory:
    task_name: str                                    # "month_end_close", "aging_review"
    status: Literal["idle", "in_progress", "done"]   # where are we
    steps_completed: list[str] = field(default_factory=list)   # what's been checked
    steps_pending: list[str] = field(default_factory=list)     # what's left
    flags: list[str] = field(default_factory=list)             # anomalies found mid-task
    context: dict[str, Any] = field(default_factory=dict)      # arbitrary task data
    started_at: datetime = field(default_factory=datetime.now)
    def to_dict(self) -> dict:
        return asdict(self)

    def complete_step(self, step: str) -> None:
        """Move a step from pending to completed."""
        if step in self.steps_pending:
            self.steps_completed.append(step)
            self.steps_pending.remove(step)

    def add_flag(self, flag: str) -> None:
        """Record an anomaly or warning found during the task."""
        self.flags.append(flag)

    def to_prompt_block(self) -> str:
        """Serialize state into a string for injection into the system prompt."""
        # YOUR CODE HERE
        # Should produce something like:
        # WORKING MEMORY
        # Task: month_end_close | Status: in_progress
        # Completed: aging_report, reconciliation
        # Pending: expense_check, cashflow
        # Flags: Lambda Energies 67 days overdue
        stringOutput = ""
        stringOutput += f"WORKING MEMORY\nTask: {self.task_name} | Status: {self.status}\n"
        stringOutput += f"Completed: {', '.join(self.steps_completed) if self.steps_completed else 'None'}\n"
        stringOutput += f"Pending: {', '.join(self.steps_pending) if self.steps_pending else 'None'}\n"
        stringOutput += f"Flags: {', '.join(self.flags) if self.flags else  'None'}\n"
        return stringOutput
        


# ==========================================
# Tier 3 — Episodic Memory (Cross-Session)
# ==========================================

EPISODIC_STORE = "episodic_memory.json"

@dataclass
class Episode:
    episode_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    actor: str = ""         # "user", "jarvis", or a client name
    entity: str = ""        # subject — "Lambda Energies", "INV042"
    trigger: str = ""       # what caused this — "aging_report", "anomaly_detected"
    observation: str = ""   # what happened — the actual fact
    outcome: str = ""       # what was done (can be empty at write time)
    importance: int = 5     # 1-10, used for ranking on retrieva
    def to_dict(self) -> dict:
        return asdict(self)
def write_working_memory_to_file(memory: WorkingMemory, filename: str) -> None:
    """Serialize the working memory to a JSON file."""
    with open(filename, "w") as f:
        json.dump(memory.to_dict(), f, default=str, indent=4)
        
def write_episode(episode: Episode) -> None:
    try:
        with open(EPISODIC_STORE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []                          # list, not dict

    data.append(episode.to_dict())         # append, not key assignment

    with open(EPISODIC_STORE, "w") as f:
        json.dump(data, f, indent=4)


    # 2. Append episode.to_dict() to the list
    
    # 3. Write the whole list back to EPISODIC_STORE
    
def recall_episodes(entity: str = None, trigger: str = None, top_n: int = 5) -> list[Episode]:
    try:
        with open(EPISODIC_STORE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    # Filter by entity and/or trigger if provided
    if entity:
        data = [ep for ep in data if ep["entity"] == entity]
    if trigger:
        data = [ep for ep in data if ep["trigger"] == trigger]

    # Sort by importance descending
    data.sort(key=lambda ep: ep["importance"], reverse=True)

    # Convert dicts back to Episode objects and return top_n
    return [Episode(**ep) for ep in data[:top_n]]
    
# ==========================================
# Persistent Key-Value Memory Tools (Tier 4)
# ==========================================

def get_current_datetime() -> str:
    """Get current local date and time."""
    now = datetime.now()
    return f"Current datetime: {now.strftime('%Y-%m-%d %H:%M:%S')}"


def remember(key: str, value: str) -> str:
    """Store information inside a JSON file with its adjacent key."""
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
    """List all stored keys."""
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
    """Retrieve the value corresponding to a key safely."""
    file_path = "memory.json"
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return "You can't recall as no memory file exists yet."
    
    # Safe lookup to prevent KeyError crashes
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
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "remember",
        "description": "Store factual snippets or user preferences across sessions permanently.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The unique shorthand label to store the memory under (e.g., 'user_name')"
                },
                "value": {
                    "type": "string", 
                    "description": "The explicit information to remember"
                }
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
                "key": {
                    "type": "string",
                    "description": "The exact label of the memory to look up"
                }
            },
            "required": ["key"]
        }
    }
]