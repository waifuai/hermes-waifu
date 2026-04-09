# hermes-waifu

Live2D waifu display for Hermes Agent with expression controls.

## What is this?

Live animated waifu you can drag around, resize, and control expressions. No TTS, no chat, no complexity.

**Features:**
- Live2D model rendering in browser
- 5 built-in models (Hiyori, Haru, Mao, Rice, Senko)
- Drag to reposition, scroll to resize (5%-200%)
- Model selector dropdown
- Expression controls (per-model)
- Emotion system (e1-e12)
- Agent state display (idle/thinking/speaking/etc)
- Manual mode toggle (override auto state)
- Minimal dependencies (4 CDN scripts)

## Expression System

Three rows of controls at the bottom:

| Row | What it does |
|-----|-------------|
| **States** | Agent states: idle, listening, speaking, thinking, working, error |
| **Expressions** | Per-model face buttons — Haru (f00-f07), Mao (exp_01-08), motion-only models show "motion-only" |
| **Emotions** | e1-e12 mapped to names (happy, amused, empathetic, curious, confused, surprised, embarrassed, confident, annoyed, overwhelmed, determined, affectionate) |

Emotion→expression mapping matches `waifu_hook.py`:
- Haru: e1(happy)→f04, e4(curious)→f01, e5(confused)→f06, etc.
- Mao: e1(happy)→exp_04, e4(curious)→exp_07, e9(annoyed)→exp_08, etc.

Active expression/emotion is highlighted with a glow.

## Expression Details

### Haru (f00-f07)
| ID | Face |
|----|------|
| f00 | neutral |
| f01 | surprised/excited |
| f02 | angry/sad |
| f03 | worried/concerned |
| f04 | happy (closed eyes) |
| f05 | shocked |
| f06 | sad |
| f07 | pouty |

### Mao (exp_01-exp_08)
| ID | Face |
|----|------|
| exp_01 | neutral |
| exp_02 | closed smile (^_^) |
| exp_03 | neutral alt |
| exp_04 | excited sparkle |
| exp_05 | sad |
| exp_06 | shy/blush |
| exp_07 | worried |
| exp_08 | angry |

### Motion-only (Hiyori, Rice, Senko)
No expression files — only idle/tap motions. Emotion buttons exist but have no visual effect on the model face.

## Usage

### Live2D Display

Open `index.html` in a browser. No server needed, no build step. Pure client-side.

**Controls:**
- Click expression/emotion buttons to change the face
- Scroll over model to resize
- Drag to reposition
- ⏸/▶ button toggles manual mode (ignores server state)
- Model selector in top-right header

### Hermes Agent Integration

Symlink `src/waifu.py` and `src/waifu_hook.py` into `~/.hermes/hermes-agent/`:

```bash
ln -sf /path/to/hermes-waifu/src/waifu.py ~/.hermes/hermes-agent/waifu.py
ln -sf /path/to/hermes-waifu/src/waifu_hook.py ~/.hermes/hermes-agent/waifu_hook.py
```

Then run `python waifu.py` instead of `python cli.py` to get lifecycle hooks injected.

`waifu_hook.py` writes state to `~/.hermes-waifu-state.json`. The HTML polls `/state` to sync (requires a server endpoint, or use manual mode).

## Adding more models

Edit the `models` array in `index.html`:

```javascript
const models = [
  {
    name: "YourModel",
    url: "https://cdn.jsdelivr.net/.../model.model3.json",
    type: "expression",           // or "motion-only"
    expressions: ["face1","face2"] // only if type="expression"
  }
];
```

Models must be hosted online (CDN) or served locally.

## License

MIT No Attribution - see [LICENSE](LICENSE)
