import os 
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # now read from environment
MODEL_NAME = "gemini-2.5-flash"

# Agent behaviour
CONFIDENCE_THRESHOLD = 0.30       # move it out of agent.py
HIGH_EXPENSE_THRESHOLD = 10000    # for anomaly work later

# Finance defaults  
STARTING_BALANCE = 50_000.00      # replaces the hardcoded value in tools.py
