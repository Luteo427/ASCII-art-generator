import os
import PyInstaller.__main__
import customtkinter

# Find where customtkinter is installed so we can bundle its themes and fonts
customtkinter_path = os.path.dirname(customtkinter.__file__)

print("Building ASCII Art Generator Pro...")
print(f"Bundling CustomTkinter from: {customtkinter_path}")

PyInstaller.__main__.run([
    'main.py',
    '--noconfirm',
    '--windowed',
    '--onefile',
    '--name=ASCII_Art_Generator',
    f'--add-data={customtkinter_path};customtkinter/'
])

print("Build complete! Check the 'dist' folder for your .exe file.")
