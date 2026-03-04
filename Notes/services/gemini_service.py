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
        try:
            # Build context with chunk-boundary-aware truncation
            context_text = self._build_context_from_chunks(context_chunks, max_chars=30000)

            # Build chat history context
            history_context = self._build_history_context(chat_history or [])

            # Create comprehensive prompt
            prompt = self._create_rag_prompt(user_query, context_text, history_context)

            logger.info(f"Sending prompt to Gemini (length: {len(prompt)} chars)")

            # 8192 is a safe, generous ceiling for notebook Q&A responses
            safe_max_output_tokens = 8192

            generation_config = genai.types.GenerationConfig(
                max_output_tokens=min(safe_max_output_tokens, max_tokens or safe_max_output_tokens),
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

            # Warn early if truncation occurred — helps catch regressions
            if finish_reason and finish_reason.name == "MAX_TOKENS":
                logger.warning(
                    f"Response truncated at MAX_TOKENS ({safe_max_output_tokens}). "
                    "Consider increasing safe_max_output_tokens or reducing context size."
                )

            # Safely extract text from parts
            parts = getattr(getattr(candidate, "content", None), "parts", []) or []
            text = "".join(
                getattr(p, "text", "") for p in parts if hasattr(p, "text")
            ).strip()

            if not text:
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

    
    def _build_context_from_chunks(
        self,
        chunks: List[Dict[str, Any]],
        max_chars: int = 30000
    ) -> str:
        """Build context string from relevant chunks with chunk-boundary-aware truncation."""
        if not chunks:
            return "No relevant context available."

        context_parts = []
        total_chars = 0

        for i, chunk in enumerate(chunks, 1):
            source_name = chunk.get("source_name", "Unknown source")
            content = chunk.get("chunk", "")
            score = chunk.get("score", 0.0)

            part = f"[Source {i}: {source_name} (relevance: {score:.2f})]\n{content}\n"

            if total_chars + len(part) > max_chars:
                logger.info(
                    f"Context truncated cleanly at chunk {i-1} "
                    f"({total_chars}/{max_chars} chars used)"
                )
                break  # stop at a clean chunk boundary, never mid-sentence

            context_parts.append(part)
            total_chars += len(part)

        return "\n".join(context_parts)


    def _build_history_context(self, history: List[Dict[str, str]]) -> str:
        """Build chat history context string, capped at recent 6 messages."""
        if not history:
            return ""

        # Only include recent history to keep prompt size manageable
        recent_history = history[-6:]

        history_parts = []
        for msg in recent_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "").strip()

            if not content:
                continue  # skip empty messages that waste tokens

            if role == "user":
                history_parts.append(f"User: {content}")
            elif role == "assistant":
                history_parts.append(f"Assistant: {content}")
            # silently skip unknown roles rather than polluting the prompt

        return "\n".join(history_parts)

    
    def _create_rag_prompt(self, user_query: str, context: str, history: str) -> str:
        """Create a RAG prompt for Gemini with minimal token waste."""

        base_prompt = """You are an AI assistant helping users understand their uploaded documents and notes.

    INSTRUCTIONS:
    1. Answer based primarily on the provided context from the user's documents.
    2. If context is insufficient, acknowledge it and answer what you can.
    3. Use chat history to maintain conversation continuity when relevant.
    4. Be concise but thorough. Cite source numbers (e.g. [Source 1]) when possible.
    """

        has_context = context and context.strip() != "No relevant context available."

        if has_context:
            base_prompt += f"\nRELEVANT CONTEXT:\n{context}\n"
        else:
            base_prompt += "\nNOTE: No specific context was found in your documents for this query.\n"

        if history:
            base_prompt += f"\nCONVERSATION HISTORY:\n{history}\n"

        base_prompt += f"\nUSER QUESTION: {user_query}\n\nRESPONSE:"

        return base_prompt


    async def generate_simple_response(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Generate a simple response without RAG context."""
        try:
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens or 4096,  # was 512 — far too low for any meaningful answer
                temperature=0.7,
                top_p=0.8,
                top_k=40
            )

            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=generation_config
            )

            if not response or not getattr(response, "candidates", None):
                raise ValueError("Empty response from Gemini API (no candidates)")

            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)

            if finish_reason and finish_reason.name == "MAX_TOKENS":
                logger.warning(
                    f"generate_simple_response truncated at MAX_TOKENS "
                    f"({max_tokens or 4096}). Consider passing a higher max_tokens."
                )

            text = response.text.strip() if response.text else ""

            if not text:
                raise ValueError("Empty response from Gemini API")

            logger.info(f"Simple response generated ({len(text)} chars)")
            return text

        except Exception as e:
            logger.error(f"Error generating simple response: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")
