from config import GEMINI_API_KEY,MODEL_NAME
from tools import TOOLS, get_current_datetime,remember,recall,list_memories
import httpx
user_message = "Tell me what time is right now."

import httpx


def dispatch_tool(tool_name, tool_args):
    if tool_name == "get_current_datetime":
        return get_current_datetime()
    elif tool_name == "remember":
        return remember(**tool_args)   # equivalent to remember(key="name", value="Hamza")

    elif tool_name == "recall":
        return recall(**tool_args)  
    elif tool_name=="list_memories":
        return list_memories()

    else:
        return f"Unknown tool: {tool_name}"
    
def run_agent(user_message):
    system_prompt = """You are Jarvis, a personal AI assistant.

        You have access to the following tools and MUST use them:
        - get_current_datetime: call this whenever the user asks about time or date
        - remember: call this whenever the user shares personal information, goals, or preferences
        - list_memories: ALWAYS call this first when asked what you know about the user
        - recall: call this for EACH key returned by list_memories, then summarize everything

        You have persistent memory. Always check your memory before saying you don't know something about the user.
        Never say you have no memory of past interactions — use your tools to check first."""
    result = {}
    history = [
    {"role": "user", "parts": [{"text": user_message}]},
    ]   
    URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"

    
    for i in range(10):
        request = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": history,
            "tools": [{"function_declarations": TOOLS}]
        }
        response = httpx.post(URL,json=request)
        data= response.json()
        part = data["candidates"][0]["content"]["parts"][0]
        if("functionCall" in part):
            tool_name = part["functionCall"]["name"]
            tool_args = part["functionCall"]["args"]
            result = dispatch_tool(tool_name, tool_args)
            history.append({
            "role": "model",
            "parts": [{"functionCall": {"name": tool_name, "args": tool_args}}]
            })
            history.append({
                "role": "user",
                "parts": [{"functionResponse": {
                    "name": tool_name,
                    "response": {"result": result}
                }}]
            })
        else:
            print("loop  exited before 10")
            print(part["text"])  # print what Gemini actually said

            break
        print(result)

        
if __name__ == "__main__":
   run_agent("What do you know about me?")
    