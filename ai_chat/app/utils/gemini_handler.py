import os
from typing import List, Optional
import google.generativeai as genai

# Configure the API key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is required")

genai.configure(api_key=api_key)

class GeminiHandler:
    def __init__(self, model_name: str = "gemini-2.5-pro"):
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
    
    def generate_response(self, query: str, context: Optional[List[str]] = None) -> str:
        """Generate response from Gemini with optional context."""
        try:
            if context:
                # RAG mode: prepend context
                context_text = "\n\n".join([f"Document {i+1}:\n{doc}" for i, doc in enumerate(context)])
                prompt = f"""You are SmartStudy, an intelligent tutoring assistant. Use the following documents to answer the user's question. If the answer cannot be found in the provided documents, say so and provide a general response based on your knowledge.

Context Documents:
{context_text}

User Question: {query}

Please provide a comprehensive and helpful answer."""
            else:
                # General mode: direct query
                prompt = f"""You are SmartStudy, a friendly AI study assistant.
                            - If the user just greets you (e.g., "hi", "hello"), reply briefly and warmly (1–2 sentences).
                            - For study-related questions, keep answers clear, concise, and helpful.
                            - Use simple formatting (line breaks, bullet points) for readability.
                            - Keep responses under 4–5 sentences unless the user explicitly asks for detailed explanations.

                user question: {query}"""
            
            response = self.model.generate_content(prompt)
            return response.text if response.text else "I apologize, but I couldn't generate a response."
            
        except Exception as e:
            return f"Sorry, I encountered an error while processing your request: {str(e)}"
        
    async def generate_image_answer(
        self,
        image_bytes: bytes,
        *,
        subject: str | None = None,
        mode: str | None = "steps",
    ) -> str:
        """
        Use Gemini vision to read a question from a screenshot/image
        and return a clear solution.

        mode:
          - "steps": brief step‑by‑step explanation + final answer
          - "final": only the final answer in 1–2 sentences
        """
        try:
            # Build instruction based on mode
            if mode == "final":
                instruction = (
                    "You are a homework helper. Look at the image and answer the "
                    "question directly in 1–2 concise sentences, without long steps."
                )
            else:
                instruction = (
                    "You are a homework helper. Look at the image and solve the "
                    "question step by step. Then clearly state the final answer."
                )

            if subject:
                instruction += f" The subject is {subject}."

            # Gemini image‑understanding call: one image + instruction text
            response = self.model.generate_content(
                [
                    {"role": "user", "parts": [
                        {"text": instruction},
                        {"inline_data": {
                            "mime_type": "image/png",
                            "data": image_bytes,
                        }},
                    ]}
                ]
            )

            return response.text or "I could not generate an answer from the image."
        except Exception as e:
            return f"Sorry, I encountered an error while processing the image: {str(e)}"


# Global handler instance
_gemini_handler: Optional[GeminiHandler] = None

def get_gemini_handler() -> GeminiHandler:
    """Get or create the global Gemini handler instance."""
    global _gemini_handler
    if _gemini_handler is None:
        _gemini_handler = GeminiHandler()
    return _gemini_handler
