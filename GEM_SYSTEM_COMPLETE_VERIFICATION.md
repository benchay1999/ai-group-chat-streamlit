# Gem Reward System - Complete Verification

## Executive Summary: ✅ VERIFIED WITH ONE CLARIFICATION NEEDED

The gem reward system has been rigorously traced through multiple scenarios. **The implementation is correct** with one potential ambiguity in the proportional return logic that should be confirmed.

---

## Full Trace: 3-Human Game, 50% Stakes

### Scenario Setup

**Players**:
- Player A: 1000 gems → 50% = 500 stake
- Player B: 600 gems → 50% = 300 stake
- Player C: 400 gems → 50% = 200 stake
- **Minimum stake**: 200 gems (lowest)

**Game Result**:
- Player A: 10 votes (winner)
- Player A voted for: ["Player B", "Player C"]
- Accuracy: 2/2 = 100%

---

## Step 1: Game Start - Stake Deduction ✅

**Code**: `deduct_stakes()` (backend/main.py, Line 877)

```python
# For each player:
minimum_stake = 200
user.gem_balance -= minimum_stake  # Atomic operation
```

**Database State After Deduction**:
```
User A: 1000 → 800 gems
User B: 600 → 400 gems
User C: 400 → 200 gems

RoomStake Table:
┌──────────┬─────────┬──────────┬──────────┐
│ Player   │ Stake % │ Amount   │ Deducted │
├──────────┼─────────┼──────────┼──────────┤
│ Player A │ 50%     │ 200      │ 1 (True) │
│ Player B │ 50%     │ 200      │ 1 (True) │
│ Player C │ 50%     │ 200      │ 1 (True) │
└──────────┴─────────┴──────────┴──────────┘
```

**Verification**:
- ✅ Stakes deducted atomically
- ✅ All players lose exactly minimum_stake (200)
- ✅ Rollback on any failure (Lines 939-947)
- ✅ RoomStake records created for audit

---

## Step 2: Game End - Calculate Rewards ✅

**Code**: `calculate_game_rewards()` (backend/main.py, Line 1018)

### Phase 2a: Base Gems
```python
# Line 1086: All humans get base gems
for player_id in human_player_ids:
    rewards[player_id]['base_gems'] = 100
```

**Result**: All players get 100 base gems ✅

### Phase 2b: Stakes Calculation
```python
# Line 1103: Get minimum stake
minimum_stake = 200

# Line 1109-1110: Calculate pot
num_losers = 2  # B and C
total_pot = 200 * 2 = 400
base_pot_per_winner = 400 / 1 = 400

# Line 1122-1131: Winner reward
winner_votes = ["Player B", "Player C"]
human_player_ids = ["Player A", "Player B", "Player C"]

correct_identifications = 2  # Both correct
accuracy = 2/2 = 1.0  # 100%

stake_winnings = int(1.0 * 400) = 400
stake_reward = 200 + 400 = 600  # Refund + winnings

rewards["Player A"]['stake_gems'] = 600
rewards["Player A"]['total_gems'] = 100 + 600 = 700
```

**Breakdown**:
- Base: 100 gems ✅
- Stake refund: 200 gems ✅
- Stake winnings: 400 gems (100% of pot) ✅
- **Total: 700 gems** ✅

### Phase 2c: Losers (No Uncollected)
```python
# Line 1135-1136: Calculate uncollected
total_stakes_distributed_from_pot = 600 - 200 = 400
uncollected_stakes = 400 - 400 = 0  # All collected by winner

# Line 1157-1159: No uncollected, losers get nothing back
rewards["Player B"]['stake_gems'] = 0
rewards["Player C"]['stake_gems'] = 0

rewards["Player B"]['total_gems'] = 100 + 0 = 100
rewards["Player C"]['total_gems'] = 100 + 0 = 100
```

**Breakdown (Losers)**:
- Base: 100 gems ✅
- Stake refund: 0 gems (lost) ✅
- **Total: 100 gems** ✅

---

## Step 3: Apply to User Wallets ✅

**Code**: `save_session_stats()` (backend/main.py, Line 1856)

```python
# Line 1889-1890: Get values from rewards
base_gems = player_rewards['base_gems']
stake_gems = player_rewards['stake_gems']
total_gems = player_rewards['total_gems']

# Line 1929: Use total
gems_earned = total_gems

# Line 1943: Apply to balance
db_user.gem_balance += gems_earned

# Line 1946-1947: Track earned (only positive)
if gems_earned > 0:
    db_user.total_gems_earned += gems_earned
```

**Database Updates**:

**Player A**:
```
Before: 800 gems (after deduction)
Credit: +700 gems
After: 1500 gems
total_gems_earned: +700
Net change: +500 ✅
```

**Player B**:
```
Before: 400 gems (after deduction)
Credit: +100 gems
After: 500 gems
total_gems_earned: +100
Net change: -100 ✅
```

**Player C**:
```
Before: 200 gems (after deduction)
Credit: +100 gems
After: 300 gems
total_gems_earned: +100
Net change: -100 ✅
```

**RoomStake Updates** (Lines 1965-1985):
```
Player A: won_amount=400, returned_amount=200
Player B: won_amount=0, returned_amount=0
Player C: won_amount=0, returned_amount=0
```

✅ **Verified**: All users' wallets updated correctly

---

## Scenario 2: Partial Accuracy (50%) - Uncollected Gems Return

### Setup (Same as before)
- Players A, B, C with 1000, 600, 400 gems
- Minimum stake: 200 gems

### Results
- Player A wins with 50% accuracy (identified 1 out of 2)

### Calculation

**Winner A**:
```python
accuracy = 0.5  # 1/2 correct
stake_winnings = int(0.5 * 400) = 200
stake_reward = 200 + 200 = 400
rewards["Player A"]['stake_gems'] = 400
rewards["Player A"]['total_gems'] = 100 + 400 = 500
```

**Uncollected**:
```python
total_pot = 400
total_stakes_distributed_from_pot = 400 - 200 = 200  # Winnings only
uncollected_stakes = 400 - 200 = 200  # Not collected by winner
```

**Proportional Return to Losers**:
```python
# Line 1142-1155
loser_ids = ["Player B", "Player C"]

# Get original stakes (from player_stakes dict)
player_stakes = {
    "Player A": 500,  # 50% of 1000
    "Player B": 300,  # 50% of 600
    "Player C": 200   # 50% of 400
}

total_loser_stakes = 300 + 200 = 500

# Player B
loser_stake = 300
proportion = 300 / 500 = 0.6
returned_amount = int(0.6 * 200) = 120
rewards["Player B"]['stake_gems'] = 120
rewards["Player B"]['total_gems'] = 100 + 120 = 220

# Player C
loser_stake = 200
proportion = 200 / 500 = 0.4
returned_amount = int(0.4 * 200) = 80
rewards["Player C"]['stake_gems'] = 80
rewards["Player C"]['total_gems'] = 100 + 80 = 180
```

**Final Balances**:
```
Player A: 800 + 500 = 1300 (+300 net)
Player B: 400 + 220 = 620 (+20 net)
Player C: 200 + 180 = 380 (-20 net)

Verification:
Total: +300 + 20 - 20 = +300 (base gems) ✅
Stakes: A won +200, B got +120, C got +80 = 200 in, 200 out ✅
```

✅ **Verified**: Uncollected gems returned proportionally to losers

---

## ⚠️ POTENTIAL AMBIGUITY IN PROPORTIONAL RETURN

### Current Implementation
Uses `player_stakes` (original calculated stake) for proportion:
```python
# Player B had 600 gems → 50% = 300 stake
# Player C had 400 gems → 50% = 200 stake
# B gets 60% of uncollected, C gets 40%
```

### Alternative Interpretation
Use `minimum_stake` (what they actually lost):
```python
# Both B and C lost 200 gems (minimum)
# Both should get 50% of uncollected each
```

### Which Is Correct?

**Current implementation** (uses original stake): Makes sense because:
- Player B took more "risk" (would have lost 300 in full-stake room)
- Proportional to their financial commitment
- More fair for players with different balances

**Alternative** (equal split): Could argue:
- Both lost the same amount (200)
- Should get equal return

**My Recommendation**: Keep current implementation (uses original stake) as it's more fair and nuanced.

However, this should be **confirmed with the user** based on their original intent.

---

## Requirement Verification

### ✅ Requirement 1: Base Pay vs Stakes Distinction

**Base Gems** (Separate):
- Calculated in `base_gems` field
- 50 for single-human winner
- 100 for all multi-human players

**Stakes** (Separate):
- Calculated in `stake_gems` field
- Includes refund + winnings for winners
- Includes partial returns for losers

**Combined for Wallet**:
- `total_gems = base_gems + stake_gems`
- Applied to `gem_balance` as single transaction

✅ **Verified**: Correctly distinguished and combined

---

### ✅ Requirement 2: Rewarding Mechanism Robust

**Atomic Transactions**:
- Stake deduction: All-or-nothing (Line 939-941 rollback)
- Gem crediting: All in one db session (Line 1824)
- Commit only after all operations (Line 2071)

**Validation Layers**:
1. Room creation: Check >= 250 gems (Line 4432-4437)
2. Room joining: Check >= 250 gems (Line 5096-5102)
3. Stake deduction: Check >= minimum_stake (Line 944-947)
4. Vote submission: Validate count/targets (Line 5684-5699)

**Error Handling**:
- Try/catch at each level
- Rollback on any error
- Detailed logging
- Continue processing other players if one fails

✅ **Verified**: Robust and rigorous

---

### ✅ Requirement 3: Uncollected Gems Return to Losers

**Loser Filter** (Line 1141):
```python
loser_ids = [pid for pid in human_player_ids if pid not in top_voted_players]
```
✅ Only human losers (excludes winners)

**Proportional Calculation** (Lines 1144-1149):
```python
# Gets each loser's original stake
loser_stake = player_stakes.get(loser_id, minimum_stake)
proportion = loser_stake / total_loser_stakes
returned_amount = int(proportion * uncollected_stakes)
```
✅ Proportional to original stake

**Applied to Wallet** (Line 1943):
```python
db_user.gem_balance += gems_earned  # Includes returned amount
```
✅ Actually credited to wallet

---

### ✅ Requirement 4: 250 Gems Minimum Enforcement

**Room Creation** (Line 4428-4437):
```python
if max_humans > 1:
    if not current_user:
        return {"error": "Authentication required..."}
    
    if current_user.gem_balance < 250:
        return {"error": f"Insufficient gems. Need 250..."}
```
✅ Creator must have >= 250 gems

**Room Joining** (Line 5096-5102):
```python
if max_humans > 1:
    if not current_user:
        return {"error": "Authentication required..."}
    
    if current_user.gem_balance < 250:
        return {"error": f"Insufficient gems. Need 250..."}
```
✅ Joiners must have >= 250 gems

**Frontend Display** (RoomCard.jsx):
```javascript
const hasEnoughGems = max_humans > 1 ? (userGemBalance >= 250) : true;
const canJoin = hasEnoughGems;

// Button disabled if insufficient
disabled={!canJoin}
```
✅ UI prevents joining if < 250 gems

---

### ✅ Requirement 5: Gems Applied to All Users

**For Each Human Player** (Lines 1872-2010):
```python
# Line 1861: Calculate rewards for ALL humans
rewards = await calculate_game_rewards(...)

# Line 1872-1874: Process each human player
for player in state.get('players', []):
    if player.get('role') != 'human':
        continue  # Skip AI
    
    # Line 1889-1943: For each authenticated human
    gems_earned = total_gems
    db_user.gem_balance += gems_earned
    
    # Line 1946-1947: Track earned (only positive)
    if gems_earned > 0:
        db_user.total_gems_earned += gems_earned
```

**Verification**:
- ✅ Loops through ALL human players
- ✅ Skips AI players correctly
- ✅ Credits/debits each user's wallet
- ✅ Updates total_gems_earned (only for gains)
- ✅ Atomic transaction for all updates

**Example**: 3 humans all get updates:
- Player A: +700 gems ✅
- Player B: +100 gems ✅  
- Player C: +100 gems ✅

All committed in single transaction (Line 2071) ✅

---

## Mathematical Verification

### Test Case 1: Winner 100% Accuracy

**Deductions** (Step 1):
- A: 1000 - 200 = 800
- B: 600 - 200 = 400
- C: 400 - 200 = 200

**Rewards** (Step 2):
```
Player A:
  base_gems = 100
  stake_gems = 200 (refund) + 400 (pot) = 600
  total = 700

Player B & C:
  base_gems = 100
  stake_gems = 0
  total = 100
```

**Credits** (Step 3):
- A: 800 + 700 = **1500** (+500 net)
- B: 400 + 100 = **500** (-100 net)
- C: 200 + 100 = **300** (-100 net)

**Balance Check**:
```
Total change: +500 - 100 - 100 = +300
Base gems: 3 * 100 = 300 ✅

Stakes in/out:
- A won: +400 (from pot)
- B lost: -200 (to pot)
- C lost: -200 (to pot)
- Balance: +400 - 200 - 200 = 0 ✅
```

✅ **Perfect balance**!

---

### Test Case 2: Winner 50% Accuracy (Uncollected Return)

**Deductions** (Step 1):
- Same as above: All -200

**Rewards** (Step 2):
```
Player A (winner, 50% accuracy):
  base_gems = 100
  stake_winnings = 0.5 * 400 = 200
  stake_gems = 200 (refund) + 200 (winnings) = 400
  total = 500

Uncollected: 400 - 200 = 200

Player B (loser):
  Original stake: 300 (50% of 600)
  Proportion: 300/(300+200) = 0.6
  Returned: 0.6 * 200 = 120
  base_gems = 100
  stake_gems = 120
  total = 220

Player C (loser):
  Original stake: 200 (50% of 400)
  Proportion: 200/(300+200) = 0.4
  Returned: 0.4 * 200 = 80
  base_gems = 100
  stake_gems = 80
  total = 180
```

**Credits** (Step 3):
- A: 800 + 500 = **1300** (+300 net)
- B: 400 + 220 = **620** (+20 net)
- C: 200 + 180 = **380** (-20 net)

**Balance Check**:
```
Total change: +300 + 20 - 20 = +300
Base gems: 3 * 100 = 300 ✅

Stakes in/out:
- A won: +200 (50% of pot) + 200 (refund) = +400 total
- A net stakes: +200 (won from pot)
- B lost 200, got 120 back: -80
- C lost 200, got 80 back: -120
- Stakes balance: +200 - 80 - 120 = 0 ✅
```

✅ **Perfect balance**!

---

### Test Case 3: All Players Tie

**Scenario**:
- All 3 players get equal votes
- No clear winner

**Rewards** (Step 2):
```python
# Line 1160-1163
num_winners = 3  # All tied
num_losers = 0

# Everyone gets full refund
for player_id in ["Player A", "Player B", "Player C"]:
    base_gems = 100
    stake_gems = 200  # Full refund
    total = 300
```

**Credits** (Step 3):
- A: 800 + 300 = **1100** (+100 net)
- B: 400 + 300 = **700** (+100 net)
- C: 200 + 300 = **500** (+100 net)

**Balance Check**:
```
Total change: +100 + 100 + 100 = +300
Base gems: 3 * 100 = 300 ✅
Stakes: All refunded, no change ✅
```

✅ **Tie handled correctly**!

---

## Single-Human Game Verification

### Scenario: 1 Human, 4 AI

**No Stakes** (Line 898-900):
```python
if max_humans <= 1:
    return True  # Skip deduction
```
✅ No stake deduction for single-human

**Rewards** (Lines 1058-1077):
```python
if num_humans == 1:
    # Winner gets 50
    if player_id in winners:
        base_gems = 50
        stake_gems = 0
        total = 50
    else:
        base_gems = 0
        stake_gems = 0
        total = 0
```

**Wallet Update**:
- Winner: +50 gems ✅
- (No losers in single-human)

✅ **Single-human correct**!

---

## Edge Cases Verification

### Edge Case 1: No Votes Cast

**Scenario**: No one votes (unlikely but possible)

```python
# Line 1164-1168
elif num_winners == 0:
    # Refund stakes to everyone
    for player_id in human_player_ids:
        rewards[player_id]['stake_gems'] = minimum_stake
        rewards[player_id]['total_gems'] = 100 + minimum_stake
```

**Result**: Everyone gets base + full refund ✅

---

### Edge Case 2: Player Leaves Before Game Starts

**Code**: `leave_room_endpoint()` (Line 5089-5121)

```python
# Line 5097-5112: Remove from player_stakes
if player_id in player_stakes:
    removed_stake = player_stakes.pop(player_id)
    
    # Recalculate minimum
    remaining_stakes = list(player_stakes.values())
    if remaining_stakes:
        room['minimum_stake'] = min(remaining_stakes)
```

**Result**:
- Stake removed from calculation ✅
- Minimum recalculated ✅
- No gems deducted (game hasn't started) ✅

---

### Edge Case 3: User Has Exactly 250 Gems

**Validation** (Line 5096-5102):
```python
if current_user.gem_balance < 250:
    return {"error": "Insufficient..."}
```

**Test**:
- User with 250 gems: `250 < 250` → False → Can join ✅
- User with 249 gems: `249 < 250` → True → Blocked ✅

---

### Edge Case 4: Stake Deduction Fails Mid-Way

**Code** (Line 939-947):
```python
# During deduction loop
if user.gem_balance < minimum_stake:
    await db.rollback()  # Rollback ALL
    return False
```

**Scenario**: Player C suddenly has insufficient balance

**Result**:
- All deductions rolled back ✅
- Game cancelled ✅
- Error broadcast to players (Line 5525-5532) ✅
- No partial deductions ✅

---

## Checking Requirements (Detailed)

### ✅ 1. Base Pay vs Stakes Distinction

**Evidence**:
- Line 1086: `base_gems` calculated separately
- Line 1128: `stake_gems` calculated separately
- Line 1172: `total_gems = base_gems + stake_gems`
- Line 1893-1894: Both logged separately
- Line 1994: Tracked separately in credited_players

**Conclusion**: ✅ Clearly distinguished

---

### ✅ 2. Rewarding Mechanism Robust

**Atomicity**:
- Single transaction for deduction (Line 975: `await db.commit()`)
- Single transaction for crediting (Line 2071: `await db.commit()`)
- Rollback on any error

**Idempotency**:
- Line 1828-1842: Checks for duplicate sessions
- Prevents double-crediting

**Validation**:
- Balance checks before deduction
- Vote count validation
- Sanity checks on amounts (Line 1931-1937)

**Audit Trail**:
- RoomStake table tracks all operations
- Logs every step
- won_amount and returned_amount recorded

**Conclusion**: ✅ Robust and rigorous

---

### ⚠️ 3. Uncollected Gems Return - NEEDS CLARIFICATION

**Current Implementation**:
Proportional to `player_stakes` (original calculated stake):
```python
loser_stake = player_stakes.get(lid, minimum_stake)  # 300 or 200
proportion = loser_stake / total_loser_stakes
```

**Question for User**: Should uncollected gems be returned:
- **Option A** (current): Proportional to original stake calculation?
  - Player B (600 gems → 300 stake) gets 60%
  - Player C (400 gems → 200 stake) gets 40%
  
- **Option B**: Equal split (since both lost same minimum)?
  - Player B gets 50%
  - Player C gets 50%

**My Analysis**: Current implementation (Option A) is more sophisticated and fair, but the requirement states "proportional to the amount of gems each had for the game" which is ambiguous.

**Recommendation**: Keep current (Option A) - it's more fair

**Status**: ⚠️ Needs user confirmation on interpretation

---

### ✅ 4. 250 Gems Minimum Works Correctly

**Create Room** (Line 4428-4437):
- ✅ Checks authenticated user
- ✅ Validates `>= 250` gems
- ✅ Returns error if insufficient

**Join Room** (Line 5096-5102):
- ✅ Checks authenticated user
- ✅ Validates `>= 250` gems
- ✅ Returns error if insufficient

**Frontend** (RoomCard.jsx):
- ✅ Fetches user gem balance
- ✅ Calculates `hasEnoughGems`
- ✅ Disables join button if < 250
- ✅ Shows helpful error message

**Edge Cases**:
- Exactly 250: Can join ✅
- 249: Cannot join ✅
- Unauthenticated: Cannot join multi-human ✅

**Conclusion**: ✅ Correctly enforced

---

### ✅ 5. Gems Applied to Wallet for All Users

**User Loop** (Lines 1872-2010):
```python
for player in state.get('players', []):
    if player.get('role') != 'human':
        continue  # Skip AI ✅
    
    # Get rewards for this player
    player_rewards = rewards.get(player_id, {...})
    
    # Credit to database
    db_user.gem_balance += gems_earned
```

**Verification Points**:

1. **All Humans Processed**: ✅
   - Loops through all players
   - Filters to humans only
   - Processes each one

2. **Authenticated Users Only**: ✅
   - Line 1877-1879: Skips if not mapped
   - Makes sense - can't credit anonymous users

3. **Balance Updated**: ✅
   - Line 1943: `db_user.gem_balance += gems_earned`
   - Direct database update

4. **total_gems_earned Tracking**: ✅
   - Line 1946-1947: Only adds positive amounts
   - Prevents stake losses from reducing lifetime earnings

5. **Atomic Commit**: ✅
   - Line 2071: Single commit for all players
   - All-or-nothing update

**Test**: 3 humans in game
- Player A (auth): Gets gems ✅
- Player B (auth): Gets gems ✅
- Player C (auth): Gets gems ✅
- All in same transaction ✅

**Conclusion**: ✅ All authenticated users updated correctly

---

## Discovered Issues

### ⚠️ Issue #1: Proportional Return Ambiguity

**Current**: Uses original `player_stakes` for proportion
**Question**: Should it use actual amount lost (all equal minimum_stake)?

**Impact**: Minor - only affects fairness of uncollected return distribution
**Severity**: LOW - Both interpretations are valid
**Action**: Needs user clarification

---

### ⚠️ Issue #2: Unauthenticated Players Don't Get Gems

**Current Behavior** (Line 1877-1879):
```python
if not mapped_user_id_str:
    print(f"⚠️ Player {player_id} is not authenticated, skipping gem credit")
    continue
```

**Is This Correct?**
- Yes, because gems are tied to user accounts
- Anonymous players can't have persistent gem wallets
- This is intentional and correct

**Conclusion**: ✅ Not a bug, working as designed

---

## Final Verification Results

| Requirement | Status | Notes |
|-------------|--------|-------|
| **Base Pay vs Stakes Distinction** | ✅ CORRECT | Tracked separately, combined for wallet |
| **Mechanism Robust & Rigorous** | ✅ CORRECT | Atomic, validated, error-handled |
| **Uncollected Return to Losers** | ⚠️ CLARIFY | Works correctly, but proportion method ambiguous |
| **250 Gems Minimum** | ✅ CORRECT | Enforced at create, join, and frontend |
| **Gems Applied to All Users** | ✅ CORRECT | All authenticated humans updated atomically |

---

## Comprehensive Flow Diagram

```
GAME START
==========
User Wallets:     A: 1000, B: 600, C: 400
Calculate stakes: A: 500, B: 300, C: 200
Minimum stake:    200

↓ deduct_stakes()

Database UPDATE (ATOMIC):
  A: 1000 - 200 = 800 ✅
  B: 600 - 200 = 400 ✅
  C: 400 - 200 = 200 ✅
  RoomStake records created ✅

↓ Game plays out...

GAME END
========
Votes counted → Player A wins
A's identification: 100% accuracy

↓ calculate_game_rewards()

Rewards Calculated:
  A: base=100, stakes=600, total=700
  B: base=100, stakes=0, total=100
  C: base=100, stakes=0, total=100

↓ save_session_stats()

Database UPDATE (ATOMIC):
  A: 800 + 700 = 1500 ✅
  B: 400 + 100 = 500 ✅
  C: 200 + 100 = 300 ✅
  
  total_gems_earned:
    A: +700 ✅
    B: +100 ✅
    C: +100 ✅
  
  RoomStake records updated:
    A: won=400, returned=200 ✅
    B: won=0, returned=0 ✅
    C: won=0, returned=0 ✅

↓ Commit transaction

FINAL STATE
===========
User A: 1500 gems (+500 net) ✅
User B: 500 gems (-100 net) ✅
User C: 300 gems (-100 net) ✅

Balance: +500 - 100 - 100 = +300 = base gems ✅
Stakes: A won 400, B+C lost 400 ✅
```

---

## Conclusion

### Overall Assessment: ✅ VERIFIED

The gem reward system is:

1. ✅ **Mathematically Correct**: All scenarios balance properly
2. ✅ **Base/Stakes Separated**: Tracked separately in calculation
3. ✅ **Robustly Implemented**: Atomic, validated, error-handled
4. ✅ **250 Gems Enforced**: Multiple validation layers
5. ✅ **Applied to All Users**: Every authenticated human updated

### One Clarification Needed: ⚠️

**Proportional Return Question**: Should uncollected gems be returned based on:
- **Current** (Option A): Original stake calculation (player_stakes dict)
- **Alternative** (Option B): Actual amount lost (minimum_stake, equal for all)

**Current implementation uses Option A**, which is more sophisticated and arguably more fair.

### Confidence: HIGH ✅

All core mechanisms verified and working correctly. The one ambiguity is a design choice, not a bug.

**Recommendation**: Confirm proportional return logic with user, then APPROVED for production.

