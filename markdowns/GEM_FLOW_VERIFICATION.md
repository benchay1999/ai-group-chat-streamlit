# Gem Reward System - Complete Flow Verification

## Tracing Example: 3-Human Game, 50% Stakes, Winner with 100% Accuracy

### Initial State

**Players**:
- Player A: 1000 gems (50% = 500 stake)
- Player B: 600 gems (50% = 300 stake)
- Player C: 400 gems (50% = 200 stake)
- **Minimum stake**: min(500, 300, 200) = **200 gems**

---

## Step 1: Game Start - Stake Deduction

**Function**: `deduct_stakes()` (Line 877-976)

```python
# Line 909: Get minimum_stake
minimum_stake = room_data.get('minimum_stake', 0)  # 200

# Line 920-950: For each player
for player_id, stake_amount in player_stakes.items():
    # Line 944: Validate sufficient balance
    if user.gem_balance < minimum_stake:  # 200
        return False  # Rollback all
    
    # Line 950: Deduct minimum stake
    user.gem_balance -= minimum_stake  # -200
```

**Database After Step 1**:
```
Player A: 1000 - 200 = 800 gems
Player B: 600 - 200 = 400 gems
Player C: 400 - 200 = 200 gems

RoomStake records created:
- Player A: stake_amount=200, deducted=1
- Player B: stake_amount=200, deducted=1
- Player C: stake_amount=200, deducted=1
```

✅ **Verified**: Stakes deducted correctly, atomic transaction

---

## Step 2: Game Ends - Calculate Rewards

**Function**: `calculate_game_rewards()` (Line 1018-1176)

**Voting Results**:
- Player A: 10 votes (most)
- Player B: 5 votes
- Player C: 3 votes

**Player A's Votes**: `["Player B", "Player C"]`
**Actual Humans**: `["Player A", "Player B", "Player C"]`
**Correct Identifications**: 2/2 = 100%

```python
# Line 1086: All humans get base gems
rewards["Player A"]['base_gems'] = 100
rewards["Player B"]['base_gems'] = 100
rewards["Player C"]['base_gems'] = 100

# Line 1103: minimum_stake = 200
# Line 1109: total_pot = 200 * 2 (losers) = 400
# Line 1110: base_pot_per_winner = 400 / 1 = 400

# Line 1124-1125: Winner calculation
stake_winnings = int(1.0 * 400) = 400
stake_reward = 200 + 400 = 600
rewards["Player A"]['stake_gems'] = 600
rewards["Player A"]['total_gems'] = 100 + 600 = 700

# Line 1135: total_stakes_distributed_from_pot = 600 - 200 = 400
# Line 1136: uncollected_stakes = 400 - 400 = 0

# Line 1140-1157: Losers (no uncollected)
rewards["Player B"]['stake_gems'] = 0
rewards["Player B"]['total_gems'] = 100 + 0 = 100

rewards["Player C"]['stake_gems'] = 0
rewards["Player C"]['total_gems'] = 100 + 0 = 100
```

**Rewards Dict Returned**:
```python
{
  "Player A": {
    'base_gems': 100,
    'stake_gems': 600,  # 200 refund + 400 winnings
    'total_gems': 700,
    'is_winner': True
  },
  "Player B": {
    'base_gems': 100,
    'stake_gems': 0,  # No refund (lost)
    'total_gems': 100
  },
  "Player C": {
    'base_gems': 100,
    'stake_gems': 0,  # No refund (lost)
    'total_gems': 100
  }
}
```

✅ **Verified**: Base and stakes correctly separated

---

## Step 3: Apply to Wallets

**Function**: `save_session_stats()` (Line 1856-2012)

```python
# Line 1861: Get rewards
rewards = await calculate_game_rewards(room_code, room_data, state, db)

# Line 1889-1890: Extract values
total_gems = player_rewards['total_gems']  # 700 for A, 100 for B/C
base_gems = player_rewards['base_gems']    # 100 for all
stake_gems = player_rewards['stake_gems']  # 600, 0, 0

# Line 1929: Use total_gems
gems_earned = total_gems

# Line 1943: Credit to balance
db_user.gem_balance += gems_earned
```

**Database After Step 3**:
```
Player A:
  Before: 800 (after deduction)
  Credit: +700 (100 base + 600 stakes)
  After: 1500 gems
  Net: +500 ✅

Player B:
  Before: 400 (after deduction)
  Credit: +100 (100 base + 0 stakes)
  After: 500 gems
  Net: -100 ✅

Player C:
  Before: 200 (after deduction)
  Credit: +100 (100 base + 0 stakes)
  After: 300 gems
  Net: -100 ✅
```

**Verification**:
```
Total net change: +500 - 100 - 100 = +300
Base gems issued: 3 * 100 = 300 ✅
Stakes balanced: A won 400, B+C lost 400 ✅
```

✅ **Verified**: Gems applied to wallet correctly for all users

---

## Checking Requirements

### Requirement 1: Base Pay vs Stakes Distinction ✅

**Base Pay**:
- Line 1069: Single-human winner gets 50 gems
- Line 1086: Multi-human all players get 100 gems
- Stored separately in rewards dict

**Stakes**:
- Line 1128: `stake_gems` calculated separately
- Includes refund + winnings for winners
- Includes partial returns for losers
- Can be positive (won) or zero/negative conceptually

**In wallet update**:
- Line 1929: `gems_earned = total_gems` (base + stakes combined)
- Line 1943: Applied to `gem_balance`
- Line 1954: Logged separately for debugging

✅ **Verified**: Base and stakes tracked separately in calculation, combined for wallet update

### Requirement 2: Rewarding Mechanism Robust & Rigorous ✅

**Atomicity**:
- Line 877-976: Stake deduction in single transaction
- Line 939-940: Rollback all if any player fails
- Line 1824-2105: Gem crediting in single transaction

**Validation**:
- Line 944: Check sufficient balance before deduction
- Line 1931-1937: Sanity checks on gem amounts
- Line 1686-1699: Vote validation before processing

**Error Handling**:
- Try/catch blocks at multiple levels
- Rollback on any failure
- Detailed logging for debugging

✅ **Verified**: Robust with atomic transactions and validation

### Requirement 3: Uncollected Gems Return to Human Losers ✅

Let me check this with partial accuracy example...


