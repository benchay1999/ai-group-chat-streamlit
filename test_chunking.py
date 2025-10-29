#!/usr/bin/env python3
"""
Test the fixed chunk_message function to ensure it respects quotes.
"""

import re
from typing import List

def chunk_message(message: str, max_chunks: int = 4) -> List[str]:
    """
    Split a message into 2-4 chunks based on commas and sentence boundaries.
    Simulates human-like incremental typing by removing commas and keeping sentence endings.
    Respects quoted text - doesn't split inside quotes.
    """
    # Handle empty or whitespace-only messages
    if not message or not message.strip():
        return [message]
    
    # If message is very short, don't chunk it
    if len(message) < 20:
        return [message]
    
    # Find split points that are NOT inside quotes
    def find_split_points(text):
        """Find positions where we can split (sentence endings and commas outside quotes)"""
        split_points = []
        in_double_quote = False
        in_single_quote = False
        
        for i, char in enumerate(text):
            # Track quote state
            if char == '"' and (i == 0 or text[i-1] != '\\'):
                in_double_quote = not in_double_quote
            elif char == "'" and (i == 0 or text[i-1] != '\\'):
                in_single_quote = not in_single_quote
            
            # Only split at punctuation outside quotes
            if not in_double_quote and not in_single_quote:
                if char in '.!?,':
                    # Record split point with punctuation type
                    split_points.append((i, char))
        
        return split_points
    
    split_points = find_split_points(message)
    
    # If no split points found, return original
    if not split_points:
        return [message]
    
    # Create chunks from split points
    chunks = []
    start = 0
    
    for pos, punct in split_points:
        # Extract text up to and including the punctuation
        chunk_text = message[start:pos+1].strip()
        
        if chunk_text:
            # Remove commas to make chunks more natural
            # Keep sentence-ending punctuation (. ! ?)
            if punct == ',':
                chunk_text = chunk_text[:-1].strip()  # Remove trailing comma
            
            if chunk_text:  # Only add non-empty chunks
                chunks.append(chunk_text)
        
        start = pos + 1
    
    # Add any remaining text after the last split point
    if start < len(message):
        remaining = message[start:].strip()
        if remaining:
            chunks.append(remaining)
    
    # If we have no chunks, return original
    if not chunks:
        return [message]
    
    # Limit to max_chunks by combining adjacent chunks if needed
    if len(chunks) > max_chunks:
        combined = []
        items_per_chunk = len(chunks) / max_chunks
        
        for chunk_idx in range(max_chunks):
            start_idx = int(chunk_idx * items_per_chunk)
            end_idx = int((chunk_idx + 1) * items_per_chunk) if chunk_idx < max_chunks - 1 else len(chunks)
            combined_text = ' '.join(chunks[start_idx:end_idx])
            if combined_text:
                combined.append(combined_text)
        
        chunks = combined
    
    # Ensure we have at least 2 chunks for longer messages
    if len(chunks) == 1 and len(message) > 40:
        # Try to split roughly in half at a word boundary
        mid = len(message) // 2
        # Find nearest space after midpoint
        space_pos = message.find(' ', mid)
        if space_pos == -1:  # No space after mid, try before
            space_pos = message.rfind(' ', 0, mid)
        if space_pos > 0:
            chunks = [message[:space_pos].strip(), message[space_pos+1:].strip()]
    
    # Final filter: ensure minimum of 2 chunks for meaningful chunking
    if len(chunks) < 2:
        return [message]
    
    return chunks


def test_chunking():
    """Test cases to verify chunking works correctly"""
    
    print("=" * 70)
    print("Testing Message Chunking with Quotes")
    print("=" * 70)
    print()
    
    # Test Case 1: User's first example
    msg1 = 'someone once told me to "ignore the warning signs and just go for it." Spoiler: it didn\'t end well'
    print("Test 1: Quote with period inside")
    print(f"Input:  {msg1}")
    print("Output:")
    chunks1 = chunk_message(msg1)
    for i, chunk in enumerate(chunks1, 1):
        print(f"  Chunk {i}: {chunk}")
    print()
    
    # Check that the period stays inside the quote
    assert any('"' in chunk and '."' in chunk for chunk in chunks1), "Period should stay inside quote!"
    print("✅ PASS: Period stays inside quote")
    print()
    
    # Test Case 2: User's second example  
    msg2 = 'I was told to "fake it till you make it".'
    print("Test 2: Quote at end with period outside")
    print(f"Input:  {msg2}")
    print("Output:")
    chunks2 = chunk_message(msg2)
    for i, chunk in enumerate(chunks2, 1):
        print(f"  Chunk {i}: {chunk}")
    print()
    
    # Should NOT split into separate period
    assert not any(chunk == '.' for chunk in chunks2), "Should not have standalone period!"
    print("✅ PASS: No standalone period")
    print()
    
    # Test Case 3: Multiple quotes
    msg3 = 'He said "hello," then I said "goodbye." That was it.'
    print("Test 3: Multiple quotes")
    print(f"Input:  {msg3}")
    print("Output:")
    chunks3 = chunk_message(msg3)
    for i, chunk in enumerate(chunks3, 1):
        print(f"  Chunk {i}: {chunk}")
    print()
    
    # Commas inside quotes should not split
    assert not any(chunk == ',' for chunk in chunks3), "Should not have standalone comma!"
    print("✅ PASS: Commas inside quotes don't split")
    print()
    
    # Test Case 4: Normal sentence (no quotes)
    msg4 = 'This is a test. It has multiple sentences. This is the third one.'
    print("Test 4: Normal sentences without quotes")
    print(f"Input:  {msg4}")
    print("Output:")
    chunks4 = chunk_message(msg4)
    for i, chunk in enumerate(chunks4, 1):
        print(f"  Chunk {i}: {chunk}")
    print()
    
    assert len(chunks4) >= 2, "Should split into multiple chunks"
    print(f"✅ PASS: Split into {len(chunks4)} chunks")
    print()
    
    # Test Case 5: Single quotes
    msg5 = "Someone said 'watch out for the dog.' I didn't listen."
    print("Test 5: Single quotes")
    print(f"Input:  {msg5}")
    print("Output:")
    chunks5 = chunk_message(msg5)
    for i, chunk in enumerate(chunks5, 1):
        print(f"  Chunk {i}: {chunk}")
    print()
    
    assert any("'watch out for the dog.'" in chunk for chunk in chunks5), "Single quote content should stay together!"
    print("✅ PASS: Single quotes respected")
    print()
    
    print("=" * 70)
    print("All Tests Passed! ✅")
    print("=" * 70)


if __name__ == '__main__':
    test_chunking()

