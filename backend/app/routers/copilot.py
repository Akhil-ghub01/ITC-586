from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter

from app.models.copilot import (
    SuggestReplyRequest,
    SuggestReplyResponse,
    SummarizeCaseRequest,
    SummarizeCaseResponse,
    ChatMessage,
)
from app.services.llm_client import generate_text
from app.services.rag_service import retrieve_relevant_chunks
from app.utils.logger import log_copilot_call
from app.utils.pii import mask_pii
from app.utils.safety import classify_safety

router = APIRouter(
    prefix="/copilot",
    tags=["copilot"],
)

SUGGEST_SYSTEM_PROMPT = """
You are an AI assistant helping CUSTOMER SUPPORT AGENTS.
Your job is to draft clear, polite, and accurate replies that the agent can edit before sending.

Context:
- The business is an e-commerce store (orders, shipping, returns, refunds, accounts).
- You MUST follow the knowledge base snippets if they are provided.
- If the knowledge base doesn't clearly answer something, say you are not fully sure and suggest
  the agent escalate or check with a supervisor.
- Use a friendly, concise tone.
- Do NOT invent order numbers, tracking numbers, or policy details that are not in the snippets.
"""

SUMMARY_SYSTEM_PROMPT = """
You are an AI assistant helping CUSTOMER SUPPORT AGENTS understand a case quickly.

Your task:
- Read the conversation between the customer and the agent.
- Produce a short summary (3–6 sentences).
- Then list 3–6 key points as bullet points (issues, promises, next steps).
- Do not hallucinate extra facts; only use what is in the conversation.
"""


def _format_conversation(conversation: List[ChatMessage]) -> str:
    lines: List[str] = []
    for msg in conversation:
        prefix = "Customer" if msg.role == "user" else "Agent"
        lines.append(f"{prefix}: {msg.content}")
    return "\n".join(lines) if lines else "(no previous messages)"


def build_suggest_prompt(
    customer_message: str,
    history: List[ChatMessage],
    contexts: List[dict[str, Any]],
    topic_hint: str | None,
) -> str:
    lines: List[str] = [SUGGEST_SYSTEM_PROMPT.strip(), ""]

    # 1) Conversation so far
    lines.append("Conversation so far:")
    lines.append(_format_conversation(history))
    lines.append("")

    # 2) New customer message
    lines.append("Latest customer message:")
    lines.append(f"Customer: {customer_message}")
    lines.append("")

    # 3) Knowledge base snippets (RAG)
    if contexts:
        lines.append("Relevant knowledge base snippets (treat these as ground truth):")
        for i, ctx in enumerate(contexts, start=1):
            meta = ctx.get("metadata", {}) or {}
            src = meta.get("source", "kb")
            lines.append(f"[{i}] Source: {src}")
            lines.append(ctx["text"])
            lines.append("")
    else:
        lines.append(
            "No specific KB snippet was found. Answer only using generic customer-service best practices, "
            "and recommend checking or escalating if needed."
        )
        lines.append("")

    # 4) Instruction to the model
    if topic_hint:
        lines.append(f"Topic hint: {topic_hint}")

    lines.append(
        "Now, draft ONE suggested reply the agent can send to the customer. "
        "Do not mention that you used a knowledge base in your answer."
    )
    lines.append("Suggested reply:")

    return "\n".join(lines)


def build_summary_prompt(conversation: List[ChatMessage]) -> str:
    lines: List[str] = [SUMMARY_SYSTEM_PROMPT.strip(), ""]
    lines.append("Conversation:")
    lines.append(_format_conversation(conversation))
    lines.append("")
    lines.append("Now provide the summary, then key bullet points.")
    return "\n".join(lines)


@router.post("/suggest-reply", response_model=SuggestReplyResponse)
def suggest_reply(req: SuggestReplyRequest) -> SuggestReplyResponse:
    """
    Agent copilot endpoint:
    - PII masking for customer message + history
    - Safety classification (so we can guide the agent for crisis / out-of-scope cases)
    - RAG-augmented prompt to draft a suggested reply
    """
    raw_msg = req.customer_message or ""
    safety_flag = classify_safety(raw_msg)

    # PII masking for customer message
    masked_customer_message, had_pii_msg = mask_pii(raw_msg)

    # PII masking for history
    masked_history: List[ChatMessage] = []
    had_pii_history = False
    for msg in (req.conversation_history or []):
        masked_content, had_pii = mask_pii(msg.content)
        if had_pii:
            had_pii_history = True
        masked_history.append(
            ChatMessage(role=msg.role, content=masked_content)
        )

    pii_masked = had_pii_msg or had_pii_history

    # Safety: in copilot we return guidance to the agent instead of customer-facing text
    if safety_flag == "unsafe":
        safe_reply = (
            "The customer's message appears to mention self-harm, violence, or another safety-critical issue. "
            "Follow your organization's crisis and escalation procedures immediately, and avoid giving advice "
            "beyond approved guidelines."
        )

        log_copilot_call(
            mode="suggest-reply",
            payload=req.model_dump(),
            output={"suggested_reply": safe_reply},
            extra={
                "safety_flag": safety_flag,
                "pii_masked": pii_masked,
                "handled_by": "safety_guardrail",
            },
        )
        return SuggestReplyResponse(suggested_reply=safe_reply)

    if safety_flag == "out_of_scope":
        safe_reply = (
            "The customer's request seems outside the store's scope (for example, medical, legal, tax, or "
            "investment advice). You should gently explain that this support channel can only help with orders, "
            "shipping, returns, refunds, and account issues, and redirect the customer to an appropriate professional "
            "or official resource."
        )

        log_copilot_call(
            mode="suggest-reply",
            payload=req.model_dump(),
            output={"suggested_reply": safe_reply},
            extra={
                "safety_flag": safety_flag,
                "pii_masked": pii_masked,
                "handled_by": "scope_guardrail",
            },
        )
        return SuggestReplyResponse(suggested_reply=safe_reply)

    # Normal path: RAG + Gemini
    rag_query = masked_customer_message
    if req.topic_hint:
        rag_query = f"{req.topic_hint}: {masked_customer_message}"

    contexts = retrieve_relevant_chunks(rag_query, n_results=3)
    prompt = build_suggest_prompt(
        customer_message=masked_customer_message,
        history=masked_history,
        contexts=contexts,
        topic_hint=req.topic_hint,
    )
    reply = generate_text(prompt)

    log_copilot_call(
        mode="suggest-reply",
        payload=req.model_dump(),
        output={"suggested_reply": reply},
        extra={
            "safety_flag": safety_flag,
            "pii_masked": pii_masked,
            "contexts": contexts,
            "handled_by": "rag_copilot",
        },
    )

    return SuggestReplyResponse(suggested_reply=reply)


@router.post("/summarize-case", response_model=SummarizeCaseResponse)
def summarize_case(req: SummarizeCaseRequest) -> SummarizeCaseResponse:
    """
    Summarize a case for an agent:
    - PII masking in the conversation before sending to the LLM
    - Safety classification on conversation content
    - Logs with safety + pii flags
    """
    # Combine conversation text for safety classification
    combined_text = " ".join(msg.content for msg in req.conversation or [])
    safety_flag = classify_safety(combined_text)

    # PII mask conversation
    masked_conversation: List[ChatMessage] = []
    had_pii = False
    for msg in req.conversation:
        masked_content, had_pii_msg = mask_pii(msg.content)
        if had_pii_msg:
            had_pii = True
        masked_conversation.append(
            ChatMessage(role=msg.role, content=masked_content)
        )

    # For unsafe content, we still can provide a short guidance summary for the agent
    if safety_flag == "unsafe":
        summary_text = (
            "This case appears to involve a safety-critical concern (for example, self-harm or violence). "
            "You should stop normal handling and follow your organization's crisis and escalation procedures. "
            "Do not provide unapproved advice."
        )

        log_copilot_call(
            mode="summarize-case",
            payload=req.model_dump(),
            output={"summary": summary_text, "key_points": []},
            extra={
                "safety_flag": safety_flag,
                "pii_masked": had_pii,
                "handled_by": "safety_guardrail",
            },
        )
        return SummarizeCaseResponse(summary=summary_text, key_points=[])

    # Normal path: summarize via LLM
    prompt = build_summary_prompt(masked_conversation)
    text = generate_text(prompt)

    # For now we return the full text as summary and keep key_points empty.
    # You can later parse bullet points into key_points if you want more structure.
    log_copilot_call(
        mode="summarize-case",
        payload=req.model_dump(),
        output={"summary": text, "key_points": []},
        extra={
            "safety_flag": safety_flag,
            "pii_masked": had_pii,
            "handled_by": "summary_copilot",
        },
    )

    return SummarizeCaseResponse(
        summary=text,
        key_points=[],
    )
