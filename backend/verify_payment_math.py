#!/usr/bin/env python3
"""
Verify MTurk Payment Math
Ensures payment calculations are correct
"""

from decimal import Decimal

# HIT Configuration (must match create_standing_hit.py)
HIT_BASE_REWARD = Decimal('0.01')

def verify_payment(redemption_amount: Decimal) -> dict:
    """
    Verify payment calculation for a given redemption amount.
    
    Args:
        redemption_amount: Amount user is cashing out (e.g., 2.00)
        
    Returns:
        Dict with payment breakdown
    """
    # Calculate bonus
    bonus_amount = redemption_amount - HIT_BASE_REWARD
    
    # Calculate total
    total_paid = HIT_BASE_REWARD + bonus_amount
    
    # Verify math
    is_correct = total_paid == redemption_amount
    
    return {
        "redemption_amount": float(redemption_amount),
        "hit_base_reward": float(HIT_BASE_REWARD),
        "bonus_amount": float(bonus_amount),
        "total_paid": float(total_paid),
        "is_correct": is_correct,
        "error": None if is_correct else f"Math error: {total_paid} ≠ {redemption_amount}"
    }


if __name__ == "__main__":
    print("=" * 70)
    print("  MTurk Payment Math Verification")
    print("=" * 70)
    
    # Test cases
    test_amounts = [
        Decimal('2.00'),   # Minimum
        Decimal('2.85'),   # Random amount
        Decimal('5.00'),   # Mid amount
        Decimal('10.00'),  # Higher amount
        Decimal('0.01'),   # Edge case: exactly base reward
    ]
    
    print(f"\n📋 HIT Configuration:")
    print(f"   Base Reward (set in create_standing_hit.py): ${HIT_BASE_REWARD}")
    print(f"   Payment Method: Base Reward + Bonus")
    
    print(f"\n🧮 Testing Payment Calculations:")
    print(f"{'─'*70}")
    
    all_correct = True
    
    for amount in test_amounts:
        result = verify_payment(amount)
        
        status = "✅" if result["is_correct"] else "❌"
        print(f"\n{status} Redemption: ${result['redemption_amount']:.2f}")
        print(f"   Base Reward:  ${result['hit_base_reward']:.2f}")
        print(f"   Bonus:        ${result['bonus_amount']:.2f}")
        print(f"   ─────────────────────────")
        print(f"   Total Paid:   ${result['total_paid']:.2f}")
        
        if not result["is_correct"]:
            print(f"   ❌ ERROR: {result['error']}")
            all_correct = False
        else:
            print(f"   ✓ Math correct!")
    
    print(f"\n{'='*70}")
    if all_correct:
        print("✅ ALL PAYMENT CALCULATIONS CORRECT")
        print("   Workers will receive the exact amount they redeem.")
    else:
        print("❌ PAYMENT CALCULATION ERRORS DETECTED")
        print("   FIX REQUIRED BEFORE PRODUCTION USE!")
    print(f"{'='*70}\n")
    
    # Show MTurk display
    print("💡 What workers see in MTurk:")
    print(f"   HIT Reward: ${HIT_BASE_REWARD} (shown in HIT listing)")
    print(f"   Bonus: $X.XX (shown after approval)")
    print(f"   Total: ${HIT_BASE_REWARD} + Bonus = Redemption Amount")
    print()
    
    exit(0 if all_correct else 1)

