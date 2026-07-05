# ASCII Art Generator

A modern, feature-rich desktop application built with Python and `customtkinter` that seamlessly converts images and animated GIFs into customizable ASCII art.

## Features

- **🎨 Modern User Interface:** A sleek, single-window dark-mode GUI built for ease of use and maximum efficiency.
- **🎞️ Full GIF Support:** Converts animated GIFs into fully animated ASCII GIFs frame-by-frame, perfectly preserving duration and loops.
- **⚡ Smart Batch Processing:** Select multiple images or GIFs at once. The app will let you preview the first file, and then process the entire queue in the background with a single click.
- **🔤 Endless Customization:** 
  - Adjust Output Width, Brightness, Contrast, and Vertical Stretch with precision sliders or direct keyboard input.
  - Choose between multiple character sets (Standard, Complex, Blocks, Binary) or create your own.
  - Load custom `.ttf` fonts for rendering.
- **🖌️ Color Palettes & Backgrounds:**
  - Export with full RGB colors, text-only monochrome, or specialized palettes like *GameBoy* and *Sepia*.
  - Support for **Custom PNG Palettes** (load a 1px height PNG file to apply custom colors).
  - Customizable solid background colors or transparent backgrounds.
- **💾 Multiple Export Formats:** Export your creations as `.png` (images), `.gif` (animations), `.txt` (raw text), or `.html` (colored text for web).

## Requirements

If you are running from source, install the required dependencies using:

```bash
pip install -r requirements.txt
```

*Note: The application uses `Pillow`, `customtkinter`, and `numpy`.*

## Running the Application

To launch the GUI, simply run:

```bash
python main.py
```

## Building a Standalone Executable

You can easily package the application into a standalone `.exe` file that requires no Python installation for the end user.

1. Ensure you have `pyinstaller` installed:
   ```bash
   pip install pyinstaller
   ```
2. Run the included build script:
   ```bash
   python build.py
   ```
3. Your compiled executable will be waiting in the `dist` folder.

## How to use Custom PNG Palettes

1. Select **"Custom (PNG)"** from the Color Palette dropdown.
2. Click **"Load Palette (.png) [1px H]"**.
3. Select a PNG file that is exactly **1 pixel in height**. The width of the image will determine how many colors are in your palette. The app will automatically map image luminosity to your palette colors!
