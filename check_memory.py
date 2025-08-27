import os
import psutil
from sentence_transformers import SentenceTransformer

# Get memory usage before loading the model
process = psutil.Process(os.getpid())
mem_before = process.memory_info().rss / (1024 * 1024)  # in MB
print(f"Memory before model load: {mem_before:.2f} MB")

# Load the model
print("Loading model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded.")

# Get memory usage after loading the model
mem_after = process.memory_info().rss / (1024 * 1024)  # in MB
print(f"Memory after model load: {mem_after:.2f} MB")

model_usage = mem_after - mem_before
print(f"\n📈 The SentenceTransformer model is using approximately: {model_usage:.2f} MB of RAM")

# You'll also need to install psutil: pip install psutil