# Proxy SDK Simplification

## Overview

The proxy SDK has been dramatically simplified from a manual per-class implementation to an **automatic generic translator** that works with any class.

## Before vs After

### Before: Manual Proxy Classes (❌ Complex)

```python
# Had to manually implement proxy classes for each SDK class
class AgentProxy:
    def __init__(self, proxy_client, llm, tools=None):
        self._proxy = proxy_client
        self.llm = llm
        self.tools = tools or []

class LLMProxy:
    def __init__(self, proxy_client, **kwargs):
        self._proxy = proxy_client
        self._data = kwargs
    
    def model_dump(self):
        return self._data
    
    def __getattr__(self, name):
        # Manual attribute delegation...

class ConversationProxy:
    def __init__(self, proxy_client):
        # Manual implementation of all conversation methods...
    
    def send_message(self, message, agent=None, tools=None):
        # Manual HTTP request handling...
    
    def run_conversation(self, message, agent, tools=None, max_iterations=10):
        # Manual HTTP request handling...
```

**Problems:**
- Had to manually implement each proxy class
- Lots of boilerplate code
- Hard to maintain and extend
- ~200 lines of repetitive proxy code

### After: Generic Automatic Translator (✅ Simple)

```python
class GenericProxy:
    """Generic proxy that can handle any BaseModel automatically."""
    
    def __init__(self, proxy_client, original_class, **kwargs):
        self._proxy = proxy_client
        self._original_class = original_class
        self._data = kwargs
        self._class_name = original_class.__name__

    def __getattr__(self, name):
        """Automatically proxy method calls and attribute access."""
        # Check stored data first
        if name in self._data:
            return self._data[name]
        
        # Check if original class has this attribute/method
        if hasattr(self._original_class, name):
            original_attr = getattr(self._original_class, name)
            
            # If it's a method, create automatic proxy method
            if callable(original_attr):
                def proxy_method(*args, **kwargs):
                    # Automatic serialization and remote call
                    data = {
                        'class_name': self._class_name,
                        'method_name': name,
                        'instance_data': self._data,
                        'args': self._serialize_args(args),
                        'kwargs': self._serialize_kwargs(kwargs)
                    }
                    return self._proxy._make_request("POST", "/proxy/call", data)
                return proxy_method
            else:
                return original_attr
```

**Benefits:**
- **ONE** generic proxy handles ALL classes automatically
- No manual implementation needed for new classes
- ~50 lines of code instead of ~200
- Conversation remains special case (uses existing API)

## Usage Comparison

### Before and After: Identical Interface! 

```python
# Usage is EXACTLY the same!
from openhands.sdk.client import Proxy
from openhands.sdk import Agent, LLM, Conversation

proxy = Proxy(url="http://localhost:9000", api_key="abc")

Agent = proxy.import_(Agent)
LLM = proxy.import_(LLM) 
Conversation = proxy.import_(Conversation)

# Use exactly like original SDK:
llm = LLM(model="claude-sonnet-4", api_key="key")
agent = Agent(llm=llm, tools=[])
convo = Conversation()  # Created remotely!
```

## Architecture

### Two-Tier Approach

1. **Generic Proxy**: Handles all BaseModel classes automatically
   - Agent, LLM, and any other BaseModel
   - Automatic method proxying via `__getattr__`
   - Automatic serialization/deserialization

2. **Special Case**: Conversation uses existing server API
   - Already has dedicated endpoints (`/conversation/send_message`, etc.)
   - Maintains existing server implementation

## Key Improvements

1. **Maintainability**: Adding support for new SDK classes requires ZERO code changes
2. **Simplicity**: ~75% reduction in proxy implementation code
3. **Flexibility**: Can proxy ANY class, not just predefined ones
4. **Consistency**: Same interface pattern for all classes

## Example: Adding New Class Support

### Before (Manual)
```python
# Had to manually implement new proxy class
class NewClassProxy:
    def __init__(self, proxy_client, **kwargs):
        # Manual implementation...
    
    def some_method(self, arg):
        # Manual HTTP request...
```

### After (Automatic)
```python
# NO CODE CHANGES NEEDED!
ProxyNewClass = proxy.import_(NewClass)
instance = ProxyNewClass(param="value")
result = instance.some_method("arg")  # Automatically proxied!
```

## Testing

- All 13 tests pass
- Maintains identical interface compatibility
- Type checking passes
- Pre-commit hooks pass

The simplified proxy SDK provides the same functionality with dramatically less code and much better maintainability!