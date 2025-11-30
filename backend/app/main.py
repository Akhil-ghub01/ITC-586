from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.llm_client import generate_text
from app.routers import chatbot, copilot  # <-- add this import

app = FastAPI(
    title="AI Customer Service Backend",
    version="0.1.0",
    description="RAG chatbot + agent copilot backend for MS Design Studio project",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(chatbot.router)  # <-- add this line
app.include_router(copilot.router)  # <-- add this line

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/llm-test")
def llm_test():
    text = generate_text("Say one short sentence confirming Gemini is connected.")
    return {"response": text}
