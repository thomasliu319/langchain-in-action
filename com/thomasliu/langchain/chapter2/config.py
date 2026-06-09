"""模型配置"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

MODEL_PATH = os.getenv("MODEL_PATH", "/home/thomas/Downloads/models/Phi-3-mini-4k-instruct")
DEVICE = os.getenv("DEVICE", "cuda")
DTYPE = os.getenv("DTYPE", "auto")
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "200"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
DO_SAMPLE = os.getenv("DO_SAMPLE", "true").lower() == "true"
