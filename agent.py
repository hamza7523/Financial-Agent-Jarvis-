import os
import json
import torch
import httpx
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, util
from config import GEMINI_API_KEY, MODEL_NAME
from tools import TOOLS
from memory import (
    ConversationBuffer, ConversationTurn, ToolCall,
    Episode, write_episode, recall_episodes
)
import google.generativeai as genai
load_dotenv()

# Initialize Gemini once when the module loads
gemini_model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel(MODEL_NAME)
    except Exception as exc:
        print(f"[WARN] Could not initialize Gemini model: {exc}")

def call_gemini(prompt: str) -> str:
    """Call the Gemini REST API directly without the deprecated SDK."""
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API key not configured")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ]
    }

    response = httpx.post(url, json=payload, timeout=30.0)
    response.raise_for_status()
    data = response.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Gemini response format: {data}") from exc

SYSTEM_PROMPT = """You are Jarvis, an intelligent Finance Operations Agent.
You have just executed a financial tool and received its raw output.
Your job is to interpret that data and respond like a sharp, concise CFO assistant.

Rules:
- Never say "the tool returned" or "the data shows" — just speak directly
- Lead with the most important finding
- Flag risks, anomalies, or urgent items clearly
- Be concise — no padding, no filler
- If numbers are present, interpret them, don't just repeat them
- If something looks wrong, say so plainly"""


def generate_response(
    user_query: str,
    tool_name: str,
    tool_result: dict,
    working_memory: str = None,
    episodes: list = None
) -> str:
    """Takes raw tool output and returns a natural language Gemini response."""

    # --- Build the context block ---
    context_parts = [SYSTEM_PROMPT]

    if working_memory:
        context_parts.append(f"\n{working_memory}")

    if episodes:
        ep_lines = "\n".join(
            f"- [{ep.trigger}] {ep.entity}: {ep.observation} (importance: {ep.importance})"
            for ep in episodes
        )
        context_parts.append(f"\nRELEVANT PAST EPISODES:\n{ep_lines}")

    full_system = "\n".join(context_parts)

    # --- Build the user message ---
    user_message = f"""User asked: {user_query}

Tool executed: {tool_name}
Tool output: {json.dumps(tool_result, indent=2, default=str)}

Respond as Jarvis."""

    # --- Call Gemini ---
    prompt = full_system + "\n\n" + user_message

    try:
        return call_gemini(prompt)
    except Exception as exc:
        return (
            "Summary unavailable: Gemini is not configured or the request failed. "
            f"Tool '{tool_name}' returned {json.dumps(tool_result, default=str)}. "
            f"Details: {exc}"
        )


def extract_parameters(user_query: str, tool: dict) -> dict:
    """Use Gemini to extract tool parameters from the user query."""
    required = tool.get("parameters", {}).get("required", [])
    if not required:
        return {}

    properties = tool["parameters"]["properties"]
    param_descriptions = "\n".join(
        f'- {k}: {v["description"]}' for k, v in properties.items()
    )

    prompt = f"""Extract the following parameters from the user query.
Return ONLY a valid JSON object with the parameter values. No explanation, no markdown.

Parameters needed:
{param_descriptions}

User query: {user_query}

JSON:"""

    response = gemini_model.generate_content(prompt)
    raw = response.text.strip().strip("```json").strip("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
# ==========================================
# 1. STARTUP - Eager Initialization
# ==========================================
print("Booting up Finance Operations Agent...")
# Session memory — lives for this run
conversation_buffer = ConversationBuffer(max_size=20)

# Initialize the embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Extract descriptions and embed them once at startup
descriptions = [tool["description"] for tool in TOOLS]
print(f"Embedding {len(descriptions)} tool descriptions into memory...")

# Store as a tensor of vectors
tool_embeddings = model.encode(descriptions, convert_to_tensor=True)

print("Startup complete. Agent is ready for queries.\n")
print("-" * 50)


# ==========================================
# 2. RUNTIME - Query Loop
# ==========================================
def process_query(user_query: str):
    """Handles a single user query end-to-end."""
    print(f"\nUser Query: '{user_query}'")

    # Log user turn to conversation buffer
    conversation_buffer.add_message(ConversationTurn(
        role="user",
        content=user_query
    ))

    # Step 1: Embed the user's query
    query_embedding = model.encode(user_query, convert_to_tensor=True)

    # Step 2: Calculate cosine similarity against all stored tool embeddings
    similarities = util.cos_sim(query_embedding, tool_embeddings)[0]

    # Step 3: Select the most relevant tool
    best_match_idx = torch.argmax(similarities).item()
    best_score = similarities[best_match_idx].item()
    selected_tool = TOOLS[best_match_idx]

    print(f"Matched Tool: {selected_tool['name']} (Confidence Score: {best_score:.4f})")

    # Confidence guardrail
    if best_score < 0.3:
        rejection = "I don't have a finance tool that covers that. Try asking about invoices, expenses, cashflow, or reconciliation."
        conversation_buffer.add_message(ConversationTurn(
            role="assistant",
            content=rejection
        ))
        return rejection

    # Step 4: Execute the tool
    print(f"Executing {selected_tool['name']}...")
    try:
        # Extract parameters if tool needs them
        params = extract_parameters(user_query, selected_tool)

        tool_function = selected_tool["fn"]
        result = tool_function(**params) if params else tool_function()

        # Auto-write episode — Jarvis logs what it just observed
        episode = Episode(
            actor="jarvis",
            entity=selected_tool["name"],
            trigger=selected_tool["name"],
            observation=str(result)[:300],  # cap length
            importance=6
        )
        write_episode(episode)

        # Recall relevant past episodes before responding
        past_episodes = recall_episodes(trigger=selected_tool["name"], top_n=3)

        # Step 5: Generate natural language response with memory context
        answer = generate_response(
            user_query=user_query,
            tool_name=selected_tool["name"],
            tool_result=result,
            episodes=past_episodes if past_episodes else None
        )

        # Log tool call and assistant response to conversation buffer
        conversation_buffer.add_message(ConversationTurn(
            role="tool_call",
            content=str(result),
            tool_call=ToolCall(
                tool_name=selected_tool["name"],
                tool_output=str(result)
            )
        ))
        conversation_buffer.add_message(ConversationTurn(
            role="assistant",
            content=answer
        ))

        return answer

    except Exception as e:
        error_msg = f"Failed to execute tool {selected_tool['name']}: {str(e)}"
        return {"error": error_msg}
# ==========================================
# TEST THE LOOP
# ==========================================
if __name__ == "__main__":
    res1 = process_query("Who owes us money right now? I need to chase down late payments.")
    print("\nResult:", res1)
    print("-" * 50)

    res2 = process_query("Did anyone double bill us this month? Check for weird spending.")
    print("\nResult:", res2)
    print("-" * 50)

    res3 = process_query("Show me everything on Delta Imports.")
    print("\nResult:", res3)
    print("-" * 50)

    res4 = process_query("Are we doing better than last month?")
    print("\nResult:", res4)