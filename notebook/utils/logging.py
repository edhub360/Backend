# Replace utils/logging.py with this:
import logging
import sys

def setup_logging(app):
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

    @app.middleware("http")
    async def log_requests(request, call_next):
        response = await call_next(request)
        # Simple logging without format conflicts
        print(f"{request.method} {request.url} - {response.status_code}")
        return response
