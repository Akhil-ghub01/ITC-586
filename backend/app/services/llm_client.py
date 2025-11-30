import google.generativeai as gen

from app.config import settings

if not settings.gemini_api_key:
    raise RuntimeError("GEMINI_API_KEY is not set in .env")

gen.configure(api_key=settings.gemini_api_key)

# Use a currently supported model ID
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
# You could also try: "gemini-2.0-flash" or "gemini-2.5-flash"


def generate_text(prompt: str, model_name: str = DEFAULT_GEMINI_MODEL) -> str:
    model = gen.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return getattr(response, "text", "").strip()
