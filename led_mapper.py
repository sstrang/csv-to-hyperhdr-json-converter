#!/usr/bin/env python3
"""
LED Grid to HyperHDR JSON Converter (Enhanced with Boundary Markers)

This script converts a Google Sheet (exported as CSV) containing LED pixel mappings
into the HyperHDR JSON format, with support for boundary markers.

You can mark monitor boundaries with 'x' or 'X' characters to help define the
screen area. This helps the script map LEDs more accurately to screen edges.

Usage:
    python led_mapper.py input.csv output.json --mode perimeter
    python led_mapper.py input.csv output.json --mode wall
    python led_mapper.py input.csv output.json --mode perimeter --boundary-aware
"""

import csv
import json
import argparse
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum


class MappingMode(Enum):
    WALL = "wall"
    PERIMETER = "perimeter"
    AMBIENT = "ambient"


def read_led_grid(csv_file: str) -> Tuple[Dict[int, Tuple[int, int]], Set[Tuple[int, int]]]:
    """
    Read the CSV file and extract pixel positions and boundary markers.
    
    Returns:
        - led_positions: dictionary mapping pixel_number -> (row, col) position
        - boundaries: set of (row, col) positions marked as boundaries (x or X)
    """
    led_positions = {}
    boundaries = set()
    
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    # Find all non-empty cells
    for row_idx, row in enumerate(rows):
        for col_idx, cell in enumerate(row):
            cell = cell.strip()
            if cell:
                # Check if it's a boundary marker
                if cell.lower() == 'x':
                    boundaries.add((row_idx, col_idx))
                # Check if it's a pixel number
                elif cell.isdigit():
                    pixel_num = int(cell)
                    led_positions[pixel_num] = (row_idx, col_idx)
    
    return led_positions, boundaries


def calculate_bounds(positions: Dict[int, Tuple[int, int]]) -> Tuple[int, int, int, int]:
    """Calculate the overall grid bounds."""
    if not positions:
        return 0, 0, 0, 0
    
    rows = [pos[0] for pos in positions.values()]
    cols = [pos[1] for pos in positions.values()]
    
    min_row, max_row = min(rows), max(rows)
    min_col, max_col = min(cols), max(cols)
    
    return min_row, max_row, min_col, max_col


def calculate_boundary_bounds(boundaries: Set[Tuple[int, int]]) -> Optional[Tuple[int, int, int, int]]:
    """
    Calculate the bounds of the boundary markers (monitor area).
    
    Boundaries are expected to be a filled rectangle of 'x' markers
    representing the monitor area.
    """
    if not boundaries:
        return None
    
    rows = [pos[0] for pos in boundaries]
    cols = [pos[1] for pos in boundaries]
    
    min_row, max_row = min(rows), max(rows)
    min_col, max_col = min(cols), max(cols)
    
    return min_row, max_row, min_col, max_col


def classify_edge_with_boundaries(row: int, col: int, 
                                   boundary_bounds: Optional[Tuple[int, int, int, int]],
                                   led_bounds: Tuple[int, int, int, int]) -> str:
    """
    Classify which edge of the screen an LED is on.
    
    If boundary_bounds is provided, use those to determine screen edges.
    Otherwise, fall back to LED bounds.
    
    Returns: 'top', 'bottom', 'left', 'right', or 'interior'
    """
    if boundary_bounds:
        min_row, max_row, min_col, max_col = boundary_bounds
    else:
        min_row, max_row, min_col, max_col = led_bounds
    
    # Calculate distance to each edge
    dist_top = abs(row - min_row)
    dist_bottom = abs(row - max_row)
    dist_left = abs(col - min_col)
    dist_right = abs(col - max_col)
    
    # Find minimum distance
    min_dist = min(dist_top, dist_bottom, dist_left, dist_right)
    
    # Classify based on closest edge (with priority for ties)
    if dist_top == min_dist:
        return 'top'
    elif dist_bottom == min_dist:
        return 'bottom'
    elif dist_left == min_dist:
        return 'left'
    elif dist_right == min_dist:
        return 'right'
    else:
        return 'interior'


def create_perimeter_config(led_positions: Dict[int, Tuple[int, int]], 
                           boundaries: Set[Tuple[int, int]],
                           group: int = 0,
                           depth: float = 0.05,
                           boundary_aware: bool = False) -> List[Dict]:
    """
    Convert LED positions to HyperHDR perimeter format.
    
    Maps LEDs to screen edges based on their position in the grid.
    If boundary_aware=True and boundaries are provided, uses boundary markers
    to define the screen area.
    
    depth: How far into the screen the LED samples (0.0-1.0)
    """
    if not led_positions:
        return []
    
    # Get LED bounds
    led_min_row, led_max_row, led_min_col, led_max_col = calculate_bounds(led_positions)
    
    # Get boundary bounds if available and requested
    boundary_bounds = None
    if boundary_aware and boundaries:
        boundary_bounds = calculate_boundary_bounds(boundaries)
        print(f"Using boundary markers to define screen area")
        print(f"  Boundary area: rows {boundary_bounds[0]}-{boundary_bounds[1]}, "
              f"cols {boundary_bounds[2]}-{boundary_bounds[3]}")
    
    # Determine which bounds to use for normalization
    if boundary_bounds:
        min_row, max_row, min_col, max_col = boundary_bounds
    else:
        min_row, max_row, min_col, max_col = led_min_row, led_max_row, led_min_col, led_max_col
    
    width = max_col - min_col + 1
    height = max_row - min_row + 1
    
    # Sort LEDs by pixel number
    sorted_leds = sorted(led_positions.items())
    
    result = []
    edge_counts = {'top': 0, 'bottom': 0, 'left': 0, 'right': 0, 'interior': 0}
    
    for pixel_num, (row, col) in sorted_leds:
        # Determine which edge this LED is on
        edge = classify_edge_with_boundaries(row, col, boundary_bounds, 
                                            (led_min_row, led_max_row, led_min_col, led_max_col))
        edge_counts[edge] += 1
        
        # Calculate normalized position along the edge
        # Clamp positions to ensure they stay within 0.0-1.0 range
        if edge == 'top':
            # Top edge: spans horizontally
            # Calculate position along the top edge
            edge_position = max(0.0, min(1.0, (col - min_col) / width))
            edge_size = 1.0 / width
            led_config = {
                "hmax": round(min(edge_position + edge_size, 1.0), 4),
                "hmin": round(max(edge_position, 0.0), 4),
                "vmax": round(depth, 4),
                "vmin": 0.0,
                "group": group
            }
        elif edge == 'bottom':
            # Bottom edge: spans horizontally
            edge_position = max(0.0, min(1.0, (col - min_col) / width))
            edge_size = 1.0 / width
            led_config = {
                "hmax": round(min(edge_position + edge_size, 1.0), 4),
                "hmin": round(max(edge_position, 0.0), 4),
                "vmax": 1.0,
                "vmin": round(1.0 - depth, 4),
                "group": group
            }
        elif edge == 'left':
            # Left edge: spans vertically
            edge_position = max(0.0, min(1.0, (row - min_row) / height))
            edge_size = 1.0 / height
            led_config = {
                "hmax": round(depth, 4),
                "hmin": 0.0,
                "vmax": round(min(edge_position + edge_size, 1.0), 4),
                "vmin": round(max(edge_position, 0.0), 4),
                "group": group
            }
        elif edge == 'right':
            # Right edge: spans vertically
            edge_position = max(0.0, min(1.0, (row - min_row) / height))
            edge_size = 1.0 / height
            led_config = {
                "hmax": 1.0,
                "hmin": round(1.0 - depth, 4),
                "vmax": round(min(edge_position + edge_size, 1.0), 4),
                "vmin": round(max(edge_position, 0.0), 4),
                "group": group
            }
        else:
            # Interior LED - treat as center point
            h_pos = (col - min_col) / width
            v_pos = (row - min_row) / height
            h_size = 1.0 / width
            v_size = 1.0 / height
            led_config = {
                "hmax": round(min(h_pos + h_size, 1.0), 4),
                "hmin": round(h_pos, 4),
                "vmax": round(min(v_pos + v_size, 1.0), 4),
                "vmin": round(v_pos, 4),
                "group": group
            }
        
        result.append(led_config)
    
    print(f"Edge distribution: Top={edge_counts['top']}, Bottom={edge_counts['bottom']}, "
          f"Left={edge_counts['left']}, Right={edge_counts['right']}, Interior={edge_counts['interior']}")
    
    if edge_counts['interior'] > 0:
        print(f"⚠ Warning: {edge_counts['interior']} LEDs classified as interior - "
              f"these may not work well in perimeter mode")
    
    return result


def create_ambient_config(led_positions: Dict[int, Tuple[int, int]], 
                         boundaries: Set[Tuple[int, int]],
                         group: int = 0,
                         boundary_aware: bool = False,
                         edge_bias: float = 0.5) -> List[Dict]:
    """
    Convert LED positions to HyperHDR ambient format.
    
    This mode is designed for LED walls/shelves surrounding a monitor.
    LEDs closer to the boundary edges sample more from screen edges (ambilight).
    LEDs farther from boundary sample more from their grid position (wall mode).
    
    edge_bias: Controls the blend between edge and position sampling (0.0-1.0)
               0.0 = pure wall mode (position-based)
               1.0 = pure edge mode (ambilight-style)
               0.5 = balanced hybrid (default)
    """
    if not led_positions:
        return []
    
    # Get bounds
    led_min_row, led_max_row, led_min_col, led_max_col = calculate_bounds(led_positions)
    
    # Use boundary bounds if available and requested
    if boundary_aware and boundaries:
        boundary_bounds = calculate_boundary_bounds(boundaries)
        screen_min_row, screen_max_row, screen_min_col, screen_max_col = boundary_bounds
        print(f"Using boundary markers to define screen area")
        print(f"  Screen area: rows {screen_min_row}-{screen_max_row}, "
              f"cols {screen_min_col}-{screen_max_col}")
    else:
        # Use LED bounds as screen bounds
        screen_min_row, screen_max_row = led_min_row, led_max_row
        screen_min_col, screen_max_col = led_min_col, led_max_col
    
    screen_height = screen_max_row - screen_min_row + 1
    screen_width = screen_max_col - screen_min_col + 1
    
    # Overall grid dimensions (for normalization)
    grid_height = led_max_row - led_min_row + 1
    grid_width = led_max_col - led_min_col + 1
    
    # Sort LEDs by pixel number
    sorted_leds = sorted(led_positions.items())
    
    result = []
    
    for pixel_num, (row, col) in sorted_leds:
        # Calculate normalized position in overall grid
        grid_h = (col - led_min_col) / grid_width
        grid_v = (row - led_min_row) / grid_height
        
        # Calculate distance to screen boundary (normalized)
        dist_to_screen_top = abs(row - screen_min_row) / grid_height
        dist_to_screen_bottom = abs(row - screen_max_row) / grid_height
        dist_to_screen_left = abs(col - screen_min_col) / grid_width
        dist_to_screen_right = abs(col - screen_max_col) / grid_width
        
        # Find minimum distance to any screen edge
        min_dist = min(dist_to_screen_top, dist_to_screen_bottom, 
                      dist_to_screen_left, dist_to_screen_right)
        
        # Determine which edge is closest
        if min_dist == dist_to_screen_top:
            edge = 'top'
        elif min_dist == dist_to_screen_bottom:
            edge = 'bottom'
        elif min_dist == dist_to_screen_left:
            edge = 'left'
        else:
            edge = 'right'
        
        # Calculate edge-based coordinates (ambilight style)
        if edge == 'top':
            edge_h = max(0.0, min(1.0, (col - screen_min_col) / screen_width))
            edge_v = 0.0
        elif edge == 'bottom':
            edge_h = max(0.0, min(1.0, (col - screen_min_col) / screen_width))
            edge_v = 1.0
        elif edge == 'left':
            edge_h = 0.0
            edge_v = max(0.0, min(1.0, (row - screen_min_row) / screen_height))
        else:  # right
            edge_h = 1.0
            edge_v = max(0.0, min(1.0, (row - screen_min_row) / screen_height))
        
        # Blend between grid position and edge position based on edge_bias
        # Also factor in distance - LEDs farther from screen act more wall-like
        distance_factor = min(1.0, min_dist * 3)  # Scale distance impact
        effective_bias = edge_bias * (1.0 - distance_factor)
        
        center_h = grid_h * (1.0 - effective_bias) + edge_h * effective_bias
        center_v = grid_v * (1.0 - effective_bias) + edge_v * effective_bias
        
        # Calculate sampling area size (smaller for edge-like LEDs)
        base_size = 0.05  # Base sampling size
        h_size = base_size / grid_width
        v_size = base_size / grid_height
        
        # Create LED config
        led_config = {
            "hmax": round(min(center_h + h_size, 1.0), 4),
            "hmin": round(max(center_h - h_size, 0.0), 4),
            "vmax": round(min(center_v + v_size, 1.0), 4),
            "vmin": round(max(center_v - v_size, 0.0), 4),
            "group": group
        }
        
        result.append(led_config)
    
    return result


def create_wall_config(led_positions: Dict[int, Tuple[int, int]], 
                      boundaries: Set[Tuple[int, int]],
                      group: int = 0,
                      boundary_aware: bool = False) -> List[Dict]:
    """
    Convert LED positions to HyperHDR wall format.
    
    Each LED covers a region of the screen based on its grid position.
    If boundary_aware=True, normalizes positions relative to boundary markers.
    """
    if not led_positions:
        return []
    
    # Get bounds
    led_min_row, led_max_row, led_min_col, led_max_col = calculate_bounds(led_positions)
    
    # Use boundary bounds if available and requested
    if boundary_aware and boundaries:
        boundary_bounds = calculate_boundary_bounds(boundaries)
        min_row, max_row, min_col, max_col = boundary_bounds
        print(f"Using boundary markers to define screen area")
    else:
        min_row, max_row, min_col, max_col = led_min_row, led_max_row, led_min_col, led_max_col
    
    height = max_row - min_row + 1
    width = max_col - min_col + 1
    
    # Sort LEDs by pixel number
    sorted_leds = sorted(led_positions.items())
    
    result = []
    
    for pixel_num, (row, col) in sorted_leds:
        # Normalize positions to 0.0 - 1.0 range relative to screen bounds
        norm_col = col - min_col
        norm_row = row - min_row
        
        # Calculate the position of this LED in normalized space
        h_start = norm_col / width
        h_end = (norm_col + 1) / width
        
        v_start = norm_row / height
        v_end = (norm_row + 1) / height
        
        led_config = {
            "hmax": round(h_end, 4),
            "hmin": round(h_start, 4),
            "vmax": round(v_end, 4),
            "vmin": round(v_start, 4),
            "group": group
        }
        
        result.append(led_config)
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Convert LED grid CSV to HyperHDR JSON format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Mapping Modes:
  perimeter - Maps LEDs to screen edges (monitor backlighting)
  wall      - Maps LEDs as a grid filling the screen (LED wall)
  ambient   - Hybrid mode for LED walls around monitors (NEW!)

Boundary Markers:
  Use 'x' or 'X' to fill the entire monitor/screen area.
  The rectangle of 'x' markers defines where the monitor is.
  LEDs should be placed around the outside of this filled area.

Ambient Mode (Recommended for Hexagonal Setups):
  This mode blends between ambilight (edge sampling) and wall (position sampling).
  LEDs close to the monitor act like ambilight (sample screen edges).
  LEDs far from the monitor act like wall mode (sample their position).
  
  --edge-bias controls the blend:
    0.0 = Pure wall mode (all LEDs sample by position)
    0.5 = Balanced hybrid (default)
    1.0 = Pure edge mode (all LEDs sample nearest edge)

Example CSV with boundaries:
     0   1   2   3   4   5
    30  31  32  33  34   6
    29   x   x   x   x   7
    28   x   x   x   x   8
    27   x   x   x   x   9
    26  25  24  23  22  10
    
The filled 'x' area represents the monitor, LEDs go around it.

Example usage:
  python led_mapper.py leds.csv out.json --mode ambient --boundary-aware
  python led_mapper.py leds.csv out.json --mode ambient --edge-bias 0.7
  python led_mapper.py leds.csv out.json --mode wall --depth 0.1
        """
    )
    
    parser.add_argument('input_csv', help='Input CSV file (exported from Google Sheets)')
    parser.add_argument('output_json', help='Output JSON file for HyperHDR')
    parser.add_argument('--mode', type=str, choices=['perimeter', 'wall', 'ambient'], 
                       default='ambient',
                       help='Mapping mode: perimeter (edges), wall (full grid), or ambient (hybrid)')
    parser.add_argument('--boundary-aware', action='store_true',
                       help='Use boundary markers (x/X) to define screen area')
    parser.add_argument('--group', type=int, default=0, 
                       help='LED group number (default: 0)')
    parser.add_argument('--depth', type=float, default=0.05,
                       help='Perimeter depth - how far LEDs sample into screen (0.0-1.0, default: 0.05)')
    parser.add_argument('--edge-bias', type=float, default=0.5,
                       help='Ambient mode: edge vs position bias (0.0=wall, 1.0=edge, default: 0.5)')
    parser.add_argument('--pretty', action='store_true',
                       help='Pretty print JSON output')
    
    args = parser.parse_args()
    
    # Validate depth
    if not 0.0 <= args.depth <= 1.0:
        print("ERROR: --depth must be between 0.0 and 1.0")
        return 1
    
    # Validate edge-bias
    if not 0.0 <= args.edge_bias <= 1.0:
        print("ERROR: --edge-bias must be between 0.0 and 1.0")
        return 1
    
    # Read the LED grid
    print(f"Reading LED positions from {args.input_csv}...")
    led_positions, boundaries = read_led_grid(args.input_csv)
    
    if not led_positions:
        print("ERROR: No LED positions found in CSV file!")
        return 1
    
    print(f"Found {len(led_positions)} LEDs")
    if boundaries:
        print(f"Found {len(boundaries)} boundary markers")
    
    # Get grid dimensions
    min_row, max_row, min_col, max_col = calculate_bounds(led_positions)
    print(f"LED grid dimensions: {max_col - min_col + 1} cols × {max_row - min_row + 1} rows")
    
    # Convert based on mode
    print(f"Converting to HyperHDR JSON format (mode: {args.mode})...")
    
    if args.mode == 'perimeter':
        hyperhdr_config = create_perimeter_config(led_positions, boundaries, 
                                                  args.group, args.depth, args.boundary_aware)
    elif args.mode == 'ambient':
        hyperhdr_config = create_ambient_config(led_positions, boundaries,
                                               args.group, args.boundary_aware, args.edge_bias)
    else:  # wall mode
        hyperhdr_config = create_wall_config(led_positions, boundaries, 
                                            args.group, args.boundary_aware)
    
    # Write output
    print(f"Writing to {args.output_json}...")
    with open(args.output_json, 'w') as f:
        if args.pretty:
            json.dump(hyperhdr_config, f, indent=2)
        else:
            json.dump(hyperhdr_config, f)
    
    print(f"✓ Successfully converted {len(hyperhdr_config)} LEDs!")
    print(f"\nFirst LED config:")
    print(json.dumps(hyperhdr_config[0], indent=2))
    print(f"\nLast LED config:")
    print(json.dumps(hyperhdr_config[-1], indent=2))
    
    return 0


if __name__ == '__main__':
    exit(main())
