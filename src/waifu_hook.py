"""
Hermes-Waifu Hook — Live2D integration layer for Hermes Agent.

Maps agent emotions to Live2D expressions/motions per model.
Each model has different expression capabilities, so mappings are per-model.

Emotion system (e1-e12):
  e1=Happy      e2=Amused       e3=Empathetic   e4=Curious
  e5=Confused    e6=Surprised    e7=Embarrassed  e8=Confident
  e9=Annoyed     e10=Overwhelmed e11=Determined  e12=Affectionate
"""

import re
import json
import os

# --- Per-Model Expression/Motion Mappings ---

# Models with expression files (can set specific faces)
# Haru expressions: f00-f07 (8 faces)
#   f00 = neutral (mouth slightly open)
#   f01 = surprised/excited (wide eyes, open mouth, brows up)
#   f02 = sad/angry (furrowed brows, frown)
#   f03 = worried/concerned (narrowed eyes, angled brows)
#   f04 = happy/amused (closed happy eyes, smile)
#   f05 = shocked/alarmed (wide eyes, brows up, frown)
#   f06 = concerned/sad (similar to f03, slightly open eyes)
#   f07 = pouty/displeased (slightly closed eyes, frown)

# Mao expressions: exp_01-exp_08 (8 faces)
#   exp_01 = neutral (all params zero — default face)
#   exp_02 = happy/closed smile (eyes closed + EyeSmile=1, like ^_^)
#   exp_03 = neutral alt (all zeros, slightly different base)
#   exp_04 = excited/happy (wide eyes + EyeSmile + sparkle effect)
#   exp_05 = sad/disappointed (brows down, mouth down)
#   exp_06 = embarrassed/shy (cheek blush + brows down)
#   exp_07 = surprised/worried (wide eyes, brows up, mouth down)
#   exp_08 = angry/annoyed (EyeForm + mouth angry line)

MODEL_EXPRESSION_MAP = {
    "Haru": {
        "e1":  "f04",  # Happy        -> closed happy smile
        "e2":  "f04",  # Amused       -> closed happy smile
        "e3":  "f03",  # Empathetic   -> worried/concerned
        "e4":  "f01",  # Curious      -> surprised/excited
        "e5":  "f06",  # Confused     -> concerned
        "e6":  "f05",  # Surprised    -> shocked
        "e7":  "f02",  # Embarrassed  -> sad/angry (closest match)
        "e8":  "f04",  # Confident    -> happy smile
        "e9":  "f02",  # Annoyed      -> sad/angry
        "e10": "f03",  # Overwhelmed  -> worried
        "e11": "f01",  # Determined   -> excited (forward energy)
        "e12": "f04",  # Affectionate -> happy smile
    },
    "Mao": {
        "e1":  "exp_04",  # Happy        -> excited/happy sparkle
        "e2":  "exp_02",  # Amused       -> closed smile (^_^)
        "e3":  "exp_05",  # Empathetic   -> sad
        "e4":  "exp_07",  # Curious      -> surprised/worried
        "e5":  "exp_07",  # Confused     -> surprised/worried
        "e6":  "exp_07",  # Surprised    -> surprised/worried
        "e7":  "exp_06",  # Embarrassed  -> shy/blush
        "e8":  "exp_04",  # Confident    -> happy sparkle
        "e9":  "exp_08",  # Annoyed      -> angry
        "e10": "exp_05",  # Overwhelmed  -> sad
        "e11": "exp_04",  # Determined   -> excited
        "e12": "exp_02",  # Affectionate -> closed smile
    },
}

# Models with only motions — use motion group index for variety
# No expression files, so we cycle through idle motions for emotional variation
MODEL_MOTION_MAP = {
    "Hiyori": {
        "idle_motion_count": 9,
        "tap_motion_count": 1,
    },
    "Rice": {
        "idle_motion_count": 1,
        "tap_motion_count": 3,
    },
    "Senko": {
        "idle_motion_count": 1,
        "tap_motion_count": 1,
        "taphead_motion_count": 2,
    },
}


# --- Current State ---

_current_model = None
_current_state = "idle"


def set_current_model(model_name: str):
    """Set which Live2D model is currently loaded."""
    global _current_model
    _current_model = model_name


def get_expression_for_emotion(emotion: str) -> dict:
    """Get the Live2D expression/motion command for a given emotion.
    Returns a dict describing what to do on the frontend."""
    if _current_model and _current_model in MODEL_EXPRESSION_MAP:
        expr_map = MODEL_EXPRESSION_MAP[_current_model]
        expr_id = expr_map.get(emotion, expr_map.get("e1", "f00"))
        return {
            "type": "expression",
            "model": _current_model,
            "expression": expr_id,
            "emotion": emotion,
        }
    elif _current_model and _current_model in MODEL_MOTION_MAP:
        # Motion-only model — use tap motion for emphasis, idle otherwise
        motion_info = MODEL_MOTION_MAP[_current_model]
        return {
            "type": "motion",
            "model": _current_model,
            "group": "TapBody" if emotion not in ("e1",) else "Idle",
            "index": hash(emotion) % max(1, motion_info.get("tap_motion_count", 1)),
            "emotion": emotion,
        }
    else:
        # Unknown model or no model set — just report emotion
        return {
            "type": "emotion",
            "emotion": emotion,
        }


# --- Emotion Detection from Text ---

EMOTION_KEYWORDS = [
    # e12 - Affectionate
    (["love", "thank you", "you're sweet", "you're the best", "cutie",
      "heart", "glad i could help", "happy to help", "you're welcome",
      "♡", "❤"], "e12"),
    # e7 - Embarrassed / Apologetic
    (["sorry", "apolog", "unfortunately", "my bad", "my mistake",
      "oops", "i was wrong", "i made an error", "couldn't find",
      "i can't", "i'm afraid", "i don't have"], "e7"),
    # e10 - Overwhelmed
    (["this is a lot", "so many", "overwhelm", "massive", "huge amount",
      "complex", "complicated"], "e10"),
    # e6 - Surprised
    (["wow", "whoa", "oh!", "amazing!", "incredible!", "no way",
      "fascinating", "that's wild", "didn't expect"], "e6"),
    # e5 - Confused
    (["hmm", "confus", "unclear", "ambiguous", "what do you mean",
      "not sure what", "i'm not sure", "wait", "actually..."], "e5"),
    # e9 - Annoyed
    (["again", "repeatedly", "as i said", "i already", "once more",
      "please don't", "that's not"], "e9"),
    # e4 - Curious
    (["?", "what is", "how does", "tell me more", "interesting",
      "i wonder", "curious", "what if", "could you"], "e4"),
    # e8 - Confident
    (["found it", "here's", "let me show", "perfect", "exactly",
      "nailed", "done!", "easy", "no problem", "absolutely",
      "definitely", "certainly"], "e8"),
    # e11 - Determined
    (["let me", "i'll", "going to", "here's how", "step by step",
      "first,", "here's what we'll do", "working on"], "e11"),
    # e2 - Amused
    (["haha", "lol", "lmao", "funny", "joke", "silly",
      "that's great", "nyaa", "nya~"], "e2"),
    # e3 - Empathetic
    (["i understand", "that's tough", "i'm sorry to hear", "it's okay",
      "don't worry", "take your time", "hang in there"], "e3"),
    # e1 - Happy (default positive)
    (["great", "good", "nice", "awesome", "wonderful", "yes!",
      "sounds good", "let's go", "exciting"], "e1"),
]


def detect_emotion(text: str) -> str:
    """Detect emotion from response text. Returns e1-e12."""
    if not text:
        return "e1"
    lower = text.lower()
    for keywords, emotion in EMOTION_KEYWORDS:
        for kw in keywords:
            if kw in lower:
                return emotion
    return "e1"


# --- Hook Callbacks ---
# These are called by waifu.py's monkey patches on cli.HermesCLI.


def on_user_input_received(*args, **kwargs):
    """Triggered when the user enters a prompt."""
    global _current_state
    _current_state = "thinking"


def on_tool_start(tool_call_id=None, function_name=None, function_args=None):
    """Triggered when a tool starts execution."""
    global _current_state
    _current_state = "working"


def on_tool_complete(tool_call_id=None, function_name=None, function_args=None, function_result=None):
    """Triggered when a tool completes."""
    global _current_state
    _current_state = "idle"


def on_tool_error(*args, **kwargs):
    """Triggered on tool error."""
    global _current_state
    _current_state = "error"


def on_agent_speaking(*args, **kwargs):
    """Triggered when the agent starts responding."""
    global _current_state
    _current_state = "speaking"


def on_agent_idle(*args, **kwargs):
    """Triggered when the agent is waiting for input."""
    global _current_state
    _current_state = "idle"


def set_waifu_state(state: str):
    """Set visual/emotion state. Maps e1-e12 to model expressions."""
    global _current_state
    if state.startswith("e") and state[1:].isdigit():
        # It's an emotion — get the expression command
        cmd = get_expression_for_emotion(state)
        _current_state = state
        # Write command to a state file the frontend can poll
        _write_state_file(cmd)
    else:
        _current_state = state


def _play_ping():
    """Play a notification sound when Neko-chan responds."""
    try:
        # Terminal bell — works everywhere, swap for ffplay <file> for custom sound
        print('\a', end='', flush=True)
    except Exception:
        pass


def on_agent_reply(text: str):
    """Triggered when response is ready. Detects emotion from text."""
    _play_ping()
    if text:
        emotion = detect_emotion(text)
        set_waifu_state(emotion)


# --- State File (frontend polls this) ---

def _get_state_file():
    """Path to state file shared between WSL and browser."""
    if "WSL_DISTRO_NAME" in os.environ:
        try:
            import subprocess
            result = subprocess.run(
                ["cmd.exe", "/c", "echo", "%USERNAME%"],
                capture_output=True, text=True
            )
            win_user = result.stdout.strip()
            if win_user:
                return f"/mnt/c/Users/{win_user}/.hermes-waifu-state.json"
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), ".hermes-waifu-state.json")


def _write_state_file(cmd: dict):
    """Write current state/command to file for frontend polling."""
    try:
        state_file = _get_state_file()
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(cmd, f)
    except Exception:
        pass
