# AI Delay System - Quick Reference

## Formula
```
Total = 1 + N(0.255, 0.0255)×n_char + N(0.03, 0.003)×n_char_prev + Γ(2.5, 0.25)
```
**Note**: Typing speed enhanced by 15% (0.3 → 0.255s per char = ~3.92 chars/sec)

## Quick Tuning

### Make responses faster
```python
# In process_single_ai_message() around line 997
typing_rate_per_char = max(0.1, np.random.normal(0.22, 0.022))  # 15% faster than current
```

### Make responses slower
```python
typing_rate_per_char = max(0.1, np.random.normal(0.30, 0.03))  # Back to original baseline
```

### More personality variation
```python
typing_rate_per_char = max(0.1, np.random.normal(0.255, 0.04))  # Increased variance
```

### Adjust thinking time
```python
# Faster thinking
thinking_time = np.random.gamma(2.0, 0.2)  # Was (2.5, 0.25)

# Slower thinking
thinking_time = np.random.gamma(3.0, 0.3)  # Was (2.5, 0.25)
```

### Change chunking probability
```python
# In process_single_ai_message() around line 1016
should_chunk = random.random() < 0.5  # Was 0.3 (now 50% instead of 30%)
```

### Adjust context sensitivity
```python
# More context-aware (previous message impacts more)
context_rate_per_char = max(0.0, np.random.normal(0.05, 0.005))  # Was (0.03, 0.003)

# Less context-aware
context_rate_per_char = max(0.0, np.random.normal(0.02, 0.002))  # Was (0.03, 0.003)
```

## Testing Commands

```bash
# Activate environment
conda activate group-chat

# Install numpy if needed
pip install numpy>=1.24.0

# Run backend
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Expected Delays (100-char message, 50-char previous)

| Configuration | Base | Typing | Context | Thinking | **Total** |
|---------------|------|--------|---------|----------|-----------|
| **Default** (15% enhanced) | 1.0s | 25.5s | 1.5s | 0.6s | **~28.6s** |
| Extra Fast | 1.0s | 22.0s | 1.5s | 0.4s | **~24.9s** |
| Original Baseline | 1.0s | 30.0s | 1.5s | 0.6s | **~33.1s** |
| High Variance | 1.0s | 25.5±4s | 1.5s | 0.6±0.5s | **~28.6±4s** |

## Console Output Example

```
📊 Delay calculation for Player 3:
   Message length: 85 chars, Previous: 42 chars
   Base: 1.00s, Typing: 0.253s/char × 85 = 21.51s
   Context: 1.26s, Thinking: 0.58s
   Total delay: 24.35s
📝 Player 3 message split into 3 chunks: ['yes', 'I think so.', 'That makes sense!']
⏱️  Chunk delays: ['2.72s', '10.21s', '15.16s']
💭 Player 3 chunk 1/3: thinking=0.82s, typing=1.90s
💭 Player 3 chunk 2/3: thinking=3.06s, typing=7.15s
⏸️  Inter-chunk pause: 0.42s
💭 Player 3 chunk 3/3: thinking=4.55s, typing=10.61s
⏱️  Post-message cooldown: 1.13s
```

## Key Files

- **Implementation**: `backend/main.py` (function `process_single_ai_message`)
- **Full docs**: `backend/DELAY_SYSTEM.md`
- **Requirements**: `backend/requirements.txt` (added numpy>=1.24.0)

## Troubleshooting

**Import error: "No module named 'numpy'"**
```bash
pip install numpy
```

**Messages still too slow/fast after tuning**
- Check if multiple instances are running
- Clear browser cache
- Restart backend server

**Chunking not working**
- Ensure `chunk_message()` function is accessible (line ~810)
- Check chunking probability setting (line ~1016)

## Distribution Cheat Sheet

**Normal Distribution N(μ, σ)**
- μ = mean (center)
- σ = standard deviation (spread)
- ~68% of values within μ±σ
- ~95% within μ±2σ

**Gamma Distribution Γ(shape, scale)**
- Mean = shape × scale
- Mode = (shape-1) × scale (for shape>1)
- Right-skewed (tail on right)
- Always positive

## Quick Math

**100-char message calculation** (with 50-char previous):
```
1 + 0.255×100 + 0.03×50 + 0.625
= 1 + 25.5 + 1.5 + 0.625
= 28.625 seconds (typical)
```

**Per-character rates**:
- **0.255s/char = 3.92 chars/sec = 235 chars/min ≈ 47 WPM** (current: 15% enhanced)
- 0.22s/char = 4.55 chars/sec = 273 chars/min ≈ 55 WPM (extra fast)
- 0.30s/char = 3.33 chars/sec = 200 chars/min ≈ 40 WPM (original baseline)

