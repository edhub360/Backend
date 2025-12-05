import os
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import logging
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google Gemini API for text generation."""
    
    def __init__(self):
        """Initialize Gemini service with API configuration."""
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        
        logger.info("Gemini service initialized successfully")
    
    async def generate_contextual_response(
        self,
        user_query: str,
        context_chunks: List[Dict[str, Any]],
        chat_history: List[Dict[str, str]] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a response using Gemini with provided context and chat history.
        
        Args:
            user_query: The user's question
            context_chunks: List of relevant text chunks from the notebook
            chat_history: Previous chat messages for context
            max_tokens: Maximum tokens for response (optional)
        
        Returns:
            Generated response text
        """
        try:
            # Build context from chunks
            context_text = self._build_context_from_chunks(context_chunks)
            
            # Build chat history context
            history_context = self._build_history_context(chat_history or [])
            
            # Create comprehensive prompt
            prompt = self._create_rag_prompt(user_query, context_text, history_context)
            
            logger.info(f"Sending prompt to Gemini (length: {len(prompt)} chars)")
            
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens or 1024,
                temperature=0.7,
                top_p=0.8,
                top_k=40
            )
            
            # Generate response
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=generation_config
            )
            
            if not response or not getattr(response, "candidates", None):
                raise ValueError("Empty response from Gemini API (no candidates)")

            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)
            token_count = getattr(candidate, "token_count", None)
            logger.info(f"Gemini finish_reason={finish_reason}, token_count={token_count}")

            # Safely extract text from parts
            parts = getattr(getattr(candidate, "content", None), "parts", []) or []
            text = "".join(
                getattr(p, "text", "") for p in parts if hasattr(p, "text")
            ).strip()

            if not text:
                # Handle common no-text cases explicitly
                if finish_reason and finish_reason.name == "MAX_TOKENS":
                    raise ValueError(
                        "Gemini returned no text because max_output_tokens was reached. "
                        "Try increasing max_tokens or reducing context size."
                    )
                if finish_reason and finish_reason.name == "SAFETY":
                    raise ValueError(
                        "Gemini blocked the response due to safety filters. "
                        "Try rephrasing the question."
                    )
                raise ValueError("Gemini returned a candidate with no text parts.")

            logger.info(f"Successfully generated response ({len(text)} chars)")
            return text

        except Exception as e:
            logger.error(f"Error generating Gemini response: {str(e)}")
            raise Exception(f"Failed to generate AI response: {str(e)}")
    
    def _build_context_from_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """Build context string from relevant chunks."""
        if not chunks:
            return "No relevant context available."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source_name = chunk.get("source_name", "Unknown source")
            content = chunk.get("chunk", "")
            score = chunk.get("score", 0.0)
            
            context_parts.append(
                f"[Source {i}: {source_name} (relevance: {score:.2f})]\n{content}\n"
            )
        
        return "\n".join(context_parts)
    
    def _build_history_context(self, history: List[Dict[str, str]]) -> str:
        """Build chat history context string."""
        if not history:
            return ""
        
        # Only include recent history (last 6 messages to keep prompt manageable)
        recent_history = history[-6:] if len(history) > 6 else history
        
        history_parts = []
        for msg in recent_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if role == "user":
                history_parts.append(f"Previous User Question: {content}")
            elif role == "assistant":
                history_parts.append(f"Previous Assistant Response: {content}")
        
        return "\n".join(history_parts) if history_parts else ""
    
    def _create_rag_prompt(self, user_query: str, context: str, history: str) -> str:
        """Create a comprehensive RAG prompt for Gemini."""
        
        base_prompt = """You are an AI assistant helping users understand their uploaded documents and notes. You have access to relevant content from their notebook sources.

                INSTRUCTIONS:
                1. Answer the user's question based primarily on the provided context from their documents
                2. If the context contains relevant information, use it to provide a comprehensive answer
                3. If the context doesn't contain enough information, acknowledge this and provide what you can
                4. Maintain conversation continuity by considering previous chat history when relevant
                5. Be concise but thorough in your responses
                6. Always cite which sources you're referencing when possible

                """
        
        if context and context.strip() != "No relevant context available.":
            prompt = base_prompt + f"""
                RELEVANT CONTEXT FROM YOUR DOCUMENTS:
                {context}

                """
        else:
            prompt = base_prompt + "\nNOTE: No specific context was found in your documents for this query.\n"
        
        if history:
            prompt += f"""
                PREVIOUS CONVERSATION:
                {history}

                """
        
        prompt += f"""
            USER QUESTION: {user_query}

            RESPONSE:"""
        
        return prompt
    
    async def generate_simple_response(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate a simple response without RAG context."""
        try:
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens or 512,
                temperature=0.7,
                top_p=0.8,
                top_k=40
            )
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=generation_config
            )
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating simple response: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
