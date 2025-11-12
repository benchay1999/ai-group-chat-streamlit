# AI Delay System - Visual Guide

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYBRID DELAY SYSTEM                          │
│                                                                 │
│  Input: AI Message (n_char), Previous Message (n_char_prev)   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│               STATISTICAL DELAY CALCULATION                     │
│                                                                 │
│  Base Delay:           1.0 seconds (fixed)                     │
│  Typing Rate:          N(0.3, 0.03) × n_char                   │
│  Context Load:         N(0.03, 0.003) × n_char_prev            │
│  Thinking Time:        Γ(2.5, 0.25) seconds                    │
│                                                                 │
│  Total = Base + Typing + Context + Thinking                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CHUNKING DECISION (30%)                        │
│                                                                 │
│  30% ───> Split into 2-4 chunks                                │
│  70% ───> Send as single message                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              PROPORTIONAL DELAY DISTRIBUTION                    │
│                                                                 │
│  Chunk 1: Total × (chunk1_chars / total_chars)                 │
│  Chunk 2: Total × (chunk2_chars / total_chars)                 │
│  Chunk 3: Total × (chunk3_chars / total_chars)                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CHUNK DELIVERY LOOP                            │
│                                                                 │
│  For each chunk:                                                │
│    1. Show typing indicator                                     │
│    2. Delay: 30% thinking + 70% typing                          │
│    3. Broadcast chunk                                           │
│    4. Inter-chunk pause (0.3-0.5s)                             │
│                                                                 │
│  After all chunks:                                              │
│    5. Hide typing indicator                                     │
│    6. Cooldown (0.8-1.5s)                                      │
│    7. Trigger next agent decisions                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📈 Distribution Visualizations

### Normal Distribution N(0.3, 0.03) - Typing Rate
```
Frequency
    ▲
    │     ╱‾‾╲
    │    ╱    ╲
    │   ╱      ╲
    │  ╱        ╲
    │ ╱          ╲___
    └─────────────────────────> s/char
      0.24 0.27 0.30 0.33 0.36
              μ=0.3
         ←  σ=0.03  →
```
- **Mean**: 0.3s/char
- **68% range**: 0.27-0.33s/char
- **95% range**: 0.24-0.36s/char

### Gamma Distribution Γ(2.5, 0.25) - Thinking Time
```
Frequency
    ▲
    │  ╱╲
    │ ╱  ╲___
    │╱       ‾‾‾╲___
    │               ‾‾‾╲____
    └────────────────────────> seconds
      0    0.5   1.0   1.5
         mode  mean
        ≈0.38 =0.63
```
- **Mean**: 0.625s
- **Mode**: ~0.375s (most common)
- **Range**: 0.3-1.5s (typical)
- **Right-skewed**: Long tail for deep thinking

---

## 🎬 Example Timeline

### Message: "yes, I think so. That makes sense!" (31 chars)
### Previous: "What do you think about this?" (29 chars)

```
Timeline (seconds):
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  0s ────> CALCULATE DELAY                                                  │
│           Base: 1.0s                                                       │
│           Typing: 0.298×31 = 9.24s                                         │
│           Context: 0.031×29 = 0.90s                                        │
│           Thinking: 0.54s                                                  │
│           Total: 11.68s                                                    │
│                                                                             │
│  0s ────> CHUNK DECISION: Yes (30% probability)                            │
│           Chunks: ["yes", "I think so.", "That makes sense!"]             │
│           Delays: [1.13s, 4.15s, 6.40s]                                   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  CHUNK 1: "yes" (3 chars, 1.13s delay)                                    │
│  ├─> 0.0s: Show typing indicator                                          │
│  ├─> 0.0s: Thinking delay (0.34s = 30% of 1.13s)                         │
│  ├─> 0.34s: Typing delay (0.79s = 70% of 1.13s)                          │
│  ├─> 1.13s: Broadcast "yes"                                               │
│  └─> 1.13s: Inter-chunk pause (0.38s)                                     │
│                                                                             │
│  CHUNK 2: "I think so." (11 chars, 4.15s delay)                          │
│  ├─> 1.51s: Thinking delay (1.25s)                                        │
│  ├─> 2.76s: Typing delay (2.91s)                                          │
│  ├─> 5.66s: Broadcast "I think so."                                       │
│  └─> 5.66s: Inter-chunk pause (0.44s)                                     │
│                                                                             │
│  CHUNK 3: "That makes sense!" (17 chars, 6.40s delay)                    │
│  ├─> 6.10s: Thinking delay (1.92s)                                        │
│  ├─> 8.02s: Typing delay (4.48s)                                          │
│  └─> 12.50s: Broadcast "That makes sense!"                                │
│                                                                             │
│  12.50s ──> Hide typing indicator                                          │
│  12.50s ──> Cooldown (1.2s)                                                │
│  13.70s ──> Trigger next agent decisions                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Total time from generation to completion: 13.7 seconds
```

---

## 🔄 Message Flow Diagram

```
Human Message Received
         │
         ▼
  Trigger Agent Decisions ◄───────────────────┐
         │                                     │
         ▼                                     │
  Each AI Decides to Respond                  │
    (probabilistic)                            │
         │                                     │
         ▼                                     │
  Generate Message (LLM)                      │
         │                                     │
         ▼                                     │
  Calculate Statistical Delay ────────────────┤
    • Base: 1.0s                              │
    • Typing: N(0.3,0.03)×n                   │
    • Context: N(0.03,0.003)×n_prev           │
    • Thinking: Γ(2.5,0.25)                   │
         │                                     │
         ▼                                     │
  Chunking Decision (30%)                     │
         │                                     │
    ┌────┴────┐                                │
    │         │                                │
  Yes       No                                 │
    │         │                                │
    ▼         ▼                                │
  Split    Single                              │
  2-4      Chunk                               │
    │         │                                │
    └────┬────┘                                │
         │                                     │
         ▼                                     │
  Distribute Delay Proportionally             │
         │                                     │
         ▼                                     │
  ┌──────────────────────────┐                │
  │  For Each Chunk:         │                │
  │  • Thinking (30%)        │                │
  │  • Typing (70%)          │                │
  │  • Broadcast             │                │
  │  • Inter-chunk pause     │                │
  └──────────────────────────┘                │
         │                                     │
         ▼                                     │
  Cooldown (0.8-1.5s) ────────────────────────┘
         │
         ▼
  Trigger Next Agent (exclude self)
```

---

## 📐 Proportional Distribution Example

### Message: "I agree with that analysis!" (28 chars)
### Total Delay: 10.0s

```
┌────────────────────────────────────────────────────────────┐
│  Chunk 1: "I agree" (7 chars)                             │
│  ───────────────────────                                   │
│  25% of message                                            │
│  Delay: 2.5s                                               │
│    ├─ Thinking: 0.75s (30%)                               │
│    └─ Typing: 1.75s (70%)                                 │
├────────────────────────────────────────────────────────────┤
│  Chunk 2: "with that analysis!" (21 chars)                │
│  ─────────────────────────────────────────────────         │
│  75% of message                                            │
│  Delay: 7.5s                                               │
│    ├─ Thinking: 2.25s (30%)                               │
│    └─ Typing: 5.25s (70%)                                 │
└────────────────────────────────────────────────────────────┘

Total: 2.5s + 7.5s + 0.4s (pause) = 10.4s
```

---

## 🎭 Variance Visualization

### 20 Samples of 100-char Messages (prev=50)

```
Delay (seconds)
   │
45 │                                              ●
   │
40 │                                    ●
   │                       ●    ●   ●
35 │          ●    ●   ●       ●       ●
   │     ●        ●   ●   ●   ●   ●
30 │ ●      ●   ●   ●   ●   ●   ●   ●
   │    ●   ●   ●
25 │ ●
   │
20 │
   └────────────────────────────────────────> Sample #
    1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20

Mean: ~33.2s
Std Dev: ~3.1s
Range: 27.5s - 42.3s
```

**Key Insight**: Most responses cluster around 30-35s, with natural variance creating personality.

---

## 🧮 Quick Calculation Reference

### Formula Components

```
┌───────────────────────────────────────────────────────────┐
│  Component       │  Distribution  │  Example (100 chars)  │
├───────────────────────────────────────────────────────────┤
│  Base            │  Fixed         │  1.0s                │
│  Typing          │  N(0.3, 0.03)  │  30.0s ± 3.0s        │
│  Context (50ch)  │  N(0.03, 0.003)│  1.5s ± 0.15s        │
│  Thinking        │  Γ(2.5, 0.25)  │  0.625s ± 0.4s       │
├───────────────────────────────────────────────────────────┤
│  TOTAL           │                 │  33.1s ± 3.4s        │
└───────────────────────────────────────────────────────────┘
```

### Message Length Impact

```
Characters │ Typing Time  │ Total (typical)
───────────┼──────────────┼────────────────
    20     │   6.0s       │   ~8.6s
    50     │  15.0s       │  ~17.6s
   100     │  30.0s       │  ~33.1s
   150     │  45.0s       │  ~48.6s
   200     │  60.0s       │  ~64.1s
```

### Previous Message Impact

```
Prev Chars │ Context Time │ Impact
───────────┼──────────────┼─────────
     0     │   0.0s       │  None
    25     │   0.75s      │  Minimal
    50     │   1.5s       │  Moderate
   100     │   3.0s       │  Significant
   200     │   6.0s       │  Major
```

---

## 🎯 Tuning Impact Matrix

```
┌─────────────────────────────────────────────────────────────┐
│  Parameter Change         │  Impact on 100-char Message    │
├─────────────────────────────────────────────────────────────┤
│  typing_rate: 0.3 → 0.25  │  33s → 28s   (-15%)           │
│  typing_rate: 0.3 → 0.35  │  33s → 38s   (+15%)           │
│  thinking: (2.5,0.25) →   │  33s → 33.1s (minimal)        │
│            (3.0,0.30)     │                                │
│  context: 0.03 → 0.05     │  33s → 34s   (+3%)            │
│  base: 1.0 → 0.5          │  33s → 32.5s (-1.5%)          │
│  chunking: 30% → 50%      │  UX change (more incremental) │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Debug Console Output

```
🤖 Processing message for Player 3 in room ABC123

📊 Delay calculation for Player 3:
   Message length: 85 chars, Previous: 42 chars
   Base: 1.00s, Typing: 0.297s/char × 85 = 25.25s
   Context: 1.26s, Thinking: 0.58s
   Total delay: 28.09s

📝 Player 3 message split into 3 chunks: 
   ['yes', 'I agree with that.', 'That makes total sense!']

⏱️  Chunk delays: ['1.35s', '7.82s', '18.92s']

💭 Player 3 chunk 1/3: thinking=0.41s, typing=0.95s
⏸️  Inter-chunk pause: 0.38s

💭 Player 3 chunk 2/3: thinking=2.35s, typing=5.48s
⏸️  Inter-chunk pause: 0.44s

💭 Player 3 chunk 3/3: thinking=5.68s, typing=13.25s

⏱️  Post-message cooldown: 1.13s

✅ Player 3 completed message in room ABC123
```

---

## 🚦 Phase Transition Safety

```
┌────────────────────────────────────────────────────┐
│              DEFENSE LAYERS                        │
├────────────────────────────────────────────────────┤
│                                                    │
│  Layer 1: Pre-Generation Check                    │
│     ├─ Verify phase = DISCUSSION                  │
│     └─ Reject if phase changed                    │
│                                                    │
│  Layer 2: Post-Generation Check                   │
│     ├─ Verify phase = DISCUSSION                  │
│     └─ Discard message if phase changed           │
│                                                    │
│  Layer 3: Per-Chunk Check                         │
│     ├─ Before each chunk                          │
│     ├─ After thinking delay                       │
│     ├─ After typing delay                         │
│     └─ Stop typing indicator if phase changed     │
│                                                    │
│  Layer 4: Pre-Trigger Check                       │
│     ├─ Before triggering next agents              │
│     └─ Skip if phase != DISCUSSION                │
│                                                    │
└────────────────────────────────────────────────────┘
```

These layers prevent messages from appearing in the wrong phase (e.g., voting phase receiving discussion messages).

---

**Legend:**
- N(μ, σ) = Normal Distribution (mean μ, std dev σ)
- Γ(shape, scale) = Gamma Distribution
- n_char = Current message length
- n_char_prev = Previous message length

**Files**: See `DELAY_SYSTEM.md` for full documentation

