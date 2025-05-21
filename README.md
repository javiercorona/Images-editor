
# Image Toolkit Extended

A powerful Python-based image editing toolkit with a graphical user interface built on Tkinter and OpenCV. Allows you to browse folders of images, apply filters & adjustments, annotate, crop, resize, transform, and save your edited images.

## Features

* **Browse & Load**: Select a folder to view and load images supported by OpenCV (`.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.webp`).
* **Filters & Adjustments**:

  * Grayscale, Sepia, Invert, Emboss toggle filters
  * Blur, Sharpen, Brightness, Contrast adjustments
  * Cartoon effect with configurable block size and edge threshold
* **Annotation Tools**:

  * Pen: draw freehand on the image
  * Eraser: remove annotations
  * Text: add text overlays
  * Color picker and brush size slider
* **Crop & Resize**:

  * Interactive crop selection on canvas
  * Canvas resize with custom width/height
* **Transform & History**:

  * Rotate (↺, ↻), Flip (horizontal, vertical)
  * Undo/Redo history (up to 20 steps)
* **Save**:

  * Save over original with timestamp suffix
  * Save As... to choose format and location

## Requirements

* Python 3.7 or later
* OpenCV (`opencv-python`)
* Pillow (`Pillow`)

Install dependencies via pip:

```bash
pip install opencv-python Pillow
```

## Installation

1. Clone or download this repository.
2. Ensure you have the required Python dependencies installed.
3. Navigate to the project directory:

   ```bash
   cd path/to/imageseditor
   ```

## Usage

Run the application:

```bash
python image_toolkit_phase3.py
```

1. **Browse Folder**: Click the "Browse Folder…" button to select a directory. Use the dropdown to switch between recently used folders.
2. **Load Image**: Click on a filename in the list to load and display it.
3. **Apply Filters**: Check or uncheck filter checkboxes and drag the sliders to adjust values. Changes are applied in real time.
4. **Annotate**:

   * Select a tool (Pen, Eraser, Text, Crop, Move).
   * Choose a brush color and size for pen/eraser.
   * Draw directly on the image or add text overlays.
5. **Crop**:

   * Select the Crop tool and drag on the image to define a rectangle.
   * Click "Apply Crop" to crop to the selected area.
6. **Resize Canvas**: Click "Canvas Resize" to input new width and height. Original image is centered on new canvas.
7. **Transform**: Use the Rotate and Flip buttons to rotate or mirror the image.
8. **History**: Undo/Redo your edits up to 20 steps using the corresponding buttons or `Ctrl+Z` / `Ctrl+Y` shortcuts.
9. **Save**:

   * Click "Save" to write a new file in the same folder with a timestamp.
   * Click "Save As..." to choose a custom location and format.

## Shortcuts

* **Ctrl+O**: Open folder
* **Ctrl+S**: Save image
* **Ctrl+Z**: Undo
* **Ctrl+Y**: Redo
* **Ctrl+R**: Reset filters

## Configuration

A settings file `image_toolkit_settings.json` is created in the working directory to store:

* List of recent folders (up to 10)
* Default save format (e.g., `png`)

## Troubleshooting

* **Unsupported Image**: Ensure files are valid images supported by OpenCV.
* **Odd Cartoon Parameters**: Cartoon block size must be odd and ≥ 3; script adjusts automatically.
* **Missing Fonts**: If `arial.ttf` is unavailable on your system, fallback to default PIL font is used for watermark/text.

---

Enjoy editing with Image Toolkit Extended! Feel free to contribute improvements or report issues.
