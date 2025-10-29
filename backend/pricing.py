"""
Pricing configuration for LLM token usage.
Hardcoded pricing per 1M tokens for common models.
"""

from typing import Dict, Tuple
from decimal import Decimal


# Pricing per 1M tokens (input, output) in USD
# Updated as of 2025 - verify with current provider pricing
MODEL_PRICING: Dict[str, Tuple[Decimal, Decimal]] = {
    # OpenAI models
    "gpt-4": (Decimal("30.00"), Decimal("60.00")),
    "gpt-4-turbo": (Decimal("10.00"), Decimal("30.00")),
    "gpt-4-turbo-preview": (Decimal("10.00"), Decimal("30.00")),
    "gpt-4o": (Decimal("5.00"), Decimal("15.00")),
    "gpt-4o-mini": (Decimal("0.150"), Decimal("0.600")),
    "gpt-4.1-nano": (Decimal("0.20"), Decimal("0.8")),
    "gpt-3.5-turbo": (Decimal("0.50"), Decimal("1.50")),
    "gpt-3.5-turbo-16k": (Decimal("3.00"), Decimal("4.00")),
    
    # Google Gemini models
    "gemini-pro": (Decimal("0.50"), Decimal("1.50")),
    "gemini-1.5-pro": (Decimal("3.50"), Decimal("10.50")),
    "gemini-1.5-flash": (Decimal("0.075"), Decimal("0.30")),
    
    # Anthropic Claude models
    "claude-3-opus": (Decimal("15.00"), Decimal("75.00")),
    "claude-3-sonnet": (Decimal("3.00"), Decimal("15.00")),
    "claude-3-haiku": (Decimal("0.25"), Decimal("1.25")),
    "claude-3-5-sonnet": (Decimal("3.00"), Decimal("15.00")),
    
    # Default fallback pricing (conservative estimate)
    "default": (Decimal("1.00"), Decimal("3.00")),
}


def get_model_pricing(model_name: str) -> Tuple[Decimal, Decimal]:
    """
    Get pricing for a model.
    
    Args:
        model_name: Name of the LLM model
        
    Returns:
        Tuple of (input_price_per_1m, output_price_per_1m) in USD
    """
    # Normalize model name (remove version suffixes, lowercase)
    normalized = model_name.lower().strip()
    
    # Direct match
    if normalized in MODEL_PRICING:
        return MODEL_PRICING[normalized]
    
    # Partial match for versioned models
    for key in MODEL_PRICING.keys():
        if key in normalized or normalized.startswith(key):
            return MODEL_PRICING[key]
    
    # Fallback to default
    return MODEL_PRICING["default"]


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model_name: str
) -> Decimal:
    """
    Calculate the cost for token usage.
    
    Args:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
        model_name: Name of the LLM model
        
    Returns:
        Total cost in USD as Decimal
    """
    input_price, output_price = get_model_pricing(model_name)
    
    # Calculate cost (price is per 1M tokens)
    input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * input_price
    output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * output_price
    
    return input_cost + output_cost


def format_cost(cost: Decimal, currency: str = "USD") -> str:
    """
    Format cost for display.
    
    Args:
        cost: Cost as Decimal
        currency: Currency symbol (default: USD)
        
    Returns:
        Formatted cost string (e.g., "$0.0123")
    """
    if currency == "USD":
        return f"${cost:.4f}"
    return f"{cost:.4f} {currency}"


def format_tokens(tokens: int) -> str:
    """
    Format token count for display.
    
    Args:
        tokens: Number of tokens
        
    Returns:
        Formatted token string (e.g., "1.2K", "1.5M")
    """
    if tokens < 1_000:
        return str(tokens)
    elif tokens < 1_000_000:
        return f"{tokens / 1_000:.1f}K"
    else:
        return f"{tokens / 1_000_000:.2f}M"

