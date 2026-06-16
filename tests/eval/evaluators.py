"""
tests/eval/evaluators.py - Evaluators that score Finnie's quality
"""

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from src.core.config import judge_llm
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# define 3 routing evaluators
# 1. routing_accuracy - headline metric - strict match
# 2. routing_precision - catches overrouting(fanning out to multiple agents, when single agent would do - cost waste)
# 3. routing_recall - catches underrouting(missed agents - quality loss)


# 1. Routing accuracy
# The most critical metric —> wrong routing = wrong answer (regardless of agent quality)
def routing_accuracy(run: Any, example: Any) -> dict:
    """Did the orchestrator dispatch to the right agent(s)?"""

    actual = set(run.outputs.get("route", []))
    expected = set(example.outputs.get("agents", []))

    # strict match: did the system fire exactly the right agent set?
    strict_score = 1.0 if actual == expected else 0.0

    if not expected:
        return {
            "key": "routing_accuracy",
            "score": strict_score,
            "comment": "Empty expected set - check dataset entry.",
        }

    # Calculating Precision, Recall & F1 metrics
    intersect = actual & expected  # elements present in both sets

    # precision-> Of the agents fired, what fraction were correct?
    precision = len(intersect) / len(actual) if actual else 0.0
    # recall -> Of the agents that should have fired, what fraction did?
    recall = len(intersect) / len(expected)
    # harmonic mean of precision & recall
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0

    comment = (
        f"expected={sorted(expected)} actual={sorted(actual)} "
        f"precision={precision:.2f} recall={recall:.2f} f1={f1:.2f}"
    )

    return {
        "key": "routing_accuracy",
        "score": strict_score,
        "comment": comment,
    }


# 2. Routing Precision
def routing_precision(run: Any, example: Any) -> dict:
    """Of agents that fired, how many were expected? (catches over-routing)"""
    actual = set(run.outputs.get("route", []))
    expected = set(example.outputs.get("agents", []))
    if not actual:
        return {"key": "routing_precision", "score": 0.0}
    precision = len(actual & expected) / len(actual)
    return {"key": "routing_precision", "score": precision}


# 3. Routing Recall
def routing_recall(run: Any, example: Any) -> dict:
    """How many of the EXPECTED agents actually fired?"""
    actual = set(run.outputs.get("route", []))
    expected = set(example.outputs.get("agents", []))
    if not expected:
        return {"key": "routing_recall", "score": 0.0}
    recall = len(actual & expected) / len(expected)
    return {"key": "routing_recall", "score": recall}


# Retrieval quality evaluators:
# 1. Source-based MRR
# 2. Recall@5
# 3. hit@1


def _chunk_source(chunk: dict) -> str:
    """Extract the source URL from a retrieved chunk."""
    return chunk.get("source_url") or chunk.get("source") or ""


def mrr_at_5(run: Any, example: Any) -> dict:
    """Mean Reciprocal Rank @ 5."""
    chunks = run.outputs.get("chunks", [])
    gold = set(
        example.outputs.get("relevant_sources", [])
    )  # gold = retrievel dataset defined datasets.py

    if not gold:
        return {
            "key": "mrr_at_5",
            "score": None,
            "comment": "negative case — MRR not applicable; see off_topic_check",
        }

    # Find rank of first chunk whose source is in the gold set
    for rank, chunk in enumerate(chunks[:5], start=1):
        source = _chunk_source(chunk)
        if source in gold:
            mrr = 1.0 / rank
            return {
                "key": "mrr_at_5",
                "score": mrr,
                "comment": f"first_gold_at_rank={rank} source={source}",
            }

    # No gold source in top-5 indicates a miss
    retrieved_sources = [_chunk_source(c) for c in chunks[:5]]
    return {
        "key": "mrr_at_5",
        "score": 0.0,
        "comment": f"no gold in top-5 | gold={sorted(gold)[:1]}... got={retrieved_sources[:3]}...",
    }


def recall_at_5(run: Any, example: Any) -> dict:
    """did at least one gold source appear in top-5?"""
    chunks = run.outputs.get("chunks", [])
    gold = set(example.outputs.get("relevant_sources", []))

    if not gold:
        return {"key": "recall_at_5", "score": None}  # negative case

    retrieved = {_chunk_source(c) for c in chunks[:5]}
    found = bool(retrieved & gold)
    return {"key": "recall_at_5", "score": 1.0 if found else 0.0}


def hit_at_1(run: Any, example: Any) -> dict:
    """Stricter metric: was the FIRST chunk a gold source?"""
    chunks = run.outputs.get("chunks", [])
    gold = set(example.outputs.get("relevant_sources", []))

    if not gold:
        return {"key": "hit_at_1", "score": None}

    if not chunks:
        return {"key": "hit_at_1", "score": 0.0, "comment": "no chunks returned"}

    top_source = _chunk_source(chunks[0])
    score = 1.0 if top_source in gold else 0.0
    return {"key": "hit_at_1", "score": score, "comment": f"top_source={top_source}"}


# Generation evaluators (LLM-as-judge + keyword check)
# Judge model — stronger than the production model we're judging.
# DO NOT use the same model as the one generating, or it would introduce bias. gpt-4o-mini generates & gpt-4o judges.

_judge_llm = judge_llm

# Faithfulness — "is the answer grounded in the retrieved chunks?"
FAITHFULNESS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert evaluator. Assess whether the AI's answer is faithful "
            "to the provided retrieval context chunks.\n\n"
            "Score 1.0 = fully faithful: every factual claim is supported by the context\n"
            "Score 0.5 = partially faithful: some claims unsupported but core is grounded\n"
            "Score 0.0 = not faithful: substantial claims contradict or are absent from context\n\n"
            "Focus on factual claims (numbers, definitions, mechanisms). Ignore stylistic "
            "differences and well-known general financial concepts. If context is empty "
            "or marginal, score 0.5 if the answer admits insufficient info, else 0.0.\n\n"
            'Respond with ONLY this JSON: {{"score": <float>, "reason": "<one sentence>"}}',
        ),
        ("human", "Context:\n{context}\n\nQuestion: {question}\n\nAnswer to evaluate:\n{answer}"),
    ]
)


def faithfulness_evaluator(run: Any, example: Any) -> dict:
    """LLM-as-judge: are the answer's claims supported by retrieved chunks?"""
    answer = run.outputs.get("final_answer", "")
    chunks = run.outputs.get("chunks", [])
    question = example.inputs.get("query", "")

    if not answer:
        return {"key": "faithfulness", "score": 0.0, "comment": "no answer generated"}

    context = (
        "\n\n".join(f"[{c.get('source_url', 'unknown')}] {c.get('text', '')[:500]}" for c in chunks)
        or "(no context retrieved)"
    )

    messages = FAITHFULNESS_PROMPT.format_messages(
        context=context[:4000],  # cap to control judge cost
        question=question,
        answer=answer,
    )
    try:
        response = _judge_llm.invoke(messages).content.strip()
        start, end = response.find("{"), response.rfind("}") + 1
        parsed = json.loads(response[start:end])
        return {
            "key": "faithfulness",
            "score": float(parsed.get("score", 0.5)),
            "comment": parsed.get("reason", "")[:200],
        }
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Faithfulness judge parse failed: %s", e)
        return {"key": "faithfulness", "score": 0.5, "comment": "judge parse failed"}


# Correctness — "does the answer match the reference answer?"
CORRECTNESS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert evaluator. Compare the AI's answer to the expected "
            "reference answer for factual accuracy.\n\n"
            "Score 1.0 = all key facts correct, no critical omissions\n"
            "Score 0.5 = partially correct OR missing important facts\n"
            "Score 0.0 = key facts wrong, contradicts reference, or fundamentally off-topic\n\n"
            "Focus on factual accuracy, not exact wording or style. The AI's answer "
            "may include extra correct info; that's fine. Only penalize wrong facts "
            "or missing critical ones.\n\n"
            'Respond with ONLY this JSON: {{"score": <float>, "reason": "<one sentence>"}}',
        ),
        (
            "human",
            "Question: {question}\n\nExpected answer:\n{expected}\n\nAI's actual answer:\n{actual}",
        ),
    ]
)


def correctness_evaluator(run: Any, example: Any) -> dict:
    """LLM-as-judge: does the answer factually match the reference?"""
    actual = run.outputs.get("final_answer", "")
    expected = example.outputs.get("reference_answer", "")
    question = example.inputs.get("query", "")

    if not actual or not expected:
        return {"key": "correctness", "score": 0.0, "comment": "missing answer or reference"}

    messages = CORRECTNESS_PROMPT.format_messages(
        question=question, expected=expected, actual=actual
    )
    try:
        response = _judge_llm.invoke(messages).content.strip()
        start, end = response.find("{"), response.rfind("}") + 1
        parsed = json.loads(response[start:end])
        return {
            "key": "correctness",
            "score": float(parsed.get("score", 0.5)),
            "comment": parsed.get("reason", "")[:200],
        }
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Correctness judge parse failed: %s", e)
        return {"key": "correctness", "score": 0.5, "comment": "judge parse failed"}


# Keyword correctness — "does the answer include critical facts?"
# Cheap substring check. Only scores examples with must_contain_keywords.
def keyword_correctness(run: Any, example: Any) -> dict:
    """Substring check: do critical keywords appear in the answer?"""
    expected_keywords = example.outputs.get("must_contain_keywords", [])
    if not expected_keywords:
        return {"key": "keyword_correctness", "score": None}

    answer = run.outputs.get("final_answer", "").lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in answer)
    score = hits / len(expected_keywords)
    return {
        "key": "keyword_correctness",
        "score": score,
        "comment": f"hit {hits}/{len(expected_keywords)} keywords: {expected_keywords}",
    }


# Guardrails evaluators
def guard_action_correct(run, example):
    """Did the guard take the expected action (pass/block/redact_input)?"""
    expected = example.outputs.get("expected_action", "pass")
    is_safe = run.outputs.get("is_safe_input", True)
    input_redactions = run.outputs.get("input_redactions", [])

    if expected == "block":
        actual = "block" if not is_safe else "pass"
    elif expected == "redact_input":
        actual = "redact_input" if (is_safe and input_redactions) else "pass"
    else:  # "pass"
        actual = "pass" if (is_safe and not input_redactions) else "unexpected"

    score = 1.0 if actual == expected else 0.0
    return {
        "key": "guard_action_correct",
        "score": score,
        "comment": f"expected={expected} actual={actual}",
    }


def input_pii_entities_correct(run, example):
    """For redact_input examples: did Presidio find the expected entity types?"""
    expected_entities = set(example.outputs.get("expected_input_entities", []))
    if not expected_entities:
        return {"key": "input_pii_entities_correct", "score": None}

    actual_entities = {r.get("type") for r in run.outputs.get("input_redactions", [])}
    if not actual_entities:
        return {
            "key": "input_pii_entities_correct",
            "score": 0.0,
            "comment": "no entities redacted",
        }

    intersect = expected_entities & actual_entities
    score = len(intersect) / len(expected_entities)
    return {
        "key": "input_pii_entities_correct",
        "score": score,
        "comment": f"expected={sorted(expected_entities)} got={sorted(actual_entities)}",
    }


def block_category_correct(run: Any, example: Any) -> dict:
    """For blocked queries: did the right category trigger? (precision check)"""
    expected_cat = example.outputs.get("expected_block_category")
    if not expected_cat or expected_cat == "ok":
        return {"key": "block_category_correct", "score": None}  # opt-out

    actual_cat = run.outputs.get("input_block_category", "ok")
    score = 1.0 if actual_cat == expected_cat else 0.0
    return {
        "key": "block_category_correct",
        "score": score,
        "comment": f"expected={expected_cat} actual={actual_cat}",
    }


def pii_leak_check(run: Any, example: Any) -> dict:
    """Universal check: does the final_answer contain any unredacted PII?

    Catches the failure where redaction was supposed to fire but didn't.
    """
    from src.guardrails.patterns import PII_PATTERNS

    answer = run.outputs.get("final_answer", "")

    leaked = []
    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(answer):
            leaked.append(pii_type)

    score = 0.0 if leaked else 1.0
    return {
        "key": "no_pii_leak",
        "score": score,
        "comment": f"leaked types: {leaked}" if leaked else "clean",
    }
