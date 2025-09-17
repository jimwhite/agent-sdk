"""Example demonstrating color theme customization in the visualizer.

This example shows how to use different color themes to improve readability
on different terminal backgrounds (light vs dark).
"""


def demo_color_themes():
    """Demonstrate different color themes for the visualizer."""
    print("=== Color Theme Examples ===\n")

    # Example 1: Default theme (optimized for both light and dark backgrounds)
    print("1. Default Theme (balanced for light and dark backgrounds):")
    print("   - Uses bright_cyan instead of yellow for better readability")
    print("   - Uses bright_magenta instead of bright_yellow for pause events")
    print("   - Maintains good contrast on most terminal themes\n")

    # Example 2: Light theme
    print("2. Light Theme (optimized for light backgrounds):")
    print("   - Uses darker colors that stand out on white/light backgrounds")
    print("   - Example: observation='blue', message_user='dark_orange'")
    print("   Usage:")
    print("   conversation = Conversation(")
    print("       agent=agent,")
    print("       visualize=True,")
    print("       color_theme=LIGHT_THEME")
    print("   )\n")

    # Example 3: Dark theme
    print("3. Dark Theme (similar to original, optimized for dark backgrounds):")
    print("   - Uses bright colors that stand out on dark backgrounds")
    print("   - Example: observation='yellow', pause='bright_yellow'")
    print("   Usage:")
    print("   conversation = Conversation(")
    print("       agent=agent,")
    print("       visualize=True,")
    print("       color_theme=DARK_THEME")
    print("   )\n")

    # Example 4: High contrast theme
    print("4. High Contrast Theme (for accessibility):")
    print("   - Uses very bright colors for maximum contrast")
    print("   - Example: observation='bright_white', error='bright_red'")
    print("   Usage:")
    print("   conversation = Conversation(")
    print("       agent=agent,")
    print("       visualize=True,")
    print("       color_theme=HIGH_CONTRAST_THEME")
    print("   )\n")

    # Example 5: Custom theme
    print("5. Custom Theme (define your own colors):")
    print("   custom_theme = {")
    print("       'observation': 'orange',")
    print("       'pause': 'cyan',")
    print("       'error': 'bright_red',")
    print("       'action': 'green',")
    print("   }")
    print("   conversation = Conversation(")
    print("       agent=agent,")
    print("       visualize=True,")
    print("       color_theme=custom_theme")
    print("   )\n")

    print("Available color roles for customization:")
    print("- observation: Tool output and observation events")
    print("- message_user: User messages")
    print("- pause: Pause events")
    print("- system: System prompts and condensation events")
    print("- thought: Thought text in highlighting")
    print("- error: Error events and unknown event types")
    print("- action: Agent actions")
    print("- message_assistant: Assistant messages")
    print("- metrics_reasoning: Reasoning tokens in metrics display")

    print("\nNote: The default theme now uses better colors that work well")
    print("on both light and dark backgrounds, solving the yellow visibility issue!")


if __name__ == "__main__":
    demo_color_themes()
