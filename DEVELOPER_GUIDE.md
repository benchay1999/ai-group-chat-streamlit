# Developer Guide: LangGraph Multi-Agent System

## Quick Start for Developers

This guide helps you understand and work with the LangGraph-based multi-agent architecture.

## Core Concepts

### 1. State-Driven Architecture

Everything in the game flows through a central `GameState` object:

```python
from langgraph_state import GameState

# State contains ALL game information
state: GameState = {
    "room_code": "abc123",
    "round": 1,
    "phase": Phase.DISCUSSION,
    "players": [...],
    "chat_history": [...],
    "votes": {},
    # ... and more
}
```

**Key Principle**: Nodes don't modify state directly. They return partial state updates that get merged.

### 2. Graph Nodes

Each node is a function that takes state and returns a state update:

```python
def my_node(self, state: GameState) -> GameState:
    """
    Process state and return updates.
    """
    # Read from state
    current_round = state["round"]
    
    # Compute something
    new_value = current_round + 1
    
    # Return ONLY the changes
    return {
        "round": new_value,
        "broadcast_queue": [{"type": "update", "value": new_value}]
    }
```

**Important**: 
- Don't mutate state directly
- Return only fields that changed
- Use `operator.add` for list fields (chat_history, broadcast_queue)

### 3. Conditional Edges

Control flow based on state:

```python
def should_continue_discussion(self, state: GameState) -> Literal["continue", "voting"]:
    """Decide next path in graph."""
    if state["pending_ai_messages"]:
        return "continue"  # Keep chatting
    return "voting"  # Move to voting
```

## Working with AI Agents

### Agent Node Structure

```python
def ai_chat_agent_node(self, state: GameState) -> GameState:
    # 1. Get the AI to process
    ai_id = state["pending_ai_messages"][0]
    
    # 2. Generate AI response
    message = self._generate_ai_message(state, ai_id)
    
    # 3. Create state updates
    chat_msg: ChatMessage = {
        "sender": ai_id,
        "message": message,
        "timestamp": time.time()
    }
    
    # 4. Return updates
    return {
        "chat_history": [chat_msg],  # Appends due to operator.add
        "pending_ai_messages": state["pending_ai_messages"][1:],
        "broadcast_queue": [{"type": "message", "sender": ai_id, "message": message}]
    }
```

### LangChain Integration

Using LangChain for AI generation:

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Initialize model
self.llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.8
)

# Generate response
messages = [
    SystemMessage(content="You are a helpful agent..."),
    HumanMessage(content="User prompt here")
]
response = self.llm.invoke(messages)
message_text = response.content
```

## State Management Patterns

### Appending to Lists

Use `Annotated[List[T], operator.add]` for lists that accumulate:

```python
from typing import Annotated
import operator

class GameState(TypedDict):
    chat_history: Annotated[List[ChatMessage], operator.add]
    broadcast_queue: Annotated[List[Dict], operator.add]
```

Then return single items that get appended:

```python
return {
    "chat_history": [new_message],  # Appends, doesn't replace
    "broadcast_queue": [broadcast1, broadcast2]  # Appends both
}
```

### Replacing Values

Regular fields get replaced:

```python
return {
    "phase": Phase.VOTING,  # Replaces old phase
    "round": state["round"] + 1,  # Replaces with new value
    "votes": {}  # Replaces with empty dict
}
```

### Updating Dictionaries

```python
# Get current dict
new_votes = state["votes"].copy()

# Modify
new_votes[voter_id] = voted_for

# Return
return {"votes": new_votes}
```

## Adding New Features

### Example: Add a "Hint" System

**1. Update State Schema** (`langgraph_state.py`):

```python
class GameState(TypedDict):
    # ... existing fields ...
    hints_given: int
    hint_text: Optional[str]
```

**2. Create Hint Node** (`langgraph_game.py`):

```python
def hint_node(self, state: GameState) -> GameState:
    """Generate a hint for the human player."""
    # Analyze game state
    hint = self._generate_hint(state)
    
    return {
        "hints_given": state["hints_given"] + 1,
        "hint_text": hint,
        "broadcast_queue": [{"type": "hint", "text": hint}]
    }
```

**3. Add to Graph**:

```python
def _build_graph(self):
    workflow = StateGraph(GameState)
    
    # Add node
    workflow.add_node("hint", self.hint_node)
    
    # Add edge
    workflow.add_edge("discussion_phase", "hint")
    workflow.add_conditional_edges(
        "hint",
        lambda s: "continue" if s["hints_given"] < 3 else "skip",
        {"continue": "ai_chat_agent", "skip": "ai_chat_agent"}
    )
```

**4. Update Initial State** (`langgraph_state.py`):

```python
def create_initial_state(...):
    return GameState(
        # ... existing fields ...
        hints_given=0,
        hint_text=None
    )
```

## WebSocket Integration

### Broadcasting from Graph

Nodes add messages to `broadcast_queue`:

```python
def my_node(self, state: GameState) -> GameState:
    return {
        "broadcast_queue": [
            {"type": "custom_event", "data": "something"},
            {"type": "another_event", "value": 123}
        ]
    }
```

### Processing in main.py

```python
async def process_broadcast_queue(room_code: str, state: GameState):
    """Send all queued messages to clients."""
    for message in state.get("broadcast_queue", []):
        await broadcast_to_room(room_code, message)
```

### Frontend Compatibility

Ensure all messages match frontend expectations:

```typescript
// Frontend expects these message types
type MessageType = 
  | "player_list"
  | "topic"
  | "phase"
  | "message"
  | "typing"
  | "voted"
  | "elimination"
  | "game_over"
  | "new_round";
```

## Configuration Best Practices

### Environment Variables

```python
# config.py
import os

# Provide defaults
NUM_AI_PLAYERS = int(os.getenv("NUM_AI_PLAYERS", "4"))

# Validate
if not 2 <= NUM_AI_PLAYERS <= 10:
    raise ValueError("NUM_AI_PLAYERS must be between 2 and 10")
```

### Dynamic Configuration

```python
# Allow runtime configuration
@app.post("/config")
async def update_config(num_players: int):
    global NUM_AI_PLAYERS
    NUM_AI_PLAYERS = num_players
    return {"status": "updated"}
```

## Testing Strategies

### Unit Test a Node

```python
import pytest
from langgraph_game import GameGraph
from langgraph_state import create_initial_state

def test_discussion_node():
    graph = GameGraph()
    state = create_initial_state("test-room", 4)
    
    # Run node
    result = graph.discussion_phase_node(state)
    
    # Assert
    assert result["phase"] == Phase.DISCUSSION
    assert len(result["pending_ai_messages"]) > 0
```

### Integration Test Graph

```python
def test_full_round():
    graph = GameGraph()
    state = create_initial_state("test-room", 4)
    
    # Run through one round
    final_state = graph.graph.invoke(state)
    
    # Verify round completed
    assert final_state["round"] >= 1
    assert len(final_state["chat_history"]) > 0
```

### Mock LLM for Testing

```python
from unittest.mock import Mock

def test_ai_message_with_mock():
    graph = GameGraph()
    
    # Mock LLM
    graph.llm = Mock()
    graph.llm.invoke.return_value.content = "Test message"
    
    # Test
    message = graph._generate_ai_message(state, "Player 1")
    assert message == "Test message"
```

## Debugging Tips

### 1. Print State at Each Node

```python
def my_node(self, state: GameState) -> GameState:
    print(f"Node input: {state['phase']}, {state['round']}")
    result = {"phase": Phase.VOTING}
    print(f"Node output: {result}")
    return result
```

### 2. Use LangSmith

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY="your-key"
```

Then view traces at https://smith.langchain.com

### 3. Validate State Schema

```python
from langgraph_state import GameState

def validate_state(state: dict) -> bool:
    required_keys = GameState.__annotations__.keys()
    return all(key in state for key in required_keys)
```

### 4. Log Graph Execution

```python
# In main.py
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug(f"Graph executing with state: {state}")
```

## Performance Optimization

### 1. Async AI Generation

```python
import asyncio

async def generate_multiple_ai_messages(state, ai_ids):
    tasks = [
        asyncio.create_task(self._generate_ai_message_async(state, ai_id))
        for ai_id in ai_ids
    ]
    return await asyncio.gather(*tasks)
```

### 2. LangChain Caching

```python
from langchain.cache import InMemoryCache
from langchain.globals import set_llm_cache

set_llm_cache(InMemoryCache())
```

### 3. Batch Processing

```python
def process_batch(self, state: GameState) -> GameState:
    """Process multiple AIs in one node execution."""
    messages = []
    for ai_id in state["pending_ai_messages"]:
        msg = self._generate_ai_message(state, ai_id)
        messages.append({"sender": ai_id, "message": msg})
    
    return {
        "chat_history": messages,
        "pending_ai_messages": []
    }
```

## Common Patterns

### Pattern: Conditional Execution

```python
def conditional_node(self, state: GameState) -> GameState:
    if state["round"] > 3:
        # Special behavior after round 3
        return {"difficulty": "hard"}
    return {}
```

### Pattern: State Validation

```python
def safe_node(self, state: GameState) -> GameState:
    # Validate input
    if not state.get("players"):
        raise ValueError("No players in state")
    
    # Process
    result = self._do_something(state)
    
    # Validate output
    if not result:
        return {}
    
    return result
```

### Pattern: Error Recovery

```python
def robust_node(self, state: GameState) -> GameState:
    try:
        result = self._risky_operation(state)
        return {"success": True, "data": result}
    except Exception as e:
        print(f"Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "broadcast_queue": [{"type": "error", "message": "Something went wrong"}]
        }
```

## Resources

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **LangChain Docs**: https://python.langchain.com/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **WebSockets**: https://websockets.readthedocs.io/

## Getting Help

1. Check logs for error messages
2. Inspect state at each node with print statements
3. Use LangSmith for LLM call tracing
4. Review this guide's patterns
5. Consult LangGraph documentation

## Next Steps

- [ ] Read through `langgraph_state.py` to understand state structure
- [ ] Explore `langgraph_game.py` to see node implementations
- [ ] Try modifying `config.py` to change game parameters
- [ ] Add a custom node for a new feature
- [ ] Write tests for your additions
- [ ] Profile performance and optimize

Happy coding! 🚀

