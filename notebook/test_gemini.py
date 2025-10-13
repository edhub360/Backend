import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key exists: {bool(api_key)}")
print(f"API Key starts with: {api_key[:10] if api_key else 'None'}...")

genai.configure(api_key=api_key)

# Test text
test_text = "Machine learning is artificial intelligence"

try:
    # Try different parameter names
    print("Testing with 'text' parameter...")
    result = genai.embed_content(
        model="models/text-embedding-004",
        text=test_text,
        task_type="semantic_similarity"
    )
    print(f"SUCCESS with 'text'! Embedding dimension: {len(result['embedding'])}")
except Exception as e:
    print(f"FAILED with 'text': {e}")
    
    try:
        print("Testing with 'content' parameter...")
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=test_text,
            task_type="semantic_similarity"
        )
        print(f"SUCCESS with 'content'! Embedding dimension: {len(result['embedding'])}")
    except Exception as e2:
        print(f"FAILED with 'content': {e2}")
        
        try:
            print("Testing with different model...")
            result = genai.embed_content(
                model="models/embedding-001",
                text=test_text
            )
            print(f"SUCCESS with different model! Embedding dimension: {len(result['embedding'])}")
        except Exception as e3:
            print(f"All methods failed: {e3}")
