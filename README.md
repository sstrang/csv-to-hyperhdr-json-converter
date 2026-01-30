# LED Grid to HyperHDR JSON Converter

Convert Google Sheet LED mappings to HyperHDR JSON format with support for hexagonal arrangements, monitor backlighting, and LED walls.

## ✨ New: Ambient Mode

**Perfect for hexagonal LED shelves around monitors!** Ambient mode intelligently blends between ambilight (edge sampling) and wall (position sampling) based on LED distance from the screen.

## Features

🎨 **Ambient Mode** - Hybrid for LED walls/shelves around monitors (RECOMMENDED for hexagonal setups)  
🖥️ **Perimeter Mode** - Classic monitor backlighting  
📺 **Wall Mode** - Full LED matrix displays  
📐 **Boundary Markers** - Use 'x' to define your monitor area  
🔧 **Flexible Controls** - Adjust edge-bias and sampling behavior

## Quick Start

### 1. Create Your Layout in Google Sheets

```
     0   1   2   3   4   5   6   7
30  31   x   x   x   x   x   x   x   x   8   9
29       x   x   x   x   x   x   x   x      10
28       x   x   x   x   x   x   x   x      11
27  26   x   x   x   x   x   x   x   x  12  13
     25  24  23  22  21  20  19  18
```

- **LED numbers** = WLED pixel indices
- **'x'** = Fill entire monitor area
- **Empty** = No LED

### 2. Export and Run

```bash
# Download as CSV from Google Sheets
# File → Download → Comma Separated Values (.csv)

# Run with ambient mode (RECOMMENDED for hex setups)
python led_mapper.py your_leds.csv output.json --mode ambient --boundary-aware --pretty
```

## Modes Explained

### 🎨 Ambient Mode (NEW - Recommended!)

**Best for:** Hexagonal LED shelves, LED walls around monitors, complex arrangements

Intelligently blends ambilight and wall modes:
- **LEDs close to monitor** → Sample screen edges (ambilight effect)
- **LEDs far from monitor** → Sample by position (wall effect)
- **Smooth transitions** between behaviors

**Controls:**
```bash
# Default balanced hybrid
python led_mapper.py leds.csv out.json --mode ambient --boundary-aware

# More wall-like (position-based)
python led_mapper.py leds.csv out.json --mode ambient --boundary-aware --edge-bias 0.2

# More ambilight-like (edge-based)
python led_mapper.py leds.csv out.json --mode ambient --boundary-aware --edge-bias 0.8
```

**Edge-bias parameter:**
- `0.0` = Pure wall mode (all LEDs sample by position)
- `0.5` = Balanced hybrid (default)
- `1.0` = Pure edge mode (all LEDs sample nearest edge)

### 🖥️ Perimeter Mode

**Best for:** Simple rectangular monitor backlighting, TV ambient lighting

Maps LEDs directly to screen edges. Only works well if LEDs form a simple rectangle around the monitor.

```bash
python led_mapper.py leds.csv out.json --mode perimeter --boundary-aware --depth 0.1
```

### 📺 Wall Mode

**Best for:** LED matrices that fill the entire display area, pixel art walls

Each LED samples from its exact grid position. Treats the entire LED array as a screen.

```bash
python led_mapper.py leds.csv out.json --mode wall
```

## Command Line Reference

```bash
python led_mapper.py INPUT.csv OUTPUT.json [OPTIONS]
```

### Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--mode` | `ambient`, `perimeter`, `wall` | `ambient` | Mapping mode |
| `--boundary-aware` | flag | off | Use 'x' markers to define screen |
| `--edge-bias` | 0.0-1.0 | 0.5 | Ambient: edge vs position blend |
| `--depth` | 0.0-1.0 | 0.05 | Perimeter: edge sampling depth |
| `--group` | integer | 0 | LED group number |
| `--pretty` | flag | off | Pretty-print JSON output |

## Examples for Different Setups

### Hexagonal LED Shelves (Your Setup!)

```bash
# Start with this - balanced hybrid
python led_mapper.py hex_shelves.csv output.json --mode ambient --boundary-aware --pretty

# Want more ambilight effect? Increase edge-bias
python led_mapper.py hex_shelves.csv output.json --mode ambient --boundary-aware --edge-bias 0.7 --pretty

# Want LEDs to follow position more? Decrease edge-bias
python led_mapper.py hex_shelves.csv output.json --mode ambient --boundary-aware --edge-bias 0.3 --pretty
```

### Simple Monitor Backlight

```bash
# Classic ambilight setup
python led_mapper.py backlight.csv output.json --mode perimeter --boundary-aware --pretty
```

### LED Wall/Matrix

```bash
# Full screen mirror
python led_mapper.py matrix.csv output.json --mode wall --pretty
```

## Understanding Ambient Mode

Ambient mode uses **distance-weighted blending**:

1. **Calculates each LED's distance** from the monitor boundary
2. **Determines closest screen edge** (top, bottom, left, right)
3. **Blends sampling position** between:
   - Grid position (where LED actually is)
   - Nearest edge position (ambilight-style)
4. **Weight factor** = edge-bias × (1 - distance)

**What this means:**
- LEDs right next to the monitor → Strong edge sampling
- LEDs far from monitor → Mostly position sampling
- Smooth gradient of behavior across your layout
- Adjustable with `--edge-bias` parameter

### Visual Example

```
Far LEDs (more wall-like)
    ↓
    20  21  22  23
    19  x  x  x  x  24
    18  x  x  x  x  25  ← Close LEDs (more edge-like)
    17  x  x  x  x  26
    16  15  14  13
         ↑
    Far LEDs (more wall-like)
```

## Troubleshooting

### "LEDs are compressed to a few points"
→ You're using perimeter mode with a complex layout  
→ Switch to `--mode ambient` or `--mode wall`

### Colors look too "washed out" or averaged
→ Try increasing `--edge-bias` (makes it more ambilight-like)  
→ Example: `--edge-bias 0.7`

### LEDs don't follow screen content well
→ Try decreasing `--edge-bias` (makes it more wall-like)  
→ Example: `--edge-bias 0.3`

### Need to fine-tune the effect
→ Experiment with `--edge-bias` in 0.1 increments  
→ Start at 0.5 and adjust up or down

### Coordinates outside 0.0-1.0 range
→ Make sure you're using `--boundary-aware` flag  
→ Verify 'x' markers completely fill your monitor area

## Creating Your CSV Layout

### For Hexagonal/Complex Arrangements

1. **Fill monitor area with 'x'**
   - Every cell representing the monitor gets 'x'
   - Creates a solid rectangle

2. **Place LEDs around the 'x' area**
   - Match your physical LED positions
   - Number sequentially (0, 1, 2...)

3. **Leave appropriate spacing**
   - Empty cells = gaps between LEDs
   - Maintain your hexagonal pattern

### Tips

✅ **DO:**
- Use `--boundary-aware` for accurate mapping
- Start with default `--edge-bias 0.5` and adjust
- Test with HyperHDR's LED visualization
- Match your CSV to physical layout

❌ **DON'T:**
- Use perimeter mode for complex arrangements
- Skip the boundary markers for best results
- Forget to number LEDs sequentially

## Using with HyperHDR

1. Generate JSON with this script
2. Open HyperHDR web interface (usually http://your-ip:8090)
3. Go to **Configuration → LED Hardware → LED Layout**
4. Import JSON or paste contents
5. Go to **Configuration → LED Visualization** to preview
6. Fine-tune if needed:
   - Adjust `--edge-bias` for different behavior
   - Try different modes
   - Re-import and test

## Recommended Settings by Setup Type

| Setup Type | Mode | Boundary-Aware | Edge-Bias | Notes |
|------------|------|----------------|-----------|-------|
| Hex shelves around monitor | `ambient` | Yes | 0.5-0.7 | Start at 0.5, increase for more ambilight |
| Simple monitor backlight | `perimeter` | Yes | N/A | Use `--depth` instead |
| LED matrix/wall | `wall` | Optional | N/A | Boundary-aware for partial walls |
| TV strip | `perimeter` | Yes | N/A | Classic setup |
| Irregular arrangement | `ambient` | Yes | 0.4-0.6 | Experiment with bias |

## Requirements

- Python 3.6 or higher
- No additional packages (uses standard library only)

## Advanced Usage

### Multiple Configurations

Generate multiple configs with different settings and test:

```bash
# Generate three variations
python led_mapper.py leds.csv config_balanced.json --mode ambient --boundary-aware --edge-bias 0.5 --pretty
python led_mapper.py leds.csv config_edge.json --mode ambient --boundary-aware --edge-bias 0.7 --pretty
python led_mapper.py leds.csv config_wall.json --mode ambient --boundary-aware --edge-bias 0.3 --pretty

# Test each in HyperHDR to find your favorite
```

### Multi-Monitor/Multi-Zone

Create separate CSV files for each zone:

```bash
python led_mapper.py left_monitor.csv left.json --mode ambient --group 0
python led_mapper.py right_monitor.csv right.json --mode ambient --group 1
python led_mapper.py center_accent.csv center.json --mode ambient --group 2

# Combine JSON files manually or import separately
```

## What's Different About Ambient Mode?

Traditional modes are rigid:
- **Perimeter** = Always sample edges
- **Wall** = Always sample position

**Ambient mode is adaptive:**
- Considers LED distance from screen
- Blends behaviors smoothly
- Gives you control with `--edge-bias`
- Perfect for complex arrangements

Think of it as: "Let LEDs near the monitor act like ambilight, let distant LEDs act like a wall, and blend smoothly between them."

## License

Free to use and modify for your LED projects!

---

**Pro tip for your hexagonal setup:** Start with `--mode ambient --boundary-aware --edge-bias 0.5` and then adjust the edge-bias up or down in 0.1 increments until you find the perfect effect for your room!
