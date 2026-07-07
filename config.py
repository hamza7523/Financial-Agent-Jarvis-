import os 
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # now read from environment
MODEL_NAME = "gemini-2.5-flash"

