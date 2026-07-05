import os
import sys
import html
import threading
from tkinter import messagebox

try:
    import customtkinter as ctk
    from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageSequence
except ImportError as e:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Missing Dependencies", f"Please run 'pip install -r requirements.txt'\n\nError: {e}")
    sys.exit(1)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AsciiArtGeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ASCII Art Generator")
        self.geometry("980x720")
        self.resizable(False, False)
        
        self.input_files = []
        self.current_preview_index = 0
        self.frames = []
        self.is_gif = False
        self.gif_duration = 100
        
        self.font_path = None
        self.bg_color_hex = None
        self.debounce_timer = None
        self.custom_palette_colors = [(0, 0, 0), (255, 255, 255)]
        
        # Animation state
        self.animation_running = False
        self.animation_task = None
        self.current_animation_id = 0
        self.preview_animation_frames = []
        
        self.current_ascii_str = None
        self.current_ascii_lines = None
        self.current_color_lines = None
        self.current_rendered_image = None
        
        self.char_sets = {
            "Standard": "@%#*+=-:. ",
            "Detailed": "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. ",
            "Blocky": "█▓▒░ ",
            "Simple": "#+-. ",
            "Edge Detection": "/\\|-_ "
        }
        
        self.palettes = {
            "Text Only (B&W)": "None",
            "Full Color": None,
            "Adaptive (16 Colors)": 16,
            "Adaptive (8 Colors)": 8,
            "Adaptive (4 Colors)": 4,
            "Monochrome": [(0, 0, 0), (255, 255, 255)],
            "GameBoy": [(15, 56, 15), (48, 98, 48), (139, 172, 15), (155, 188, 15)],
            "Sepia": [(36, 17, 10), (105, 60, 24), (202, 154, 88), (252, 241, 206)],
            "Custom (PNG)": "Custom"
        }
        
        self.setup_vars()
        self.build_ui()
        
    def setup_vars(self):
        self.width_var = ctk.IntVar(value=100)
        self.stretch_var = ctk.DoubleVar(value=1.0)
        self.bright_var = ctk.DoubleVar(value=1.0)
        self.contrast_var = ctk.DoubleVar(value=1.0)
        
        self.dither_var = ctk.BooleanVar(value=False)
        self.transparent_var = ctk.BooleanVar(value=False)
        self.invert_var = ctk.BooleanVar(value=False)
        
        self.charset_var = ctk.StringVar(value="Standard")
        self.palette_var = ctk.StringVar(value="Text Only (B&W)")

    def build_ui(self):
        # --- Top Settings Panel ---
        settings = ctk.CTkFrame(self)
        settings.pack(fill="x", padx=10, pady=10)
        settings.columnconfigure((0,1,2,3), weight=1)
        
        def create_label_entry(parent, row, col, text, var, cmd_on_entry):
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.grid(row=row, column=col, sticky="w", padx=10, pady=(5,0))
            ctk.CTkLabel(frame, text=text).pack(side="left")
            entry = ctk.CTkEntry(frame, width=50, height=24)
            entry.pack(side="left", padx=5)
            
            def on_edit(event=None):
                val = entry.get()
                try:
                    if isinstance(var, ctk.IntVar):
                        var.set(int(val))
                    else:
                        var.set(float(val))
                    cmd_on_entry()
                except ValueError:
                    pass
                    
            entry.bind("<Return>", on_edit)
            entry.bind("<FocusOut>", on_edit)
            
            # Set initial value
            initial_val = var.get()
            entry.insert(0, str(int(initial_val)) if isinstance(var, ctk.IntVar) else f"{initial_val:.1f}")
            
            return entry
        
        # Row 0: Labels and Entries
        self.entry_w = create_label_entry(settings, 0, 0, "Output Width:", self.width_var, self.on_setting_change)
        self.entry_b = create_label_entry(settings, 0, 1, "Brightness:", self.bright_var, self.on_setting_change)
        
        ctk.CTkLabel(settings, text="Character Set").grid(row=0, column=2, sticky="w", padx=10, pady=(5,0))
        ctk.CTkLabel(settings, text="Color Palette").grid(row=0, column=3, sticky="w", padx=10, pady=(5,0))
        
        # Row 1: Main Controls
        self.slider_w = ctk.CTkSlider(settings, from_=10, to=400, variable=self.width_var, command=self.on_setting_change)
        self.slider_w.grid(row=1, column=0, sticky="ew", padx=10)
        
        self.slider_b = ctk.CTkSlider(settings, from_=0.1, to=3.0, variable=self.bright_var, command=self.on_setting_change)
        self.slider_b.grid(row=1, column=1, sticky="ew", padx=10)
        
        self.opt_char = ctk.CTkOptionMenu(settings, variable=self.charset_var, values=list(self.char_sets.keys()) + ["Custom"], command=self.on_charset_selected)
        self.opt_char.grid(row=1, column=2, sticky="ew", padx=10)
        
        self.opt_pal = ctk.CTkOptionMenu(settings, variable=self.palette_var, values=list(self.palettes.keys()), command=self.on_palette_selected)
        self.opt_pal.grid(row=1, column=3, sticky="ew", padx=10)
        
        # Row 2: Secondary Labels and Entries
        self.entry_s = create_label_entry(settings, 2, 0, "Vertical Stretch:", self.stretch_var, self.on_setting_change)
        self.entry_c = create_label_entry(settings, 2, 1, "Contrast:", self.contrast_var, self.on_setting_change)
        
        # Row 3: Secondary Controls & Custom Entries
        self.slider_s = ctk.CTkSlider(settings, from_=0.1, to=3.0, variable=self.stretch_var, command=self.on_setting_change)
        self.slider_s.grid(row=3, column=0, sticky="ew", padx=10)
        
        self.slider_c = ctk.CTkSlider(settings, from_=0.1, to=3.0, variable=self.contrast_var, command=self.on_setting_change)
        self.slider_c.grid(row=3, column=1, sticky="ew", padx=10)
        
        self.entry_custom_char = ctk.CTkEntry(settings, placeholder_text="Type custom chars...")
        self.entry_custom_char.grid(row=3, column=2, sticky="ew", padx=10)
        self.entry_custom_char.configure(state="disabled")
        self.entry_custom_char.bind("<KeyRelease>", lambda e: self.on_setting_change())
        
        self.btn_custom_pal = ctk.CTkButton(settings, text="Load Palette (.png) [1px H]", command=self.load_custom_palette)
        self.btn_custom_pal.grid(row=3, column=3, sticky="ew", padx=10)
        self.btn_custom_pal.configure(state="disabled")
        
        # Row 4: Toggles & Reset
        self.btn_reset = ctk.CTkButton(settings, text="Reset Defaults", command=self.reset_defaults, width=120, fg_color="#5c5c5c", hover_color="#474747")
        self.btn_reset.grid(row=4, column=0, sticky="w", padx=10, pady=(15,5))
        
        self.chk_dither = ctk.CTkCheckBox(settings, text="Dithering", variable=self.dither_var, command=self.on_setting_change)
        self.chk_dither.grid(row=4, column=1, sticky="w", padx=10, pady=(15,5))
        
        self.chk_trans = ctk.CTkCheckBox(settings, text="Transparent BG", variable=self.transparent_var, command=self.on_setting_change)
        self.chk_trans.grid(row=4, column=2, sticky="w", padx=10, pady=(15,5))
        
        self.chk_invert = ctk.CTkCheckBox(settings, text="Dark Theme / Invert", variable=self.invert_var, command=self.on_setting_change)
        self.chk_invert.grid(row=4, column=3, sticky="w", padx=10, pady=(15,5))
        
        # Row 5: Font Selection
        self.btn_font = ctk.CTkButton(settings, text="Select Font (.ttf)", command=self.select_font)
        self.btn_font.grid(row=5, column=0, sticky="ew", padx=10, pady=(5,10))
        
        self.lbl_font = ctk.CTkLabel(settings, text="Default Font", text_color="gray")
        self.lbl_font.grid(row=5, column=1, sticky="w", padx=10, pady=(5,10))
        
        self.btn_bg_color = ctk.CTkButton(settings, text="BG Color: Auto", command=self.select_bg_color)
        self.btn_bg_color.grid(row=5, column=2, sticky="ew", padx=10, pady=(5,10))
        
        # --- Navigation Panel ---
        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="◄ Prev", width=80, command=self.prev_preview, state="disabled")
        self.btn_prev.pack(side="left")
        
        self.lbl_nav = ctk.CTkLabel(self.nav_frame, text="No files loaded", font=("Arial", 14, "bold"))
        self.lbl_nav.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(self.nav_frame, text="Next ►", width=80, command=self.next_preview, state="disabled")
        self.btn_next.pack(side="right")
        
        # --- Split Preview ---
        self.preview_frame = ctk.CTkFrame(self, height=360)
        self.preview_frame.pack(fill="x", padx=10, pady=5)
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.columnconfigure(1, weight=1)
        self.preview_frame.pack_propagate(False)
        self.preview_frame.grid_propagate(False)
        
        self.lbl_preview_orig = ctk.CTkLabel(self.preview_frame, text="Original Image")
        self.lbl_preview_orig.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        self.lbl_preview_img = ctk.CTkLabel(self.preview_frame, text="ASCII Art Preview")
        self.lbl_preview_img.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        # --- Bottom Action Panel ---
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.pack(fill="x", pady=5)
        
        row1 = ctk.CTkFrame(bot, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        
        ctk.CTkButton(row1, text="Browse Image(s) / GIF(s)", command=self.browse_files).pack(side="left", padx=10)
        self.lbl_path = ctk.CTkLabel(row1, text="No files selected")
        self.lbl_path.pack(side="left", padx=10)
        
        self.progress_bar = ctk.CTkProgressBar(row1)
        self.progress_bar.pack(side="right", padx=10, fill="x", expand=True)
        self.progress_bar.set(0)
        
        row2 = ctk.CTkFrame(bot, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        
        self.btn_copy = ctk.CTkButton(row2, text="Copy Text", command=self.copy_to_clipboard, state="disabled")
        self.btn_copy.pack(side="left", padx=10)
        
        self.btn_save_txt = ctk.CTkButton(row2, text="Export TXT", command=self.export_txt, state="disabled")
        self.btn_save_txt.pack(side="left", padx=10)
        
        self.btn_save_html = ctk.CTkButton(row2, text="Export HTML", command=self.export_html, state="disabled")
        self.btn_save_html.pack(side="left", padx=10)
        
        self.btn_save_img = ctk.CTkButton(row2, text="Export PNG/GIF", command=self.export_img, state="disabled", fg_color="#2b8a3e", hover_color="#237032")
        self.btn_save_img.pack(side="right", padx=10)

    # --- Logic ---

    def reset_defaults(self):
        self.width_var.set(100)
        self.stretch_var.set(1.0)
        self.bright_var.set(1.0)
        self.contrast_var.set(1.0)
        
        self.palette_var.set("Text Only (B&W)")
        self.charset_var.set("Standard")
        self.dither_var.set(False)
        self.transparent_var.set(False)
        self.invert_var.set(False)
        
        self.font_path = None
        self.lbl_font.configure(text="Default Font")
        self.bg_color_hex = None
        self.btn_bg_color.configure(text="BG Color: Auto")
        self.custom_palette_colors = [(0, 0, 0), (255, 255, 255)]
        self.btn_custom_pal.configure(text="Load Palette (.png) [1px H]")
        
        self.on_charset_selected()
        self.on_palette_selected()
        self.on_setting_change()

    def on_charset_selected(self, event=None):
        if self.charset_var.get() == "Custom":
            self.entry_custom_char.configure(state="normal")
        else:
            self.entry_custom_char.configure(state="disabled")
        self.on_setting_change()

    def on_palette_selected(self, event=None):
        if self.palette_var.get() == "Custom (PNG)":
            self.btn_custom_pal.configure(state="normal")
        else:
            self.btn_custom_pal.configure(state="disabled")
        self.on_setting_change()

    def load_custom_palette(self):
        filepath = ctk.filedialog.askopenfilename(filetypes=[("PNG Image", "*.png")])
        if filepath:
            try:
                img = Image.open(filepath).convert("RGB")
                if img.height != 1:
                    messagebox.showerror("Invalid Palette", "The palette image MUST be exactly 1 pixel in height.\n\nThe width of the image determines the number of colors.")
                    return
                self.custom_palette_colors = list(img.getdata())
                self.btn_custom_pal.configure(text=f"Loaded: {len(self.custom_palette_colors)} colors")
                self.on_setting_change()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load palette:\n{e}")

    def select_font(self):
        filepath = ctk.filedialog.askopenfilename(filetypes=[("Fonts", "*.ttf *.otf")])
        if filepath:
            self.font_path = filepath
            self.lbl_font.configure(text=os.path.basename(filepath))
            self.on_setting_change()

    def select_bg_color(self):
        from tkinter import colorchooser
        color = colorchooser.askcolor(title="Choose Background Color")
        if color and color[1]:
            self.bg_color_hex = color[1]
            self.btn_bg_color.configure(text=f"BG Color: {self.bg_color_hex}")
            self.transparent_var.set(False)
            self.on_setting_change()

    def get_solid_bg_color(self):
        if self.bg_color_hex:
            h = self.bg_color_hex.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        return (0, 0, 0) if self.invert_var.get() else (255, 255, 255)

    def browse_files(self):
        filetypes = (("Images/GIF", "*.jpg *.jpeg *.png *.webp *.bmp *.gif"), ("All files", "*.*"))
        filenames = ctk.filedialog.askopenfilenames(title="Select File(s)", filetypes=filetypes)
        if filenames:
            self.input_files = list(filenames)
            self.current_preview_index = 0
            if len(self.input_files) == 1:
                self.lbl_path.configure(text=os.path.basename(self.input_files[0]))
            else:
                self.lbl_path.configure(text=f"{len(self.input_files)} files selected (Batch Mode)")
                
            self.update_navigation_ui()
            self.load_preview_file(self.input_files[self.current_preview_index])

    def update_navigation_ui(self):
        total = len(self.input_files)
        if total == 0:
            self.lbl_nav.configure(text="No files loaded")
            self.btn_prev.configure(state="disabled")
            self.btn_next.configure(state="disabled")
        else:
            curr = self.current_preview_index + 1
            fname = os.path.basename(self.input_files[self.current_preview_index])
            self.lbl_nav.configure(text=f"File {curr} of {total}: {fname}")
            
            if total > 1:
                self.btn_prev.configure(state="normal" if curr > 1 else "disabled")
                self.btn_next.configure(state="normal" if curr < total else "disabled")
            else:
                self.btn_prev.configure(state="disabled")
                self.btn_next.configure(state="disabled")

    def prev_preview(self):
        if self.current_preview_index > 0:
            self.current_preview_index -= 1
            self.update_navigation_ui()
            self.load_preview_file(self.input_files[self.current_preview_index])

    def next_preview(self):
        if self.current_preview_index < len(self.input_files) - 1:
            self.current_preview_index += 1
            self.update_navigation_ui()
            self.load_preview_file(self.input_files[self.current_preview_index])

    def load_preview_file(self, filepath):
        try:
            img = Image.open(filepath)
            if filepath.lower().endswith('.gif'):
                self.is_gif = True
                self.gif_duration = img.info.get('duration', 100)
                if self.gif_duration == 0: self.gif_duration = 100
                self.frames = []
                for frame in ImageSequence.Iterator(img):
                    self.frames.append(frame.convert("RGBA").convert("RGB"))
            else:
                self.is_gif = False
                self.frames = [img.convert("RGB")]
                
            self.generate_ascii_preview()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image:\n{e}")

    def on_setting_change(self, value=None):
        if hasattr(self, 'entry_w'):
            if self.focus_get() != self.entry_w:
                self.entry_w.delete(0, 'end')
                self.entry_w.insert(0, str(int(self.width_var.get())))
            if self.focus_get() != self.entry_s:
                self.entry_s.delete(0, 'end')
                self.entry_s.insert(0, f"{self.stretch_var.get():.1f}")
            if self.focus_get() != self.entry_b:
                self.entry_b.delete(0, 'end')
                self.entry_b.insert(0, f"{self.bright_var.get():.1f}")
            if self.focus_get() != self.entry_c:
                self.entry_c.delete(0, 'end')
                self.entry_c.insert(0, f"{self.contrast_var.get():.1f}")
            
        if not self.frames: return
        if self.debounce_timer:
            self.after_cancel(self.debounce_timer)
        self.lbl_preview_img.configure(image='', text="Processing...")
        self.debounce_timer = self.after(350, self.generate_ascii_preview)

    def get_custom_palette(self):
        return self.custom_palette_colors if self.custom_palette_colors else [(0,0,0), (255,255,255)]

    def apply_color_palette(self, image):
        pal_name = self.palette_var.get()
        palette_option = self.palettes.get(pal_name)
        
        if pal_name == "Custom (PNG)":
            palette_option = self.get_custom_palette()
        elif palette_option is None:
            return image
            
        dither_mode = Image.Dither.FLOYDSTEINBERG if self.dither_var.get() else Image.Dither.NONE
        
        if isinstance(palette_option, int):
            return image.quantize(colors=palette_option, dither=dither_mode).convert("RGB")
        elif isinstance(palette_option, list):
            pal_img = Image.new("P", (1, 1))
            flat_palette = []
            for r, g, b in palette_option: flat_palette.extend([r, g, b])
            flat_palette.extend(flat_palette[-3:] * (256 - len(palette_option)))
            pal_img.putpalette(flat_palette)
            return image.quantize(palette=pal_img, dither=dither_mode).convert("RGB")
        return image

    def process_image(self, image_raw):
        image = image_raw.copy()
        
        width = int(self.width_var.get())
        stretch = self.stretch_var.get()
        bright = self.bright_var.get()
        contrast = self.contrast_var.get()
        color_mode = self.palette_var.get() != "Text Only (B&W)"
        invert = self.invert_var.get()
        
        charset_name = self.charset_var.get()
        if charset_name == "Custom":
            chars = self.entry_custom_char.get()
            if not chars: chars = "@"
        else:
            chars = self.char_sets.get(charset_name, self.char_sets["Standard"])
        
        if bright != 1.0: image = ImageEnhance.Brightness(image).enhance(bright)
        if contrast != 1.0: image = ImageEnhance.Contrast(image).enhance(contrast)
            
        orig_width, orig_height = image.size
        new_height = max(1, int(width * (orig_height / orig_width) * 0.5 * stretch))
        image = image.resize((width, new_height))
        
        if invert and charset_name != "Edge Detection":
            chars = chars[::-1]
            
        if charset_name == "Edge Detection":
            gray_image = image.convert("L").filter(ImageFilter.FIND_EDGES)
            if invert:
                import PIL.ImageOps
                gray_image = PIL.ImageOps.invert(gray_image)
        else:
            gray_image = image.convert("L")
            
        pixels_gray = gray_image.getdata()
        
        if color_mode:
            color_image = self.apply_color_palette(image.convert("RGB"))
            pixels_color = color_image.getdata()
        else:
            pixels_color = None
            
        ascii_lines, color_lines = [], []
        char_len = len(chars)
        
        for y in range(new_height):
            l_chars, l_colors = [], []
            for x in range(width):
                idx = y * width + x
                intensity = pixels_gray[idx]
                char_idx = min(intensity * char_len // 256, char_len - 1)
                l_chars.append(chars[char_idx])
                if color_mode: l_colors.append(pixels_color[idx])
                    
            ascii_lines.append("".join(l_chars))
            if color_mode: color_lines.append(l_colors)
                
        return "\n".join(ascii_lines), ascii_lines, color_lines

    def render_ascii_image(self, ascii_lines, color_lines):
        font_size = 12
        font = None
        if self.font_path:
            try: font = ImageFont.truetype(self.font_path, font_size)
            except: pass
        if not font:
            try: font = ImageFont.truetype("consola.ttf", font_size)
            except: font = ImageFont.load_default()
                    
        dummy_img = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        
        try:
            bbox = draw.textbbox((0, 0), "M", font=font)
            char_width, line_height = max(bbox[2]-bbox[0], 7), max(bbox[3]-bbox[1], 10)
        except AttributeError:
            char_width, line_height = font.getsize("M") if hasattr(font, 'getsize') else (7, 12)
        
        max_width = max(len(line) for line in ascii_lines) * char_width
        total_height = len(ascii_lines) * (line_height + 2)
        
        invert = self.invert_var.get()
        if self.transparent_var.get():
            bg_color = (0, 0, 0, 0)
        else:
            bg_color = self.get_solid_bg_color() + (255,)
            
        default_text_color = (255, 255, 255, 255) if invert else (0, 0, 0, 255)
        
        img = Image.new('RGBA', (int(max_width + 20), int(total_height + 20)), color=bg_color)
        d = ImageDraw.Draw(img)
        
        y_text = 10
        for y, line in enumerate(ascii_lines):
            if color_lines:
                x_text = 10
                for x, char in enumerate(line):
                    if char != " ":
                        c = tuple(list(color_lines[y][x]) + [255])
                        d.text((x_text, y_text), char, font=font, fill=c)
                    x_text += char_width
            else:
                d.text((10, y_text), line, font=font, fill=default_text_color)
            y_text += line_height + 2
            
        return img

    def generate_ascii_preview(self):
        if not self.frames: return
        
        self.animation_running = False
        if self.animation_task:
            self.after_cancel(self.animation_task)
            self.animation_task = None
        self.current_animation_id += 1
        
        try:
            a_str, a_lines, c_lines = self.process_image(self.frames[0])
            self.current_ascii_str = a_str
            self.current_ascii_lines = a_lines
            self.current_color_lines = c_lines
            
            self.current_rendered_image = self.render_ascii_image(a_lines, c_lines)
            
            orig_img = self.frames[0].copy()
            orig_img.thumbnail((440, 330), Image.Resampling.LANCZOS)
            self.photo_orig = ctk.CTkImage(light_image=orig_img, dark_image=orig_img, size=orig_img.size)
            self.lbl_preview_orig.configure(image=self.photo_orig, text="")
            
            preview_img = self.current_rendered_image.copy()
            if preview_img.mode == 'RGBA':
                bg = Image.new('RGB', preview_img.size, (30, 30, 30))
                bg.paste(preview_img, mask=preview_img.split()[3])
                preview_img = bg
                
            preview_img.thumbnail((440, 330), Image.Resampling.LANCZOS)
            self.photo_ascii = ctk.CTkImage(light_image=preview_img, dark_image=preview_img, size=preview_img.size)
            self.lbl_preview_img.configure(image=self.photo_ascii, text="")
            
            self.btn_save_txt.configure(state="normal")
            self.btn_save_html.configure(state="normal")
            
            is_batch = len(self.input_files) > 1
            if is_batch:
                self.btn_save_img.configure(state="normal", text="Export All (Batch)")
                self.btn_copy.configure(state="normal")
            else:
                self.btn_save_img.configure(state="normal", text="Export Animated GIF" if self.is_gif else "Export PNG")
                self.btn_copy.configure(state="normal")
            
            if self.is_gif and len(self.frames) > 1:
                self.lbl_preview_img.configure(text="Rendering GIF preview...")
                threading.Thread(target=self.build_gif_preview, args=(self.current_animation_id,), daemon=True).start()
            
        except Exception as e:
            self.lbl_preview_img.configure(image='', text=f"Error generating preview:\n{e}")

    def build_gif_preview(self, anim_id):
        anim_frames = []
        for f in self.frames:
            if self.current_animation_id != anim_id: return
            
            _, a, c = self.process_image(f)
            r_img = self.render_ascii_image(a, c)
            
            orig_copy = f.copy()
            orig_copy.thumbnail((440, 330), Image.Resampling.LANCZOS)
            orig_ctk = ctk.CTkImage(light_image=orig_copy, dark_image=orig_copy, size=orig_copy.size)
            
            if r_img.mode == 'RGBA':
                bg = Image.new('RGB', r_img.size, (30, 30, 30))
                bg.paste(r_img, mask=r_img.split()[3])
                r_img = bg
            r_img.thumbnail((440, 330), Image.Resampling.LANCZOS)
            ascii_ctk = ctk.CTkImage(light_image=r_img, dark_image=r_img, size=r_img.size)
            
            anim_frames.append((orig_ctk, ascii_ctk))
            
        if self.current_animation_id == anim_id:
            self.preview_animation_frames = anim_frames
            self.animation_running = True
            self.after(0, lambda: self.update_animation_frame(0))

    def update_animation_frame(self, idx):
        if not self.animation_running or not self.preview_animation_frames: return
        
        orig_ctk, ascii_ctk = self.preview_animation_frames[idx]
        self.lbl_preview_orig.configure(image=orig_ctk, text="")
        self.lbl_preview_img.configure(image=ascii_ctk, text="")
        
        next_idx = (idx + 1) % len(self.preview_animation_frames)
        self.animation_task = self.after(self.gif_duration, self.update_animation_frame, next_idx)

    def copy_to_clipboard(self):
        if self.current_ascii_str:
            self.clipboard_clear()
            self.clipboard_append(self.current_ascii_str)
            self.btn_copy.configure(text="Copied!")
            self.after(2000, lambda: self.btn_copy.configure(text="Copy Text"))

    def get_html_str(self, a_lines, c_lines):
        invert = self.invert_var.get()
        if self.transparent_var.get():
            bg = "transparent"
        else:
            bg = self.bg_color_hex if self.bg_color_hex else ("#000000" if invert else "#FFFFFF")
        fg = "#FFFFFF" if invert else "#000000"
        
        html_str = f"<html><body style='background-color: {bg}; font-family: monospace; line-height: 1.0; white-space: pre;'>"
        for y, line in enumerate(a_lines):
            html_str += "<div>"
            if c_lines:
                for x, char in enumerate(line):
                    r, g, b = c_lines[y][x][:3]
                    safe_char = html.escape(char)
                    if safe_char == " ": safe_char = "&nbsp;"
                    html_str += f"<span style='color: rgb({r},{g},{b})'>{safe_char}</span>"
            else:
                safe_line = html.escape(line).replace(" ", "&nbsp;")
                html_str += f"<span style='color: {fg}'>{safe_line}</span>"
            html_str += "</div>"
        html_str += "</body></html>"
        return html_str

    def export_txt(self):
        if not self.input_files: return
        is_batch = len(self.input_files) > 1
        
        if not is_batch:
            filepath = ctk.filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
            if filepath:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(self.current_ascii_str)
        else:
            out_dir = ctk.filedialog.askdirectory(title="Select Output Directory")
            if not out_dir: return
            
            self.btn_save_txt.configure(text="Processing...", state="disabled")
            self.progress_bar.set(0)
            
            def save_batch():
                total = len(self.input_files)
                for i, fpath in enumerate(self.input_files):
                    self.after(0, lambda p=i/total: self.progress_bar.set(p))
                    base_name = os.path.basename(fpath).rsplit('.', 1)[0]
                    out_path = os.path.join(out_dir, f"{base_name}_ascii.txt")
                    try:
                        img = Image.open(fpath).convert("RGB")
                        a_str, _, _ = self.process_image(img)
                        with open(out_path, "w", encoding="utf-8") as f:
                            f.write(a_str)
                    except Exception as e:
                        print(f"Error on {fpath}: {e}")
                self.after(0, lambda: (
                    self.progress_bar.set(1.0),
                    messagebox.showinfo("Done", f"Batch TXT export complete!\nSaved to: {out_dir}"),
                    self.btn_save_txt.configure(text="Export TXT", state="normal")
                ))
            threading.Thread(target=save_batch, daemon=True).start()

    def export_html(self):
        if not self.input_files: return
        is_batch = len(self.input_files) > 1
        
        if not is_batch:
            filepath = ctk.filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML", "*.html")])
            if filepath:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(self.get_html_str(self.current_ascii_lines, self.current_color_lines))
        else:
            out_dir = ctk.filedialog.askdirectory(title="Select Output Directory")
            if not out_dir: return
            
            self.btn_save_html.configure(text="Processing...", state="disabled")
            self.progress_bar.set(0)
            
            def save_batch():
                total = len(self.input_files)
                for i, fpath in enumerate(self.input_files):
                    self.after(0, lambda p=i/total: self.progress_bar.set(p))
                    base_name = os.path.basename(fpath).rsplit('.', 1)[0]
                    out_path = os.path.join(out_dir, f"{base_name}_ascii.html")
                    try:
                        img = Image.open(fpath).convert("RGB")
                        _, a_lines, c_lines = self.process_image(img)
                        with open(out_path, "w", encoding="utf-8") as f:
                            f.write(self.get_html_str(a_lines, c_lines))
                    except Exception as e:
                        print(f"Error on {fpath}: {e}")
                self.after(0, lambda: (
                    self.progress_bar.set(1.0),
                    messagebox.showinfo("Done", f"Batch HTML export complete!\nSaved to: {out_dir}"),
                    self.btn_save_html.configure(text="Export HTML", state="normal")
                ))
            threading.Thread(target=save_batch, daemon=True).start()

    def export_img(self):
        if not self.input_files: return
        is_batch = len(self.input_files) > 1
        
        if not is_batch:
            default_ext = ".gif" if self.is_gif else (".png" if self.transparent_var.get() else ".jpg")
            filetypes = [("GIF", "*.gif")] if self.is_gif else [("Image", "*.png *.jpg")]
            filepath = ctk.filedialog.asksaveasfilename(defaultextension=default_ext, filetypes=filetypes)
            if not filepath: return
            
            self.btn_save_img.configure(text="Saving...", state="disabled")
            
            def save_single():
                if self.is_gif:
                    rendered = []
                    for f in self.frames:
                        _, a, c = self.process_image(f)
                        r_img = self.render_ascii_image(a, c)
                        if r_img.mode == 'RGBA':
                            bg = Image.new('RGB', r_img.size, self.get_solid_bg_color())
                            bg.paste(r_img, mask=r_img.split()[3])
                            r_img = bg
                        rendered.append(r_img.convert("RGB"))
                    rendered[0].save(filepath, save_all=True, append_images=rendered[1:], duration=self.gif_duration, loop=0)
                else:
                    img = self.current_rendered_image
                    if filepath.lower().endswith(('.jpg', '.jpeg')):
                        img = img.convert("RGB")
                    img.save(filepath)
                self.after(0, lambda: (
                    messagebox.showinfo("Done", "Saved successfully!"),
                    self.btn_save_img.configure(text="Export Animated GIF" if self.is_gif else "Export PNG", state="normal")
                ))
            threading.Thread(target=save_single, daemon=True).start()
            
        else:
            out_dir = ctk.filedialog.askdirectory(title="Select Output Directory")
            if not out_dir: return
            
            self.btn_save_img.configure(text="Processing Batch...", state="disabled")
            self.progress_bar.set(0)
            
            def save_batch():
                total = len(self.input_files)
                for i, fpath in enumerate(self.input_files):
                    self.after(0, lambda p=i/total: self.progress_bar.set(p))
                    base_name = os.path.basename(fpath).rsplit('.', 1)[0]
                    
                    try:
                        img = Image.open(fpath)
                        if fpath.lower().endswith('.gif'):
                            out_path = os.path.join(out_dir, f"{base_name}_ascii.gif")
                            dur = img.info.get('duration', 100)
                            if dur == 0: dur = 100
                            rendered = []
                            for frame in ImageSequence.Iterator(img):
                                f_rgb = frame.convert("RGBA").convert("RGB")
                                _, a, c = self.process_image(f_rgb)
                                r_img = self.render_ascii_image(a, c)
                                if r_img.mode == 'RGBA':
                                    bg = Image.new('RGB', r_img.size, self.get_solid_bg_color())
                                    bg.paste(r_img, mask=r_img.split()[3])
                                    r_img = bg
                                rendered.append(r_img.convert("RGB"))
                            if rendered:
                                rendered[0].save(out_path, save_all=True, append_images=rendered[1:], duration=dur, loop=0)
                        else:
                            out_path = os.path.join(out_dir, f"{base_name}_ascii.png")
                            f_rgb = img.convert("RGB")
                            _, a, c = self.process_image(f_rgb)
                            r_img = self.render_ascii_image(a, c)
                            r_img.save(out_path)
                    except Exception as e:
                        print(f"Error on {fpath}: {e}")
                        
                self.after(0, lambda: (
                    self.progress_bar.set(1.0),
                    messagebox.showinfo("Done", f"Batch export complete!\nSaved to: {out_dir}"),
                    self.btn_save_img.configure(text="Export All (Batch)", state="normal")
                ))
            threading.Thread(target=save_batch, daemon=True).start()

if __name__ == "__main__":
    app = AsciiArtGeneratorApp()
    app.mainloop()
