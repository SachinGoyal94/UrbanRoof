import os
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_KEY")
MODEL_NAME     = "gemini-3.1-flash-lite-preview"
OUTPUT_DIR     = "outputs"
UPLOAD_DIR     = "uploads"
TEMP_IMG_DIR   = "temp_images"