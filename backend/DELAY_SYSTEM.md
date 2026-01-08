# AI Agent Delay System - Hybrid Implementation

## Overview

The AI agent delay system has been upgraded to a **hybrid approach** that combines:
1. **Statistical rigor** - Mathematical formula based on Normal and Gamma distributions
2. **UX realism** - Chunking behavior that mimics human typing patterns
3. **Context awareness** - Considers previous message length (cognitive load)

This document explains the implementation, the mathematics behind it, and how to tune parameters.

---

## Mathematical Model

The total delay for an AI agent's response is calculated using:

```
Total_delay = 1 + N(0.3, 0.05)×n_char + N(0.03, 0.005)×n_char_prev + Γ(2.5, 0.25)
```

### Components

| Component | Distribution | Purpose | Typical Value |
|-----------|--------------|---------|---------------|
| **Base delay** | Fixed | Minimum reaction time | 1.0s |
| **Typing rate** | N(0.3, 0.05) | Per-character typing time | 0.25-0.35s/char |
| **Context factor** | N(0.03, 0.005) | Cognitive load from previous message | 0.025-0.035s/char_prev |
| **Thinking time** | Γ(2.5, 0.25) | Cognitive processing before typing | 0.3-1.2s (right-skewed) |

### Why These Distributions?

**Normal Distribution N(μ, σ):**
- Models natural variation in human typing speed
- μ = 0.3 → Average typing speed of ~3.33 chars/sec (realistic for thoughtful conversation)
- σ = 0.05 → ±17% variance (higher variance for more realistic human variation)
- **Clamped to minimum 0.15** to prevent negative/zero delays

**Gamma Distribution Γ(shape, scale):**
- Models thinking/reaction time (naturally right-skewed)
- shape=2.5, scale=0.25 → mean=0.625s, mode≈0.375s
- **Right-skewed**: Most responses are quick (~0.4s), some require longer thought (1-2s)
- **Always positive**: No risk of negative thinking time

### Example Calculation

**100-character message** (previous message was 50 chars):

```python
base = 1.0s
typing = N(0.3, 0.05) × 100 = 30.0s ± 5.0s
context = N(0.03, 0.005) × 50 = 1.5s ± 0.25s  
thinking = Γ(2.5, 0.25) ≈ 0.625s (mean)

Total ≈ 33.1s ± 5.3s
```

---

## Chunking System

### Purpose
Humans don't type entire messages before hitting send. They send partial thoughts in "bursts," creating natural conversational flow. Modern implementation uses LLM to generate realistic chunks with human-like imperfections.

### Implementation

**LLM-Generated Chunking**: The AI model generates pre-chunked messages with personality-based imperfections

**Chunking Strategy**:
- LLM directly outputs 1-4 message chunks simulating "thinking aloud" behavior
- No rule-based splitting - chunks are contextually and semantically natural
- Chunks vary by personality (e.g., "enthusiastic" agents use more bursts)

**Human-Like Imperfections** (Personality-Based):
1. **Typos** (10-40% probability based on personality):
   - Believable mistakes: "teh" instead of "the", "i" instead of "o"
   - Missing letters, swapped characters
   
2. **Self-Corrections**:
   - When typo occurs, correction message sent 2-8 seconds later
   - Format: "*meant" or "*I mean"
   - Other messages may appear between typo and correction (realistic)

3. **Netspeak/Slang**:
   - Uses detected group slang dynamically (learns from conversation)
   - Common patterns: lol, lmao, idk, ngl, tbh, etc.
   - Probability varies by personality (10-60%)

4. **Informal Grammar**:
   - Sentence fragments, run-ons, lowercase
   - No punctuation in casual messages

**Personality Imperfection Levels**:
- **High correctness** (analytical, observant): 10% typo, 15% netspeak
- **Medium correctness** (sarcastic, philosophical): 25% typo, 30% netspeak  
- **Low correctness** (cheerful, enthusiastic): 40% typo, 55% netspeak

**Delay Distribution**:
When a message is chunked, the total statistical delay is distributed proportionally:

```python
chunk_delay = total_delay × (chunk_chars / total_chars)
```

Each chunk delay is further split:
- **30% thinking** (before typing begins)
- **70% typing** (simulates character-by-character input)

**Inter-chunk pause**: 0.3-0.5s between chunks (simulates pressing Enter)

### Example

**LLM Output** (enthusiastic personality):
```json
{
  "chunks": ["hey", "did u see that lol", "that was crazy"],
  "has_typo": true,
  "correction": "*you"
}
```

**Sent Messages**:
1. "hey" (3 chars) - delay 0.8s
2. "did u see that lol" (18 chars) - delay 4.5s
3. "that was crazy" (14 chars) - delay 3.2s
4. [2-8s later] "*you" (correction)

**Total delay**: ~8.5s + correction delay

### Dynamic Slang Learning

The system tracks commonly used slang in the conversation:
- Scans last 15 messages for netspeak patterns
- Maintains top 20 most frequent terms (minimum 2 occurrences)
- Feeds detected slang back to LLM prompt for natural adoption
- Examples: If group uses "fr" often, AI agents start using it too

---

## Context Awareness

### Previous Message Impact

The formula includes `N(0.03, 0.003) × n_char_prev` to model **cognitive load**:

- **Longer previous messages** → More information to process → Longer thinking time
- **Scale**: ~0.03s per character in previous message (3% of main typing rate)
- **Example**: 100-char previous message adds ~3s to response time

### Conversation History

Currently tracks: **Last message only**

**Potential extensions**:
- Track last N messages (conversation context)
- Different weights for human vs AI messages
- Topic complexity scoring (from LLM embeddings)

---

## Implementation Details

### Location
**File**: `backend/main.py`  
**Function**: `process_single_ai_message(room_code: str, ai_id: str)`

### Key Code Sections

#### 1. Statistical Delay Calculation (lines 981-1013)
```python
import numpy as np

# Get context
chat_history = current_state.get('chat_history', [])
n_char_prev = len(chat_history[-1]['message']) if chat_history else 0
n_char = len(ai_message)

# Calculate components
base_delay = 1.0
typing_rate_per_char = max(0.1, np.random.normal(0.3, 0.03))
context_rate_per_char = max(0.0, np.random.normal(0.03, 0.003))
context_delay = context_rate_per_char * n_char_prev
thinking_time = np.random.gamma(2.5, 0.25)

# Total delay
total_statistical_delay = base_delay + (typing_rate_per_char * n_char) + context_delay + thinking_time
```

#### 2. Chunk Delay Distribution (lines 1034-1052)
```python
# Calculate per-chunk delays proportionally
chunk_delays = []
total_chunk_chars = sum(len(chunk) for chunk in chunks)

for chunk in chunks:
    chunk_proportion = len(chunk) / total_chunk_chars
    chunk_delay = total_statistical_delay * chunk_proportion
    chunk_delays.append(chunk_delay)
```

#### 3. Delay Application (lines 1068-1110)
```python
for chunk_idx, (chunk, chunk_delay) in enumerate(zip(chunks, chunk_delays)):
    # Split delay into thinking and typing
    thinking_portion = chunk_delay * 0.3
    typing_portion = chunk_delay * 0.7
    
    # Apply delays
    await asyncio.sleep(thinking_portion)  # Thinking
    await asyncio.sleep(typing_portion)     # Typing
    
    # Broadcast chunk
    await broadcast_to_room(room_code, {"type": "message", ...})
```

### Defense Layers

The implementation includes **4 defense layers** to handle phase transitions:
1. **Pre-processing check**: Verify phase before generating message
2. **Pre-broadcast check**: Verify phase after generation (LLM can take seconds)
3. **Per-chunk check**: Verify phase before each chunk
4. **Post-message check**: Verify phase before triggering next agent

This prevents late messages from appearing in the wrong phase.

---

## Tuning Parameters

### Typing Speed

**Current**: N(0.3, 0.05) → ~3.33 chars/sec with realistic variance

**Adjust for**:
- **Faster agents**: N(0.25, 0.05) → ~4 chars/sec
- **Slower agents**: N(0.35, 0.05) → ~2.86 chars/sec
- **More variance**: N(0.3, 0.08) → Even more personality variation
- **Less variance**: N(0.3, 0.03) → More consistent typing

### Thinking Time

**Current**: Γ(2.5, 0.25)

**Adjust for**:
- **Quicker thinkers**: Γ(2.0, 0.2) → mean=0.4s
- **Deeper thinkers**: Γ(3.0, 0.3) → mean=0.9s
- **More variance**: Γ(2.5, 0.35) → Wider distribution

### Context Sensitivity

**Current**: N(0.03, 0.003) per char

**Adjust for**:
- **More context-aware**: N(0.05, 0.005) → 5% of typing rate
- **Less context-aware**: N(0.02, 0.002) → 2% of typing rate

### Chunking Probability

**Current**: 30% (line 1016)

**Adjust for**:
- **More natural flow**: 50% chunking
- **Faster experience**: 10% chunking

---

## Performance Comparison

### Before (Fixed Speed System)

**100-char message**:
- Thinking: 1.0s (fixed)
- Typing: 100 / 4.83 × 1.0 ≈ 20.7s
- Cooldown: 1.25s
- **Total: ~22.95s**

**Issues**:
- ❌ No context awareness
- ❌ Fixed typing speed (no personality)
- ❌ Arbitrary cooldown
- ✅ Good chunking behavior

### After (Hybrid System)

**100-char message** (50-char previous):
- Base: 1.0s
- Typing: 30.0s ± 3.0s (with variance)
- Context: 1.5s ± 0.15s (cognitive load)
- Thinking: 0.625s ± 0.4s (right-skewed)
- **Total: ~33.1s ± 3.4s**

**Improvements**:
- ✅ Context awareness (previous message)
- ✅ Statistical variance (more human-like)
- ✅ Realistic thinking time distribution
- ✅ Maintained chunking behavior
- ✅ Proportional delay distribution

---

## Future Enhancements

### 1. Agent Personality Profiles
Store per-agent typing parameters:
```python
agent_profiles = {
    "Player 1": {"typing_rate": 0.25, "thinking_shape": 2.0},  # Fast thinker
    "Player 2": {"typing_rate": 0.35, "thinking_shape": 3.0},  # Slow, thoughtful
}
```

### 2. Conversation State Tracking
Track conversation momentum:
```python
# Fast-paced debate
if recent_message_rate > 3/min:
    base_delay *= 0.7  # Faster responses
```

### 3. Topic Complexity Scoring
Use LLM embeddings to estimate response difficulty:
```python
complexity_score = get_topic_complexity(message)
thinking_time *= (1 + complexity_score)  # Longer thinking for complex topics
```

### 4. Interruption Modeling
Allow agents to "interrupt" during long pauses:
```python
if time_since_last_message > 15s and np.random.random() < 0.3:
    trigger_interruption()
```

### 5. Fatigue Modeling
Slower responses as conversation progresses:
```python
message_count = len(chat_history)
fatigue_factor = 1 + (message_count * 0.02)  # +2% delay per message
total_delay *= fatigue_factor
```

---

## Testing & Validation

### Manual Testing
Run a game and observe console logs:
```
📊 Delay calculation for Player 1:
   Message length: 85 chars, Previous: 42 chars
   Base: 1.00s, Typing: 0.297s/char × 85 = 25.25s
   Context: 1.26s, Thinking: 0.58s
   Total delay: 28.09s
```

### Statistical Validation
Collect timing data and verify distributions:
```python
# Collect 100 samples
delays = [calculate_delay(100, 50) for _ in range(100)]

# Verify mean ≈ expected
expected = 1 + 0.3*100 + 0.03*50 + 2.5*0.25
assert abs(np.mean(delays) - expected) < 2.0  # Within 2s
```

### A/B Testing
Compare user experience:
- Group A: Old system (fixed speed)
- Group B: New system (hybrid)
- Metrics: Perceived realism, engagement, conversation flow

---

## Dependencies

**New requirement**: `numpy>=1.24.0`

Install via:
```bash
pip install numpy
```

Or via conda:
```bash
conda install numpy
```

---

## References

1. **Normal Distribution**: Used for typing speed variance
   - μ (mean) controls average speed
   - σ (std dev) controls variation

2. **Gamma Distribution**: Used for thinking time
   - Shape parameter controls skewness (right-skewed for cognitive processes)
   - Scale parameter controls spread
   - Mean = shape × scale
   - Mode = (shape - 1) × scale (for shape > 1)

3. **Human Typing Speed Research**:
   - Average: 40-60 WPM = 3.3-5 chars/sec
   - Thoughtful conversation: ~3 chars/sec (matches our μ=0.3s/char)
   - Think-then-type model: Supported by cognitive psychology research

---

## Troubleshooting

### Messages Too Slow
- Decrease `typing_rate_per_char` mean: N(0.25, 0.03)
- Decrease `thinking_time` scale: Γ(2.5, 0.2)
- Decrease `base_delay`: 0.5s

### Messages Too Fast
- Increase `typing_rate_per_char` mean: N(0.35, 0.03)
- Increase `thinking_time` scale: Γ(2.5, 0.3)
- Increase `base_delay`: 1.5s

### Not Enough Variation
- Increase `typing_rate_per_char` variance: N(0.3, 0.05)
- Increase `thinking_time` shape: Γ(3.0, 0.25) → wider distribution

### Too Much Chunking
- Decrease chunking probability (line 1016): `random.random() < 0.2`

### Import Errors
Ensure numpy is installed:
```bash
conda activate group-chat
pip install numpy>=1.24.0
```

---

## Conclusion

The hybrid delay system combines the best of both worlds:
- **Mathematical rigor** from statistical modeling
- **UX realism** from human-like chunking behavior
- **Context awareness** from previous message tracking

This creates a more natural, believable AI conversation experience while maintaining the flexibility to tune parameters for different use cases.

**Version**: 2.0 (Hybrid Implementation)  
**Last Updated**: November 2025  
**Author**: AI Group Chat Team

