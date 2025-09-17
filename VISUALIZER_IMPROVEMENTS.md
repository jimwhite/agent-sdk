# Visualizer Color Theme Improvements

## Problem Addressed

The original visualizer used yellow colors (`yellow` and `bright_yellow`) that were difficult to read on white/light terminal backgrounds, as shown in the user's screenshot.

## Solution

### 1. Improved Default Colors

Changed problematic colors in the default theme:
- `observation`: `yellow` → `bright_cyan` (better contrast on both light and dark backgrounds)
- `pause`: `bright_yellow` → `bright_magenta` (better contrast on both light and dark backgrounds)  
- `metrics_reasoning`: `yellow` → `bright_cyan` (consistent with observation color)

### 2. Color Theme System

Added a flexible color theming system that allows users to:
- Use predefined themes optimized for different terminal backgrounds
- Create custom color themes
- Override specific colors while keeping others as default

### 3. Predefined Themes

**LIGHT_THEME**: Optimized for light/white backgrounds
- Uses darker colors that stand out on light backgrounds
- Example: `observation='blue'`, `message_user='dark_orange'`

**DARK_THEME**: Similar to original, optimized for dark backgrounds  
- Preserves the original bright colors for dark terminal users
- Example: `observation='yellow'`, `pause='bright_yellow'`

**HIGH_CONTRAST_THEME**: For accessibility
- Uses very bright colors for maximum contrast
- Example: `observation='bright_white'`, `error='bright_red'`

## Usage Examples

### Default (Improved) Theme
```python
# Uses improved colors automatically
conversation = Conversation(agent=agent, visualize=True)
```

### Predefined Themes
```python
from openhands.sdk.conversation import LIGHT_THEME, DARK_THEME, HIGH_CONTRAST_THEME

# For light terminal backgrounds
conversation = Conversation(agent=agent, visualize=True, color_theme=LIGHT_THEME)

# For dark terminal backgrounds (original-style colors)
conversation = Conversation(agent=agent, visualize=True, color_theme=DARK_THEME)

# For high contrast/accessibility
conversation = Conversation(agent=agent, visualize=True, color_theme=HIGH_CONTRAST_THEME)
```

### Custom Themes
```python
custom_theme = {
    "observation": "orange",
    "pause": "cyan", 
    "error": "bright_red",
    "action": "green",
}
conversation = Conversation(agent=agent, visualize=True, color_theme=custom_theme)
```

## Available Color Roles

- `observation`: Tool output and observation events
- `message_user`: User messages  
- `pause`: Pause events
- `system`: System prompts and condensation events
- `thought`: Thought text in highlighting
- `error`: Error events and unknown event types
- `action`: Agent actions
- `message_assistant`: Assistant messages
- `metrics_reasoning`: Reasoning tokens in metrics display

## Backward Compatibility

- All existing code continues to work without changes
- Legacy color constants are preserved and now point to improved default colors
- The `create_default_visualizer()` function accepts the new `color_theme` parameter

## Files Modified

- `openhands/sdk/conversation/visualizer.py`: Main implementation
- `openhands/sdk/conversation/__init__.py`: Export new themes
- `tests/sdk/conversation/test_visualizer.py`: Added comprehensive tests
- `examples/17_color_themes.py`: Usage examples and documentation

## Testing

Added comprehensive tests covering:
- Custom color theme functionality
- Predefined theme usage
- Color application in panel creation
- Metrics color customization
- Backward compatibility

All existing tests continue to pass, ensuring no regressions.