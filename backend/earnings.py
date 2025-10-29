"""
Earnings calculation system for play-to-earn game.
Calculates suggested earnings based on player performance metrics.
"""

from decimal import Decimal
from typing import Dict, Tuple


# Base earnings configuration
BASE_EARNING = Decimal("0.25")  # Base payment per completed game
WIN_BONUS = Decimal("0.50")  # Bonus for correctly identifying AI
VOTE_BONUS = Decimal("0.10")  # Bonus for participating in voting


def calculate_participation_multiplier(num_messages: int, discussion_duration: int = 180) -> Decimal:
    """
    Calculate participation multiplier based on message count.
    
    Args:
        num_messages: Number of messages sent by the player
        discussion_duration: Length of discussion in seconds
        
    Returns:
        Multiplier between 0.5 and 1.5
    """
    # Expect roughly 1 message per 30 seconds for full participation
    expected_messages = max(1, discussion_duration / 30)
    
    # Calculate ratio
    participation_ratio = num_messages / expected_messages
    
    # Convert to multiplier: 0 messages = 0.5x, expected = 1.0x, double = 1.5x
    multiplier = Decimal(str(min(1.5, max(0.5, 0.5 + participation_ratio * 0.5))))
    
    return multiplier


def calculate_earnings(
    game_completed: bool = True,
    won_game: bool = False,
    num_messages: int = 0,
    discussion_duration: int = 180,
    voted: bool = False,
) -> Tuple[Decimal, Dict[str, Decimal]]:
    """
    Calculate suggested earnings based on performance metrics.
    
    Args:
        game_completed: Whether the game was completed
        won_game: Whether user correctly identified the AI
        num_messages: Number of messages sent during discussion
        discussion_duration: Length of discussion in seconds
        voted: Whether user participated in voting
        
    Returns:
        Tuple of (total_earnings, breakdown_dict)
    """
    breakdown = {}
    
    if not game_completed:
        return Decimal("0.00"), {"incomplete": Decimal("0.00")}
    
    # Base earning for completion
    breakdown["base"] = BASE_EARNING
    
    # Win bonus
    if won_game:
        breakdown["win_bonus"] = WIN_BONUS
    
    # Voting bonus
    if voted:
        breakdown["vote_bonus"] = VOTE_BONUS
    
    # Calculate subtotal before participation multiplier
    subtotal = sum(breakdown.values())
    
    # Participation multiplier
    participation_mult = calculate_participation_multiplier(num_messages, discussion_duration)
    breakdown["participation_multiplier"] = participation_mult
    
    # Final earnings
    total = subtotal * participation_mult
    
    # Round to 2 decimal places
    total = Decimal(str(round(float(total), 2)))
    
    breakdown["total"] = total
    
    return total, breakdown


def format_earnings(amount: Decimal) -> str:
    """
    Format earnings amount for display.
    
    Args:
        amount: Earnings amount
        
    Returns:
        Formatted string (e.g., "$1.25")
    """
    return f"${float(amount):.2f}"


def get_earnings_tier(total_earnings: Decimal) -> Dict[str, any]:
    """
    Get earnings tier information based on total lifetime earnings.
    
    Args:
        total_earnings: Total lifetime earnings
        
    Returns:
        Dict with tier name, color, and next tier threshold
    """
    tiers = [
        {"name": "Rookie", "threshold": Decimal("0"), "color": "#6b7280", "next": Decimal("10")},
        {"name": "Player", "threshold": Decimal("10"), "color": "#3b82f6", "next": Decimal("25")},
        {"name": "Pro", "threshold": Decimal("25"), "color": "#8b5cf6", "next": Decimal("50")},
        {"name": "Elite", "threshold": Decimal("50"), "color": "#f59e0b", "next": Decimal("100")},
        {"name": "Master", "threshold": Decimal("100"), "color": "#22c55e", "next": Decimal("250")},
        {"name": "Legend", "threshold": Decimal("250"), "color": "#ec4899", "next": None},
    ]
    
    for i, tier in enumerate(tiers):
        if total_earnings >= tier["threshold"]:
            current_tier = tier
            if i < len(tiers) - 1:
                current_tier["next"] = tiers[i + 1]["threshold"]
        else:
            break
    
    return current_tier

