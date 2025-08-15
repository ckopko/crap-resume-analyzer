from sentence_transformers import SentenceTransformer

print("Downloading and caching the 'all-MiniLM-L6-v2' model...")

# This line will download the model and save it to a cache folder.
model = SentenceTransformer('all-MiniLM-L6-v2')

print("Model downloaded successfully!")