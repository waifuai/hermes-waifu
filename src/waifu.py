#!/usr/bin/env python3
"""
Hermes-Waifu Integration Wrapper for Hermes Agent
==================================================
Non-destructive wrapper that monkey-patches cli.HermesCLI at runtime
to inject waifu lifecycle callbacks (from waifu_hook.py).

Usage:
    python waifu.py [args]
"""

import sys
import os
import threading

# --- 1. Environment Setup ---
# Add both this directory (for waifu_hook) and hermes-agent (for cli)
SRC_DIR = os.path.abspath(os.path.dirname(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Also need hermes-agent on path for importing cli
# Symlink location: ~/.hermes/hermes-agent/ -> points here via waifu.py symlink
HERMES_DIR = os.path.abspath(os.path.join(SRC_DIR, "..", "..", "..", ".hermes", "hermes-agent"))
if os.path.isdir(HERMES_DIR) and HERMES_DIR not in sys.path:
    sys.path.insert(0, HERMES_DIR)

# --- 2. Import Hermes CLI and Waifu Hooks ---
try:
    import cli
    import waifu_hook
except ImportError as e:
    print(f"[!] Error: Could not import required modules: {e}")
    sys.exit(1)

# --- 3. Define Patched Methods ---

original_init_agent = cli.HermesCLI._init_agent
original_chat = cli.HermesCLI.chat


def patched_init_agent(self, model_override=None, runtime_override=None, route_label=None):
    """Interpose agent initialization to inject lifecycle callbacks."""
    result = original_init_agent(
        self,
        model_override=model_override,
        runtime_override=runtime_override,
        route_label=route_label,
    )

    if self.agent is not None:
        # Wrap tool_start_callback
        orig_start = self.agent.tool_start_callback

        def wrapped_tool_start(tool_call_id, function_name, function_args):
            waifu_hook.on_tool_start(tool_call_id, function_name, function_args)
            if orig_start:
                orig_start(tool_call_id, function_name, function_args)

        # Wrap tool_complete_callback
        orig_complete = self.agent.tool_complete_callback

        def wrapped_tool_complete(tool_call_id, function_name, function_args, function_result):
            waifu_hook.on_tool_complete(tool_call_id, function_name, function_args, function_result)
            if orig_complete:
                orig_complete(tool_call_id, function_name, function_args, function_result)

        self.agent.tool_start_callback = wrapped_tool_start
        self.agent.tool_complete_callback = wrapped_tool_complete

        self.agent.thinking_callback = waifu_hook.on_user_input_received

    return result


def patched_chat(self, message, images=None):
    """Interpose the main chat loop to trigger high-level states."""
    # User sent message
    waifu_hook.on_user_input_received()

    # Transition to speaking/generating
    waifu_hook.on_agent_speaking()

    # Call original chat logic
    response = original_chat(self, message, images)

    # Detect emotion from response
    if response:
        emotion = waifu_hook.detect_emotion(response)
        waifu_hook.set_waifu_state(emotion)
    else:
        waifu_hook.on_agent_idle()

    # TTS hook (no-op in minimal mode, but kept for future use)
    if response:
        threading.Thread(
            target=waifu_hook.on_agent_reply, args=(response,), daemon=True
        ).start()

    return response


# --- 4. Apply Monkey Patches ---
cli.HermesCLI._init_agent = patched_init_agent
cli.HermesCLI.chat = patched_chat


# --- 5. Execution ---
if __name__ == "__main__":
    cli.main()
