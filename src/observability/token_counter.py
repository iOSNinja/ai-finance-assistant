"""
src/observability/token_counter.py — Pre-flight token + cost estimation.

  - estimate_tokens(messages, model): count tokens BEFORE calling the LLM
  - estimate_cost(input_tokens, est_output_tokens, model): $ estimate
  - TokenEstimate dataclass: bundles input/output/cost/model for caller use

"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

import tiktoken
from langchain_core.messages import BaseMessage

# Per-model pricing (in USD per 1M tokens)
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    # model_name: (input_per_1M, output_per_1M)
    "gpt-4o-mini":        (0.15,  0.60),
    "gpt-4o":             (2.50,  10.00),
    "gpt-4o-mini-2024-07-18": (0.15,  0.60),
    "gpt-4-turbo":        (10.00, 30.00),
    "text-embedding-3-small": (0.02, 0.0),   # embeddings have no output cost
    "text-embedding-3-large": (0.13, 0.0),
}

_OUTPUT_RATIO = 0.40
_OUTPUT_CAP_TOKENS = 800

@dataclass
class TokenEstimate:
    """Result of estimate_tokens(): inputs, estimated output and $ cost."""

    model:               str
    input_tokens:        int
    estimated_output_tokens: int
    input_cost_usd:      float
    estimated_output_cost_usd: float

    #computed property
    @property
    def estimated_total_cost_usd(self) -> float:
        return self.input_cost_usd + self.estimated_output_cost_usd
    
    #computed property
    @property
    def estimated_total_tokens(self) -> int:
        return self.input_tokens + self.estimated_output_tokens
    
# Encoder singleton (one per model, cached)
@lru_cache(maxsize=8)
def _encoder_for(model: str) -> tiktoken.Encoding:
    """Cache tiktoken encoders per model — they're not cheap to construct."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        # Unknown model — tiktoken falls back to its newest BPE encoding,
        # which is correct for OpenAI's current model lineup.
        return tiktoken.get_encoding("o200k_base")


# Public API
def estimate_tokens(
    messages: Sequence[BaseMessage] | Sequence[dict] | str,
    model: str = "gpt-4o-mini",
) -> TokenEstimate:
    """Estimate input tokens, output tokens, and total $ cost for an LLM call."""
    text = _messages_to_text(messages)
    encoder = _encoder_for(model)
    input_tokens = len(encoder.encode(text))

    est_output_tokens = min(int(input_tokens * _OUTPUT_RATIO), _OUTPUT_CAP_TOKENS)

    input_per_1M, output_per_1M = _MODEL_PRICING.get(
        model, _MODEL_PRICING["gpt-4o-mini"]
    )
    input_cost = (input_tokens / 1_000_000) * input_per_1M
    estimated_output_cost = (est_output_tokens / 1_000_000) * output_per_1M

    return TokenEstimate(
        model=model,
        input_tokens=input_tokens,
        estimated_output_tokens=est_output_tokens,
        input_cost_usd=round(input_cost, 8),
        estimated_output_cost_usd=round(estimated_output_cost, 8),
    )


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "gpt-4o-mini",
) -> float:
    """Compute $ cost from known token counts."""
    input_per_1M, output_per_1M = _MODEL_PRICING.get(
        model, _MODEL_PRICING["gpt-4o-mini"]
    )
    input_cost = (input_tokens / 1_000_000) * input_per_1M
    output_cost = (output_tokens / 1_000_000) * output_per_1M
    return round(input_cost + output_cost, 8)


# Helpers
def _messages_to_text(messages: Sequence[BaseMessage] | Sequence[dict] | str) -> str:
    """Flatten any supported message format into a single text blob."""
    if isinstance(messages, str):
        return messages

    parts: list[str] = []
    for m in messages:
        if isinstance(m, BaseMessage):
            parts.append(str(m.content))
        elif isinstance(m, dict):
            parts.append(str(m.get("content", "")))
        else:
            parts.append(str(m))
    return "\n".join(parts)