from typing import List, Dict


def build_prompt(user_message: str, history: List[Dict] = []) -> str:
    system_prompt = (
        "You are EdHub360 AI Tutor, a student-friendly assistant "
        "that helps students learn effectively."
    )

    prompt_parts = [system_prompt]

    for turn in history:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        prompt_parts.append(f"{role.capitalize()}: {content}")

    prompt_parts.append(f"User: {user_message}")

    return "\n".join(prompt_parts)
