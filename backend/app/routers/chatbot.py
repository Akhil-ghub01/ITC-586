from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter

from app.models.chatbot import ChatRequest, ChatResponse, ChatMessage
from app.services.llm_client import generate_text
from app.services.rag_service import retrieve_relevant_chunks
from app.utils.logger import log_chatbot_call
from app.utils.pii import mask_pii
from app.utils.safety import classify_safety

router = APIRouter(
    prefix="/chatbot",
    tags=["chatbot"],
)

SYSTEM_INSTRUCTIONS = """
You are a helpful, polite customer service assistant for an e-commerce store.
You answer questions about orders, shipping, returns, refunds, and accounts.
You must rely on the knowledge base snippets provided to you. If the answer
is not clearly supported by them, say you are not sure and suggest contacting
a human agent instead of guessing.
Keep answers short, clear, and friendly.
"""

BASELINE_SYSTEM_INSTRUCTIONS = """
You are a helpful, polite customer service assistant for an e-commerce store.
You answer questions about orders, shipping, returns, refunds, and accounts.
If you are not sure about the answer, say you are not sure and suggest contacting a human agent.
Keep answers short, clear, and friendly.
"""
def build_baseline_prompt(request: ChatRequest) -> str:
    lines: List[str] = [BASELINE_SYSTEM_INSTRUCTIONS.strip(), ""]

    lines.append("Conversation so far:")
    if request.history:
        for msg in request.history:
            prefix = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{prefix}: {msg.content}")
    else:
        lines.append("(no previous messages)")

    lines.append("")
    lines.append(f"User: {request.query}")
    lines.append("Assistant:")
    return "\n".join(lines)



def build_prompt(request: ChatRequest, contexts: List[dict[str, Any]]) -> str:
    """
    Turn history + new query + RAG context into one prompt for Gemini.
    Assumes the query/history are already PII-masked if needed.
    """
    lines: List[str] = [SYSTEM_INSTRUCTIONS.strip(), ""]

    # 1) Conversation history
    lines.append("Conversation so far:")
    if request.history:
        for msg in request.history:
            prefix = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{prefix}: {msg.content}")
    else:
        lines.append("(no previous messages)")

    # 2) RAG knowledge base snippets
    if contexts:
        lines.append("")
        lines.append(
            "Knowledge base snippets (treat these as ground truth if relevant):"
        )
        for i, ctx in enumerate(contexts, start=1):
            meta = ctx.get("metadata", {}) or {}
            src = meta.get("source", "kb")
            lines.append(f"[{i}] Source: {src}")
            lines.append(ctx["text"])
            lines.append("")
    else:
        lines.append("")
        lines.append(
            "No specific knowledge base snippets were found. "
            "Answer only if it is generic customer-service knowledge; "
            "otherwise, say you are not sure and suggest a human agent."
        )

    # 3) Final user turn
    lines.append("")
    lines.append(f"User: {request.query}")
    lines.append("Assistant:")

    return "\n".join(lines)


@router.post("/query", response_model=ChatResponse)
def chatbot_query(request: ChatRequest) -> ChatResponse:
    """
    Main chatbot endpoint with:
    - Safety classification (unsafe / out_of_scope / normal)
    - PII masking (emails, phones, card-like numbers)
    - RAG-based prompting
    - Structured logging
    """
    # --- Safety classification on the raw query ---
    raw_query = request.query or ""
    safety_flag = classify_safety(raw_query)

    # --- PII masking for query and history ---
    masked_query, had_pii_query = mask_pii(raw_query)

    masked_history: List[ChatMessage] = []
    had_pii_history = False
    for msg in (request.history or []):
        masked_content, had_pii_msg = mask_pii(msg.content)
        if had_pii_msg:
            had_pii_history = True
        masked_history.append(
            ChatMessage(role=msg.role, content=masked_content)
        )

    pii_masked = had_pii_query or had_pii_history

    # Build a masked version of the request for the model
    masked_request = ChatRequest(query=masked_query, history=masked_history)

    # --- Handle safety / scope before calling LLM ---
    if safety_flag == "unsafe":
        safe_reply = (
            "I'm not able to help with this kind of request. "
            "If you or someone else might be in danger or at risk of harm, "
            "please contact local emergency services or a trusted professional right away."
        )

        log_chatbot_call(
            query=masked_query,
            history=[m.model_dump() for m in masked_history],
            reply=safe_reply,
            extra={
                "safety_flag": safety_flag,
                "pii_masked": pii_masked,
                "handled_by": "safety_guardrail",
            },
        )
        return ChatResponse(reply=safe_reply)

    if safety_flag == "out_of_scope":
        safe_reply = (
            "I'm designed to help with our store's orders, shipping, returns, refunds, "
            "and account issues. For this topic, it's better to consult a qualified "
            "professional or the appropriate support channel."
        )

        log_chatbot_call(
            query=masked_query,
            history=[m.model_dump() for m in masked_history],
            reply=safe_reply,
            extra={
                "safety_flag": safety_flag,
                "pii_masked": pii_masked,
                "handled_by": "scope_guardrail",
            },
        )
        return ChatResponse(reply=safe_reply)

    # --- Normal path: RAG + Gemini ---
    contexts = retrieve_relevant_chunks(masked_query, n_results=3)
    prompt = build_prompt(masked_request, contexts)
    reply = generate_text(prompt)

    log_chatbot_call(
        query=masked_query,
        history=[m.model_dump() for m in masked_history],
        reply=reply,
        extra={
            "safety_flag": safety_flag,
            "pii_masked": pii_masked,
            "contexts": contexts,
            "handled_by": "rag_chatbot",
        },
    )

    return ChatResponse(reply=reply)
@router.post("/query-baseline", response_model=ChatResponse)
def chatbot_query_baseline(request: ChatRequest) -> ChatResponse:
    """
    Baseline chatbot:
    - Safety + PII like main chatbot
    - BUT no RAG: only system prompt + conversation
    Useful for experiments comparing quality against the RAG version.
    """
    raw_query = request.query or ""
    safety_flag = classify_safety(raw_query)

    # PII masking
    masked_query, had_pii_query = mask_pii(raw_query)
    masked_history: List[ChatMessage] = []
    had_pii_history = False
    for msg in (request.history or []):
        masked_content, had_pii_msg = mask_pii(msg.content)
        if had_pii_msg:
            had_pii_history = True
        masked_history.append(
            ChatMessage(role=msg.role, content=masked_content)
        )

    pii_masked = had_pii_query or had_pii_history
    masked_request = ChatRequest(query=masked_query, history=masked_history)

    # Safety guardrails same as main chatbot
    if safety_flag == "unsafe":
        safe_reply = (
            "I'm not able to help with this kind of request. "
            "If you or someone else might be in danger or at risk of harm, "
            "please contact local emergency services or a trusted professional right away."
        )
        log_chatbot_call(
            query=masked_query,
            history=[m.model_dump() for m in masked_history],
            reply=safe_reply,
            extra={
                "safety_flag": safety_flag,
                "pii_masked": pii_masked,
                "handled_by": "baseline_safety_guardrail",
            },
        )
        return ChatResponse(reply=safe_reply)

    if safety_flag == "out_of_scope":
        safe_reply = (
            "I'm designed to help with our store's orders, shipping, returns, refunds, "
            "and account issues. For this topic, it's better to consult a qualified "
            "professional or the appropriate support channel."
        )
        log_chatbot_call(
            query=masked_query,
            history=[m.model_dump() for m in masked_history],
            reply=safe_reply,
            extra={
                "safety_flag": safety_flag,
                "pii_masked": pii_masked,
                "handled_by": "baseline_scope_guardrail",
            },
        )
        return ChatResponse(reply=safe_reply)

    # Normal baseline: no RAG, just instructions + conversation
    prompt = build_baseline_prompt(masked_request)
    reply = generate_text(prompt)

    log_chatbot_call(
        query=masked_query,
        history=[m.model_dump() for m in masked_history],
        reply=reply,
        extra={
            "safety_flag": safety_flag,
            "pii_masked": pii_masked,
            "contexts": [],
            "handled_by": "baseline_chatbot",
        },
    )

    return ChatResponse(reply=reply)
