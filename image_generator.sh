#!/bin/bash

# Configuration
PYTHON_SCRIPT="image_generator.py" # Change this to match your Python script name

# Ensure gum is available
if ! command -v gum &>/dev/null; then
  echo "gum is required but not installed. Please install it first:"
  echo "brew install gum    # On macOS"
  echo "apt install gum     # On Ubuntu/Debian"
  exit 1
fi

# Ensure the Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
  echo "Error: $PYTHON_SCRIPT not found in current directory"
  exit 1
fi

# Ensure Python is available
if ! command -v python &>/dev/null; then
  if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
  else
    echo "Error: Python not found"
    exit 1
  fi
else
  PYTHON_CMD="python"
fi

# Style guide
STYLE_GUIDE="
🎨 Image Style Guide:
- photorealistic: Highly detailed, natural looking images
- artistic: Creative interpretation with artistic flair
- cartoon: Bold colors and clean lines
- minimalist: Simple elements with negative space
- pixel_art: Retro pixel-based style
"

# Size guide
SIZE_GUIDE="
📐 Size Guide:
- square: 1024x1024 pixels
- portrait: 1024x1792 pixels
- landscape: 1792x1024 pixels
"

# Show header
gum style \
  --border double \
  --align center \
  --width 50 \
  --margin "1 2" \
  --padding "1 2" \
  'Image Generator'

# Style selection with guide
gum style "$STYLE_GUIDE"
echo "Choose image style:"
STYLE=$(gum choose \
  --cursor.foreground 212 \
  --selected.foreground 212 \
  "photorealistic" \
  "artistic" \
  "cartoon" \
  "minimalist" \
  "pixel_art")

# Size selection with guide
gum style "$SIZE_GUIDE"
echo "Choose image size:"
SIZE=$(gum choose \
  --cursor.foreground 212 \
  --selected.foreground 212 \
  "square" \
  "portrait" \
  "landscape")

# Image description
echo "Enter image description:"
DESCRIPTION=$(gum input \
  --placeholder "A serene mountain landscape at sunset..." \
  --width 50 \
  --char-limit 1000)

# Validate description
if [ -z "$DESCRIPTION" ]; then
  gum style --foreground 1 "Error: Description cannot be empty"
  exit 1
fi

# Additional instructions (optional)
echo "Enter additional instructions (optional):"
INSTRUCTIONS=$(gum input \
  --placeholder "Focus on dramatic lighting..." \
  --width 50 \
  --char-limit 500)

# Filename (optional)
echo "Enter filename (optional):"
FILENAME=$(gum input \
  --placeholder "mountain-sunset" \
  --width 30)

# Build the command
CMD="$PYTHON_CMD \"$PYTHON_SCRIPT\" \"$DESCRIPTION\" --style $STYLE --size $SIZE"

if [ ! -z "$INSTRUCTIONS" ]; then
  CMD="$CMD --instructions \"$INSTRUCTIONS\""
fi

if [ ! -z "$FILENAME" ]; then
  CMD="$CMD --filename \"$FILENAME\""
fi

# Add verbose flag for better output
CMD="$CMD --verbose"

# Show summary
gum style \
  --border normal \
  --align left \
  --width 50 \
  --margin "1 2" \
  --padding "1 2" \
  "Generation Summary:
Style: $STYLE
Size: $SIZE
Description: $DESCRIPTION
Instructions: ${INSTRUCTIONS:-None}
Filename: ${FILENAME:-Auto-generated}"

# Show the command that will be executed
echo -e "\nCommand to execute:"
gum style --foreground 212 "$CMD"

# Confirm execution
if gum confirm "Generate image?"; then
  # Execute the command directly without eval
  if [ ! -z "$INSTRUCTIONS" ] && [ ! -z "$FILENAME" ]; then
    $PYTHON_CMD "$PYTHON_SCRIPT" "$DESCRIPTION" --style "$STYLE" --size "$SIZE" --instructions "$INSTRUCTIONS" --filename "$FILENAME" --verbose
  elif [ ! -z "$INSTRUCTIONS" ]; then
    $PYTHON_CMD "$PYTHON_SCRIPT" "$DESCRIPTION" --style "$STYLE" --size "$SIZE" --instructions "$INSTRUCTIONS" --verbose
  elif [ ! -z "$FILENAME" ]; then
    $PYTHON_CMD "$PYTHON_SCRIPT" "$DESCRIPTION" --style "$STYLE" --size "$SIZE" --filename "$FILENAME" --verbose
  else
    $PYTHON_CMD "$PYTHON_SCRIPT" "$DESCRIPTION" --style "$STYLE" --size "$SIZE" --verbose
  fi
else
  gum style --foreground 1 "Generation cancelled"
  exit 0
fi
