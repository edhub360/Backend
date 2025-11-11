from google.cloud import content_safety_v1beta1 as content_safety
from google.api_core.exceptions import GoogleAPIError

client = content_safety.ContentSafetyServiceClient()

def check_content_safety(text: str) -> bool:
    """Returns True if content is safe, False if harmful content detected."""
    try:
        request = content_safety.AnalyzeContentRequest(
            type_="TEXT_TYPE_UNSPECIFIED",
            text=content_safety.TextEntry(text=text),
        )
        response = client.analyze_content(request=request)

        return not response.overall_safety_attributes.overall_harmful
    except GoogleAPIError as e:
        print(f"Content Safety API error: {e}")
        # Fail safe - decide your policy (here allowing content)
        return True

def moderate_generated_content(text: str) -> tuple[bool, str]:
    """Checks generated text and returns (is_safe, safe_text).
    If unsafe, returns an alternate message to avoid harmful output."""
    is_safe = check_content_safety(text)
    if is_safe:
        return True, text
    else:
        return False, "Sorry, I am unable to provide a response to that query due to content policy."
