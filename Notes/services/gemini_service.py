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
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        genai.configure(api_key=self.api_key)

        # Set generation config at model level — acts as baseline for all calls
        self.default_generation_config = {
            "max_output_tokens": 8192,
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
        }

        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=self.default_generation_config,
        )

        logger.info(
            f"Gemini service initialized | "
            f"model=gemini-2.5-flash | "
            f"max_output_tokens={self.default_generation_config['max_output_tokens']}"
        )

    
    async def generate_contextual_response(
        self,
        user_query: str,
        context_chunks: List[Dict[str, Any]],
        chat_history: List[Dict[str, str]] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        try:
            context_text = self._build_context_from_chunks(context_chunks, max_chars=30000)
            history_context = self._build_history_context(chat_history or [])
            prompt = self._create_rag_prompt(user_query, context_text, history_context)

            prompt_tokens_approx = len(prompt) // 4
            logger.info(
                f"Sending prompt to Gemini | "
                f"chars={len(prompt)} | "
                f"~{prompt_tokens_approx} tokens"
            )

            # Use dict form — GenerationConfig object is silently ignored
            # on some google-generativeai SDK versions for gemini-2.5-flash
            # max_tokens from caller only raises the cap, never lowers below 8192
            safe_max_output_tokens = 8192
            generation_config = {
                "max_output_tokens": max(safe_max_output_tokens, max_tokens or safe_max_output_tokens),
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
            }

            logger.info(f"max_output_tokens={generation_config['max_output_tokens']}")

            # Generate response — model already has default_generation_config from __init__
            # per-call generation_config overrides it
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=generation_config  # dict, not GenerationConfig object
            )

            if not response or not getattr(response, "candidates", None):
                raise ValueError("Empty response from Gemini API (no candidates)")

            candidate = response.candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)
            finish_reason_name = getattr(finish_reason, "name", str(finish_reason))
            token_count = getattr(candidate, "token_count", None)

            logger.info(
                f"Gemini finish_reason={finish_reason_name} | "
                f"token_count={token_count} | "
                f"max_output_tokens={generation_config['max_output_tokens']}"
            )

            # Warn immediately on truncation — visible in Cloud Run logs
            if finish_reason_name == "MAX_TOKENS":
                logger.warning(
                    f"Response truncated at MAX_TOKENS. "
                    f"prompt_tokens≈{prompt_tokens_approx}, "
                    f"max_output_tokens={generation_config['max_output_tokens']}. "
                    f"Reduce top_n chunks or increase max_output_tokens."
                )

            # Safely extract text from parts
            parts = getattr(getattr(candidate, "content", None), "parts", []) or []
            text = "".join(
                getattr(p, "text", "") for p in parts if hasattr(p, "text")
            ).strip()

            if not text:
                if finish_reason_name == "MAX_TOKENS":
                    raise ValueError(
                        "Gemini returned no text because max_output_tokens was reached. "
                        "Try increasing max_tokens or reducing context size."
                    )
                if finish_reason_name == "SAFETY":
                    raise ValueError(
                        "Gemini blocked the response due to safety filters. "
                        "Try rephrasing the question."
                    )
                raise ValueError("Gemini returned a candidate with no text parts.")

            logger.info(
                f"Response generated successfully | "
                f"chars={len(text)} | "
                f"finish={finish_reason_name}"
            )
            return text

        except Exception as e:
            logger.error(f"Error generating Gemini response: {str(e)}")
            raise Exception(f"Failed to generate AI response: {str(e)}")

    
    def _build_context_from_chunks(
        self,
        chunks: List[Dict[str, Any]],
        max_chars: int = 30000
    ) -> str:
        """Build context string with correct per-file source labels."""
        if not chunks:
            return "No relevant context available."

        # Map source_id → display label using actual filenames
        # Built once so all chunks from the same file share the same label
        source_label_map: Dict[str, str] = {}
        source_counter = 1
        for chunk in chunks:
            sid = chunk.get("source_id", "")
            if sid and sid not in source_label_map:
                name = chunk.get("source_name", "Unknown source")
                source_label_map[sid] = f"Source {source_counter}: {name}"
                source_counter += 1

        context_parts = []
        total_chars = 0

        for chunk in chunks:
            sid = chunk.get("source_id", "")
            label = source_label_map.get(sid, "Unknown source")
            content = chunk.get("chunk", "")
            score = chunk.get("score", 0.0)

            part = f"[{label} (relevance: {score:.2f})]\n{content}\n"

            if total_chars + len(part) > max_chars:
                logger.info(
                    f"Context truncated at {total_chars}/{max_chars} chars"
                )
                break

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
