import os

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "Jarvis"

from dotenv import load_dotenv
load_dotenv()  # This loads LANGCHAIN_API_KEY from .env automatically

# No need to assign LANGCHAIN_API_KEY to a Python variable
# LangChain reads it directly from the environment

from typing import Literal, TypedDict
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState  # use this as-is
from tools import TOOLS

# DELETE the @dataclass MessagesState block entirely - it's already imported above


    




@tool
def search(query: str):
    """Call to surf the web."""
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."

tools = [search, TOOLS.get_aging_report, TOOLS.get_expense_summary, TOOLS.get_invoice_summary, TOOLS.get_payment_summary, TOOLS.get_reconciliation_report, TOOLS.get_client_history, TOOLS.get_month_comparison, TOOLS.get_expense_anomalies, TOOLS.get_cashflow_position]
tool_node = ToolNode(tools)

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0).bind_tools(tools)

def should_continue(state: MessagesState):
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "__end__"

def call_model(state: MessagesState):
    messages = state['messages']
    response = model.invoke(messages)
    return {"messages": [response]}

workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_edge("__start__", "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

app = workflow.compile()

def run_agent(user_query: str):
    final_state = app.invoke(
        {"messages": [HumanMessage(content=user_query)]},
        config={"configurable": {"thread_id": 42}}
    )
    return final_state["messages"][-1].content

if __name__ == "__main__":
    print("Running agent...")
    response = run_agent("what is the weather in sf")
    print(f"\nAgent response: {response}")