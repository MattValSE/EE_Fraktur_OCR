#!/bin/bash
img_width=5120
img_height=7680
tile_size=512
echo "Expected final dimensions: ${img_width}x${img_height} pixels"

# Create a blank canvas of the expected size
convert -size ${img_width}x${img_height} xc:transparent canvas.png

# Initialize variables to track actual dimensions
max_x=0
max_y=0

# Place each tile at its correct position
echo "Placing tiles on canvas..."
for file in tiles/tile_*.jpeg; do
    filename=$(basename "$file")
    
    # Extract coordinates from filename using proper parsing
    x=$(echo $filename | sed -E 's/tile_([0-9]+)_([0-9]+)\.jpeg/\2/')
    y=$(echo $filename | sed -E 's/tile_([0-9]+)_([0-9]+)\.jpeg/\1/')
    
    # Remove leading zeros to avoid octal interpretation
    x=$(echo $x | sed 's/^0*//')
    y=$(echo $y | sed 's/^0*//')
    
    # Handle empty strings (all zeros removed)
    [ -z "$x" ] && x=0
    [ -z "$y" ] && y=0

    # Perform integer division for x and y
    if [[ $x -ne 0 ]]; then
    x_half=$((x / 2))
    else
        x_half=0
    fi

    if [[ $y -ne 0 ]]; then
        y_half=$((y / 2))
    else
        y_half=0
    fi

    # Convert tile indices to pixel positions
    x_pixel=$((x_half * tile_size))
    y_pixel=$((y_half * tile_size))

    
    # Get actual dimensions of this tile using identify
    dimensions=$(identify -format "%w %h" "$file")
    tile_width=$(echo $dimensions | cut -d' ' -f1)
    tile_height=$(echo $dimensions | cut -d' ' -f2)
    
    echo "Placing tile $filename at position $x_half,$y_half (size: ${tile_width}x${tile_height})"
    
    # Composite this tile onto the canvas at the correct position
    convert canvas.png "$file" -geometry +${x_half}+${y_half} -composite canvas.png
    
    # Track max bounds
    right_edge=$((x_pixel + tile_width))
    bottom_edge=$((y_pixel + tile_height))
    
    [[ $right_edge -gt $max_x ]] && max_x=$right_edge
    [[ $bottom_edge -gt $max_y ]] && max_y=$bottom_edge
done

echo "Detected image dimensions from tiles: ${max_x}x${max_y} pixels"

# If the detected dimensions don't match the expected ones, report the difference
if [ $max_x -ne $img_width ] || [ $max_y -ne $img_height ]; then
    echo "Warning: Detected dimensions (${max_x}x${max_y}) don't match expected (${img_width}x${img_height})"
    echo "Continuing with the expected dimensions as specified."
fi

# Ensure the canvas has the expected dimensions
convert canvas.png -geometry +${img_height/2}+${img_width/2} -background transparent -trim full_image.png

echo "Full image saved as full_image.png."