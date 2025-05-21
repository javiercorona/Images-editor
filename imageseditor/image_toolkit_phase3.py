import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
import json
from datetime import datetime

class ImageToolkitExtended(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Toolkit Extended")
        self.geometry("1800x1400")
        self.minsize(1600, 1000)

        # Core image state
        self.folder = None
        self.orig_img = None      # Original loaded image (cv2)
        self.current_img = None   # Current working image (cv2)
        self.filename = None       # Current filename

        # History for undo/redo
        self.history = []
        self.history_index = -1

        # Crop state
        self.crop_start = None
        self.crop_rect = None
        self.crop_box_id = None

        # Annotation state
        self.mode = None  # 'pen', 'eraser', 'text'
        self.brush_color = (255, 0, 0)  # default red in BGR
        self.brush_size = 5
        self.last_pt = None

        # Watermark state
        self.wm_text = "Watermark"
        self.wm_color = (255, 255, 255)
        self.wm_pos = (10, 10)
        self.wm_font_size = 30
        self.wm_opacity = 0.7

        # Settings
        self.settings = {
            'recent_folders': [],
            'default_save_format': 'png'
        }
        self.load_settings()

        self.create_ui()
        self.setup_shortcuts()

    def create_ui(self):
        # Configure style
        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabelFrame', background='#f0f0f0')
        style.configure('TButton', padding=3)
        style.configure('Title.TLabel', font=('Helvetica', 10, 'bold'))

        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Left control panel
        left = ttk.Frame(main_frame, width=300)
        left.pack(side="left", fill="y", padx=5, pady=5)

        # — Browse & file list —
        file_frame = ttk.LabelFrame(left, text="Files")
        file_frame.pack(fill="x", pady=5)

        ttk.Button(file_frame, text="Browse Folder…", command=self.choose_folder).pack(fill="x", pady=2)
        
        # Recent folders dropdown
        self.recent_folders_var = tk.StringVar()
        recent_menu = ttk.OptionMenu(file_frame, self.recent_folders_var, "", *self.settings['recent_folders'], 
                                   command=self.load_recent_folder)
        recent_menu.pack(fill="x", pady=2)
        
        # File list with scrollbar
        file_list_frame = ttk.Frame(file_frame)
        file_list_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(file_list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.file_list = tk.Listbox(file_list_frame, height=10, yscrollcommand=scrollbar.set)
        self.file_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.file_list.yview)
        
        self.file_list.bind('<<ListboxSelect>>', self.on_select)
        self.file_list.bind('<Double-1>', lambda e: self.on_select(e))

        # — Filters & adjustments —
        ff = ttk.LabelFrame(left, text="Filters & Adjustments")
        ff.pack(fill="x", pady=5)
        
        # Basic filters
        filter_frame = ttk.Frame(ff)
        filter_frame.pack(fill="x", pady=2)
        
        self.gray_var = tk.BooleanVar()
        self.sepia_var = tk.BooleanVar()
        self.inv_var = tk.BooleanVar()
        self.emboss_var = tk.BooleanVar()
        
        ttk.Checkbutton(filter_frame, text="Grayscale", variable=self.gray_var, command=self.apply_pipeline).pack(side="left", padx=2)
        ttk.Checkbutton(filter_frame, text="Sepia", variable=self.sepia_var, command=self.apply_pipeline).pack(side="left", padx=2)
        ttk.Checkbutton(filter_frame, text="Invert", variable=self.inv_var, command=self.apply_pipeline).pack(side="left", padx=2)
        ttk.Checkbutton(filter_frame, text="Emboss", variable=self.emboss_var, command=self.apply_pipeline).pack(side="left", padx=2)

        # Sliders for adjustments
        for lbl, var_name, mn, mx, res, default in [
            ("Blur", "blur", 0, 15, 1, 0),
            ("Sharpen", "sharpen", 0, 5, 1, 0),
            ("Brightness", "brightness", 0.2, 2, 0.01, 1),
            ("Contrast", "contrast", 0.2, 3, 0.01, 1),
            ("Cartoon BS", "cartoon_bs", 3, 51, 2, 7),
            ("Cartoon C", "cartoon_c", 1, 50, 1, 9),
        ]:
            frame = ttk.Frame(ff)
            frame.pack(fill="x", pady=2)
            
            ttk.Label(frame, text=lbl, width=10).pack(side="left")
            var = tk.DoubleVar(value=default)
            setattr(self, var_name + "_var", var)
            
            scale = ttk.Scale(frame, from_=mn, to=mx, orient="horizontal", 
                             variable=var, command=lambda e, v=var_name: self.slider_changed(v))
            scale.pack(side="left", fill="x", expand=True, padx=5)
            
            value_label = ttk.Label(frame, text=str(default), width=4)
            value_label.pack(side="left")
            setattr(self, var_name + "_label", value_label)

        # — Annotation & Crop & Resize —
        af = ttk.LabelFrame(left, text="Tools")
        af.pack(fill="x", pady=5)
        
        # Tool buttons
        tool_frame = ttk.Frame(af)
        tool_frame.pack(fill="x", pady=2)
        
        self.tool_btns = {}
        for txt, mode in [("Pen", "pen"), ("Eraser", "eraser"), ("Text", "text"), 
                         ("Crop", "crop"), ("Move", "move")]:
            btn = ttk.Button(tool_frame, text=txt, command=lambda m=mode: self.set_mode(m))
            btn.pack(side="left", fill="x", expand=True, padx=2)
            self.tool_btns[mode] = btn
        
        # Color and size controls
        color_frame = ttk.Frame(af)
        color_frame.pack(fill="x", pady=2)
        
        ttk.Button(color_frame, text="Color", command=self.choose_color).pack(side="left", padx=2)
        self.color_preview = tk.Canvas(color_frame, width=30, height=20, bg="#ff0000")
        self.color_preview.pack(side="left", padx=2)
        
        ttk.Label(color_frame, text="Size:").pack(side="left", padx=2)
        self.size_scale = ttk.Scale(color_frame, from_=1, to=50, orient="horizontal", 
                                  command=self.update_brush_size)
        self.size_scale.set(self.brush_size)
        self.size_scale.pack(side="left", fill="x", expand=True, padx=2)
        self.size_label = ttk.Label(color_frame, text=str(self.brush_size))
        self.size_label.pack(side="left", padx=2)

        # Action buttons
        action_frame = ttk.Frame(af)
        action_frame.pack(fill="x", pady=2)
        
        ttk.Button(action_frame, text="Apply Crop", command=self.apply_crop).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(action_frame, text="Canvas Resize", command=self.canvas_resize).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(action_frame, text="Reset", command=self.reset_image).pack(side="left", fill="x", expand=True, padx=2)

        # — Transform & History & Save —
        tf = ttk.LabelFrame(left, text="Transform / History")
        tf.pack(fill="x", pady=5)
        
        # Transform buttons
        transform_frame = ttk.Frame(tf)
        transform_frame.pack(fill="x", pady=2)
        
        for txt, op in [("Rot ↺", cv2.ROTATE_90_COUNTERCLOCKWISE),
                        ("Rot ↻", cv2.ROTATE_90_CLOCKWISE),
                        ("Flip H", 'hflip'), ("Flip V", 'vflip')]:
            ttk.Button(transform_frame, text=txt, command=lambda o=op: self.transform(o))\
                .pack(side="left", fill="x", expand=True, padx=2)

        # History buttons
        history_frame = ttk.Frame(tf)
        history_frame.pack(fill="x", pady=2)
        
        ttk.Button(history_frame, text="Undo", command=self.undo).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(history_frame, text="Redo", command=self.redo).pack(side="left", fill="x", expand=True, padx=2)
        
        # Save button
        save_frame = ttk.Frame(tf)
        save_frame.pack(fill="x", pady=2)
        
        ttk.Button(save_frame, text="Save", command=self.save_image).pack(side="left", fill="x", expand=True, padx=2)
        ttk.Button(save_frame, text="Save As...", command=self.save_image_as).pack(side="left", fill="x", expand=True, padx=2)

        # — Watermark —
        wm = ttk.LabelFrame(left, text="Watermark / Overlay")
        wm.pack(fill="x", pady=5)
        
        ttk.Button(wm, text="Set Text", command=self.prompt_watermark).pack(fill="x", pady=1)
        
        wm_color_frame = ttk.Frame(wm)
        wm_color_frame.pack(fill="x", pady=1)
        ttk.Button(wm_color_frame, text="Set Color", command=self.prompt_wm_color).pack(side="left", padx=2)
        self.wm_color_preview = tk.Canvas(wm_color_frame, width=30, height=20, bg="#ffffff")
        self.wm_color_preview.pack(side="left", padx=2)
        
        ttk.Label(wm, text="Font Size:").pack(anchor="w")
        self.wm_size_scale = ttk.Scale(wm, from_=10, to=100, orient="horizontal", 
                                      command=self.update_wm_size)
        self.wm_size_scale.set(self.wm_font_size)
        self.wm_size_scale.pack(fill="x", pady=1)
        
        ttk.Label(wm, text="Opacity:").pack(anchor="w")
        self.wm_opacity_scale = ttk.Scale(wm, from_=0.1, to=1.0, orient="horizontal", 
                                        command=self.update_wm_opacity)
        self.wm_opacity_scale.set(self.wm_opacity)
        self.wm_opacity_scale.pack(fill="x", pady=1)
        
        ttk.Button(wm, text="Apply WM", command=self.apply_watermark).pack(fill="x", pady=1)

        # — Canvas —
        self.canvas_frame = ttk.Frame(main_frame)
        self.canvas_frame.pack(side="right", fill="both", expand=True)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="black", cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        
        # Status bar
        self.status_bar = ttk.Label(self.canvas_frame, text="Ready", relief="sunken")
        self.status_bar.pack(fill="x", side="bottom")
        
        # Canvas bindings
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Motion>", self.update_status_bar)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

    def setup_shortcuts(self):
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-s>", lambda e: self.save_image())
        self.bind("<Control-o>", lambda e: self.choose_folder())
        self.bind("<Control-r>", lambda e: self.reset_image())

    def load_settings(self):
        try:
            with open('image_toolkit_settings.json', 'r') as f:
                self.settings.update(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_settings(self):
        with open('image_toolkit_settings.json', 'w') as f:
            json.dump(self.settings, f)

    def add_recent_folder(self, folder):
        if folder in self.settings['recent_folders']:
            self.settings['recent_folders'].remove(folder)
        self.settings['recent_folders'].insert(0, folder)
        self.settings['recent_folders'] = self.settings['recent_folders'][:10]  # Keep only 10 most recent
        self.save_settings()

    def load_recent_folder(self, folder):
        if not folder: return
        self.folder = folder
        self.file_list.delete(0, tk.END)
        try:
            for f in sorted(os.listdir(folder)):
                if f.lower().endswith(('.png','.jpg','.jpeg','.bmp','.tiff','.webp')):
                    self.file_list.insert(tk.END, f)
        except PermissionError:
            messagebox.showerror("Error", f"Cannot access folder: {folder}")

    # --- Folder & Loading ---
    def choose_folder(self):
        fld = filedialog.askdirectory()
        if not fld: return
        self.folder = fld
        self.add_recent_folder(fld)
        self.recent_folders_var.set(fld)
        self.load_recent_folder(fld)

    def on_select(self, evt):
        sel = self.file_list.curselection()
        if not sel: return
        self.filename = self.file_list.get(sel[0])
        path = os.path.join(self.folder, self.filename)
        try:
            img = cv2.imread(path)
            if img is None:
                return messagebox.showerror("Error", "Cannot load image (unsupported format?)")
            self.orig_img = img
            self.current_img = img.copy()
            self.history.clear()
            self.history_index = -1
            self.push_history(self.orig_img)
            self.apply_pipeline()
            self.update_status_bar()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    # --- Pipeline ---
    def slider_changed(self, var_name):
        # Update the label showing the current value
        value = getattr(self, f"{var_name}_var").get()
        getattr(self, f"{var_name}_label").config(text=f"{value:.2f}" if isinstance(value, float) else str(value))
        self.apply_pipeline()

    def apply_pipeline(self):
        if self.orig_img is None: return
        img = self.orig_img.copy()

        # grayscale / sepia / invert
        if self.gray_var.get():
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        if self.sepia_var.get():
            K = np.array([[0.272, 0.534, 0.131], [0.349, 0.686, 0.168], [0.393, 0.769, 0.189]])
            img = cv2.transform(img, K)
        if self.inv_var.get():
            img = cv2.bitwise_not(img)

        # blur
        b = self.blur_var.get()
        if b > 0: 
            img = cv2.GaussianBlur(img, (0, 0), b)

        # sharpen
        s = self.sharpen_var.get()
        if s > 0:
            kern = np.array([[-1, -1, -1], [-1, 9 + s, -1], [-1, -1, -1]])
            img = cv2.filter2D(img, -1, kern)

        # cartoon: ensure odd blockSize ≥3
        bs = int(self.cartoon_bs_var.get())
        block = bs if bs % 2 == 1 and bs > 1 else bs + 1 if (bs + 1) % 2 == 1 else 3
        c = int(self.cartoon_c_var.get())
        
        # Only apply cartoon effect if either parameter is non-default
        if bs != 7 or c != 9:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                         cv2.THRESH_BINARY, block, c)
            color = cv2.bilateralFilter(img, block, 200, 200)
            img = cv2.bitwise_and(color, color, mask=edges)

        # emboss
        if self.emboss_var.get():
            k = np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]])
            img = cv2.filter2D(img, -1, k)

        # brightness / contrast
        alpha = self.contrast_var.get()
        beta = int((self.brightness_var.get() - 1) * 255)
        img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

        self.current_img = img
        self.push_history(img)
        self.display(img)

    # --- Transform ---
    def transform(self, op):
        if self.current_img is None: return
        img = self.current_img.copy()
        if op == 'hflip': 
            img = cv2.flip(img, 1)
        elif op == 'vflip': 
            img = cv2.flip(img, 0)
        else: 
            img = cv2.rotate(img, op)
        self.orig_img = img
        self.push_history(img)
        self.apply_pipeline()

    # --- Watermark ---
    def prompt_watermark(self):
        txt = simpledialog.askstring("Watermark", "Enter watermark text:", initialvalue=self.wm_text)
        if txt is not None:
            self.wm_text = txt

    def prompt_wm_color(self):
        c = colorchooser.askcolor()[0]
        if c: 
            self.wm_color = tuple(map(int, c[::-1]))
            self.wm_color_preview.config(bg=colorchooser.askcolor()[1])

    def update_wm_size(self, val):
        self.wm_font_size = int(float(val))

    def update_wm_opacity(self, val):
        self.wm_opacity = float(val)

    def apply_watermark(self):
        if not self.current_img or not self.wm_text: return
        
        # Convert to PIL for better text handling
        img_pil = Image.fromarray(cv2.cvtColor(self.current_img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        try:
            font = ImageFont.truetype("arial.ttf", self.wm_font_size)
        except:
            font = ImageFont.load_default()
        
        # Calculate text size and position
        text_width, text_height = draw.textsize(self.wm_text, font=font)
        img_width, img_height = img_pil.size
        x = img_width - text_width - 20  # 20px from right
        y = img_height - text_height - 20  # 20px from bottom
        
        # Draw text with opacity
        overlay = Image.new('RGBA', img_pil.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.text((x, y), self.wm_text, font=font, 
                         fill=(*self.wm_color, int(self.wm_opacity * 255)))
        img_pil = Image.alpha_composite(img_pil.convert('RGBA'), overlay)
        
        # Convert back to OpenCV format
        img = cv2.cvtColor(np.array(img_pil.convert('RGB')), cv2.COLOR_RGB2BGR)
        self.orig_img = img
        self.push_history(img)
        self.apply_pipeline()

    # --- Annotation & Crop ---
    def set_mode(self, m):
        self.mode = m
        # Update button states
        for mode, btn in self.tool_btns.items():
            if mode == m:
                btn.state(['pressed', 'disabled'])
            else:
                btn.state(['!pressed', '!disabled'])
        
        # Update cursor
        if m == 'pen':
            self.canvas.config(cursor="pencil")
        elif m == 'eraser':
            self.canvas.config(cursor="circle")
        elif m == 'text':
            self.canvas.config(cursor="xterm")
        elif m == 'crop':
            self.canvas.config(cursor="cross")
        elif m == 'move':
            self.canvas.config(cursor="fleur")
        
        self.status_bar.config(text=f"Mode: {m.capitalize()}")

    def choose_color(self):
        c = colorchooser.askcolor()[0]
        if c: 
            self.brush_color = (int(c[2]), int(c[1]), int(c[0]))
            self.color_preview.config(bg=colorchooser.askcolor()[1])

    def update_brush_size(self, v):
        self.brush_size = int(float(v))
        self.size_label.config(text=str(self.brush_size))

    def on_mouse_down(self, ev):
        if self.current_img is None: return
        
        if self.mode in ('pen', 'eraser'):
            self.last_pt = (ev.x, ev.y)
            self.on_mouse_drag(ev)  # Draw initial point
            
        elif self.mode == 'text':
            txt = simpledialog.askstring("Text", "Enter text:")
            if txt:
                ix, iy = self.canvas_to_image(ev.x, ev.y)
                cv2.putText(self.current_img, txt, (ix, iy), cv2.FONT_HERSHEY_SIMPLEX,
                            self.brush_size / 20, self.brush_color, 2)
                self.push_history(self.current_img)
                self.display(self.current_img)
                
        elif self.mode == 'crop':
            self.crop_start = (ev.x, ev.y)
            if self.crop_box_id: 
                self.canvas.delete(self.crop_box_id)
                
        elif self.mode == 'move':
            self.last_pt = (ev.x, ev.y)

    def on_mouse_drag(self, ev):
        if self.current_img is None: return
        
        if self.mode in ('pen', 'eraser') and hasattr(self, 'last_pt'):
            x0, y0 = self.last_pt
            x1, y1 = ev.x, ev.y
            ix0, iy0 = self.canvas_to_image(x0, y0)
            ix1, iy1 = self.canvas_to_image(x1, y1)
            col = (255, 255, 255) if self.mode == 'eraser' else self.brush_color
            cv2.line(self.current_img, (ix0, iy0), (ix1, iy1), col, self.brush_size)
            self.last_pt = (x1, y1)
            self.display(self.current_img)
            
        elif self.mode == 'crop' and self.crop_start:
            x0, y0 = self.crop_start
            if self.crop_box_id: 
                self.canvas.delete(self.crop_box_id)
            self.crop_box_id = self.canvas.create_rectangle(x0, y0, ev.x, ev.y, 
                                                          outline='yellow', dash=(5,5))
            
        elif self.mode == 'move' and hasattr(self, 'last_pt'):
            # Pan the image
            dx = ev.x - self.last_pt[0]
            dy = ev.y - self.last_pt[1]
            self.last_pt = (ev.x, ev.y)
            
            # Adjust the canvas scroll region
            self.canvas.xview_scroll(-dx, "units")
            self.canvas.yview_scroll(-dy, "units")

    def on_mouse_up(self, ev):
        if self.mode in ('pen', 'eraser'):
            self.push_history(self.current_img)
        elif self.mode == 'crop' and self.crop_start:
            x0, y0 = self.crop_start
            x1, y1 = ev.x, ev.y
            self.crop_rect = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
            self.status_bar.config(text="Crop area selected. Click 'Apply Crop' to confirm.")
        self.last_pt = None

    def canvas_to_image(self, x, y):
        if self.current_img is None: return (0, 0)
        
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        ih, iw = self.current_img.shape[:2]
        
        # Calculate scale and offset
        scale = min(cw / iw, ch / ih)
        offx = (cw - iw * scale) / 2
        offy = (ch - ih * scale) / 2
        
        # Convert canvas coordinates to image coordinates
        ix = int((x - offx) / scale)
        iy = int((y - offy) / scale)
        
        # Clamp to image dimensions
        return (max(0, min(iw - 1, ix)), max(0, min(ih - 1, iy)))

    def apply_crop(self):
        if not self.crop_rect or self.orig_img is None: return
        
        x0, y0, x1, y1 = self.crop_rect
        ix0, iy0 = self.canvas_to_image(x0, y0)
        ix1, iy1 = self.canvas_to_image(x1, y1)
        
        if ix1 <= ix0 or iy1 <= iy0:
            return messagebox.showerror("Error", "Invalid crop area")
            
        cropped = self.orig_img[iy0:iy1, ix0:ix1]
        self.orig_img = cropped
        self.push_history(cropped)
        self.apply_pipeline()
        
        if self.crop_box_id: 
            self.canvas.delete(self.crop_box_id)
            self.crop_box_id = None
            self.crop_rect = None

    def canvas_resize(self):
        if self.orig_img is None: return
        
        ih, iw = self.orig_img.shape[:2]
        new_w = simpledialog.askinteger("Resize", "New width:", minvalue=1, initialvalue=iw)
        if not new_w: return
        
        new_h = simpledialog.askinteger("Resize", "New height:", minvalue=1, initialvalue=ih)
        if not new_h: return
        
        # Create new canvas with specified dimensions
        canvas = np.zeros((new_h, new_w, 3), dtype=np.uint8)
        
        # Calculate position to paste original image (centered)
        ox = (new_w - iw) // 2
        oy = (new_h - ih) // 2
        
        # Paste original image onto canvas
        canvas[oy:oy + ih, ox:ox + iw] = self.orig_img
        
        self.orig_img = canvas
        self.push_history(canvas)
        self.apply_pipeline()

    def reset_image(self):
        if self.orig_img is None: return
        
        # Reset all filters and adjustments
        self.gray_var.set(False)
        self.sepia_var.set(False)
        self.inv_var.set(False)
        self.emboss_var.set(False)
        
        for var_name in ['blur', 'sharpen', 'brightness', 'contrast', 'cartoon_bs', 'cartoon_c']:
            default = 0 if var_name in ['blur', 'sharpen'] else 1 if var_name in ['brightness', 'contrast'] else 7 if var_name == 'cartoon_bs' else 9
            getattr(self, f"{var_name}_var").set(default)
            getattr(self, f"{var_name}_label").config(text=str(default))
        
        # Reset to original image
        self.current_img = self.orig_img.copy()
        self.push_history(self.orig_img)
        self.display(self.orig_img)

    # --- History ---
    def push_history(self, img):
        self.history = self.history[:self.history_index + 1]
        self.history.append(img.copy())
        self.history_index = len(self.history) - 1
        
        # Limit history size
        if len(self.history) > 20:
            self.history.pop(0)
            self.history_index -= 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.orig_img = self.history[self.history_index].copy()
            self.apply_pipeline()

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.orig_img = self.history[self.history_index].copy()
            self.apply_pipeline()

    # --- Display & Save ---
    def on_canvas_resize(self, event):
        if hasattr(self, 'current_img') and self.current_img is not None:
            self.display(self.current_img)

    def display(self, img):
        if img is None: return
        
        ih, iw = img.shape[:2]
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        
        # Calculate scale to fit image in canvas while maintaining aspect ratio
        scale = min(cw / iw, ch / ih)
        new_w, new_h = int(iw * scale), int(ih * scale)
        
        # Resize image
        disp = cv2.resize(img, (new_w, new_h))
        disp = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(Image.fromarray(disp))
        
        # Clear canvas and display image centered
        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, image=self.photo, anchor='center')

    def update_status_bar(self, event=None):
        if self.current_img is None: 
            self.status_bar.config(text="No image loaded")
            return
            
        if event:
            # Show mouse position and image coordinates
            x, y = event.x, event.y
            ix, iy = self.canvas_to_image(x, y)
            ih, iw = self.current_img.shape[:2]
            self.status_bar.config(text=f"Canvas: ({x},{y}) | Image: ({ix},{iy}) | Size: {iw}x{ih}")
        else:
            # Show basic image info
            ih, iw = self.current_img.shape[:2]
            self.status_bar.config(text=f"Image: {self.filename or 'Untitled'} | Size: {iw}x{ih}")

    def save_image(self):
        if self.orig_img is None: return
        
        if self.filename:
            # Save to original filename with timestamp
            base, ext = os.path.splitext(self.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{base}_{timestamp}{ext}"
            path = os.path.join(self.folder, new_filename)
            cv2.imwrite(path, self.orig_img)
            messagebox.showinfo("Saved", f"Image saved as {new_filename}")
        else:
            self.save_image_as()

    def save_image_as(self):
        if self.orig_img is None: return
        
        default_ext = self.settings.get('default_save_format', 'png')
        filetypes = [
            ("PNG", "*.png"),
            ("JPEG", "*.jpg;*.jpeg"),
            ("Bitmap", "*.bmp"),
            ("TIFF", "*.tiff"),
            ("WebP", "*.webp"),
            ("All files", "*.*")
        ]
        
        p = filedialog.asksaveasfilename(
            defaultextension=f".{default_ext}",
            filetypes=filetypes,
            initialfile=self.filename or f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{default_ext}"
        )
        
        if not p: return
        
        try:
            cv2.imwrite(p, self.orig_img)
            messagebox.showinfo("Saved", f"Image saved to {p}")
            
            # Update filename and folder if saving to a new location
            self.filename = os.path.basename(p)
            self.folder = os.path.dirname(p)
            self.add_recent_folder(self.folder)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {str(e)}")

if __name__ == "__main__":
    app = ImageToolkitExtended()
    app.mainloop()