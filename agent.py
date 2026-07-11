import google.generativeai as genai
from dotenv import load_dotenv

load_env()
genai.configure()
from tools import TOOLS

# ==========================================
# 1. STARTUP - Eager Initialization
# ==========================================
print("Booting up Finance Operations Agent...")

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
    
    # Step 1: Embed the user's query
    query_embedding = model.encode(user_query, convert_to_tensor=True)
    
    # Step 2: Calculate cosine similarity against all stored tool embeddings
    similarities = util.cos_sim(query_embedding, tool_embeddings)[0]
    
    # Step 3: Select the most relevant tool
    best_match_idx = torch.argmax(similarities).item()
    best_score = similarities[best_match_idx].item()
    selected_tool = TOOLS[best_match_idx]
    
    print(f"Matched Tool: {selected_tool['name']} (Confidence Score: {best_score:.4f})")
    
    # Optional guardrail: If the score is too low, the query might be unrelated to finance
    if best_score < 0.30:
        return {"error": "Query does not match any available finance tools."}

    # Step 4: After Match - Call the tool
    print(f"Executing {selected_tool['name']}...")
    try:
        # Since our Phase 1 tools don't require dynamic parameters, we just call them directly
        tool_function = selected_tool["fn"]
        result = tool_function()
        
        # Step 5: Keep its output and return it
        return result
        
    except Exception as e:
        return {"error": f"Failed to execute tool {selected_tool['name']}: {str(e)}"}

# ==========================================
# TEST THE LOOP
# ==========================================
if __name__ == "__main__":
    # Test 1: Should trigger get_aging_report
    res1 = process_query("Who owes us money right now? I need to chase down late payments.")
    print("\nResult:", res1)
    
    print("-" * 50)
    
    # Test 2: Should trigger get_expense_anomalies
    res2 = process_query("Did anyone double bill us this month? Check for weird spending.")
    print("\nResult:", res2)