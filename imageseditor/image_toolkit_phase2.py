import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk

class ImageToolkit(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Toolkit Phase 3")
        self.folder = None
        self.orig_img = None   # keep original BGR image
        self.current_img = None

        # --- Left panel: folder picker + file list ---
        left = tk.Frame(self)
        left.pack(side="left", fill="y", padx=5, pady=5)

        tk.Button(left, text="Browse Folder…", command=self.choose_folder).pack(fill="x")
        self.image_list = tk.Listbox(left, height=20)
        self.image_list.pack(fill="both", expand=True, pady=5)
        self.image_list.bind('<<ListboxSelect>>', self.on_list_select)

        # --- Middle panel: controls ---
        ctrl = tk.Frame(self)
        ctrl.pack(side="left", fill="y", padx=5, pady=5)

        # Pre-filters
        self.gray_var  = tk.BooleanVar()
        self.sepia_var = tk.BooleanVar()
        ttk.Checkbutton(ctrl, text="Grayscale", variable=self.gray_var, command=self.update_preview).pack(anchor="w")
        ttk.Checkbutton(ctrl, text="Sepia",    variable=self.sepia_var, command=self.update_preview).pack(anchor="w")

        # Retouch sliders
        self.brightness = tk.DoubleVar(value=1.0)
        self.contrast   = tk.DoubleVar(value=1.0)
        ttk.Label(ctrl, text="Brightness").pack(anchor="w")
        ttk.Scale(ctrl, from_=0.2, to=2.0, variable=self.brightness, command=lambda e: self.update_preview()).pack(fill="x")
        ttk.Label(ctrl, text="Contrast").pack(anchor="w")
        ttk.Scale(ctrl, from_=0.2, to=3.0, variable=self.contrast,   command=lambda e: self.update_preview()).pack(fill="x")

        # Cartoon parameters
        self.block_size  = tk.IntVar(value=9)
        self.c_param     = tk.IntVar(value=2)
        self.k_size      = tk.IntVar(value=5)
        self.color_sigma = tk.IntVar(value=200)
        self.space_sigma = tk.IntVar(value=200)
        ttk.Label(ctrl, text="Cartoon: Block Size").pack(anchor="w")
        ttk.Scale(ctrl, from_=3, to=31,    variable=self.block_size,  command=lambda e: self.update_preview()).pack(fill="x")
        ttk.Label(ctrl, text="Cartoon: C").pack(anchor="w")
        ttk.Scale(ctrl, from_=1, to=50,    variable=self.c_param,     command=lambda e: self.update_preview()).pack(fill="x")
        ttk.Label(ctrl, text="Cartoon: Ksize").pack(anchor="w")
        ttk.Scale(ctrl, from_=1, to=31,    variable=self.k_size,      command=lambda e: self.update_preview()).pack(fill="x")
        ttk.Label(ctrl, text="Cartoon: Color σ").pack(anchor="w")
        ttk.Scale(ctrl, from_=1, to=500,   variable=self.color_sigma, command=lambda e: self.update_preview()).pack(fill="x")
        ttk.Label(ctrl, text="Cartoon: Space σ").pack(anchor="w")
        ttk.Scale(ctrl, from_=1, to=500,   variable=self.space_sigma, command=lambda e: self.update_preview()).pack(fill="x")

        # Extra filters
        self.invert_var  = tk.BooleanVar()
        self.emboss_var  = tk.BooleanVar()
        ttk.Checkbutton(ctrl, text="Invert Colors", variable=self.invert_var, command=self.update_preview).pack(anchor="w")
        ttk.Checkbutton(ctrl, text="Emboss",       variable=self.emboss_var, command=self.update_preview).pack(anchor="w")

        # Rotate button
        tk.Button(ctrl, text="Rotate Left", command=self.rotate_left).pack(pady=10)

        # --- Right panel: image display ---
        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(side="right", fill="both", expand=True)

    # ————— Folder & file list —————
    def choose_folder(self):
        folder = filedialog.askdirectory()
        if not folder: return
        self.folder = folder
        self.image_list.delete(0, tk.END)
        for fname in sorted(os.listdir(folder)):
            if fname.lower().endswith(('.png','jpg','jpeg','bmp')):
                self.image_list.insert(tk.END, fname)
        if self.image_list.size():
            self.image_list.select_set(0)
            self.load_image(self.image_list.get(0))

    def on_list_select(self, evt):
        sel = self.image_list.curselection()
        if sel:
            fname = self.image_list.get(sel[0])
            self.load_image(fname)

    def load_image(self, fname):
        path = os.path.join(self.folder, fname)
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            messagebox.showerror("Error", f"Unable to load {fname}")
            return
        self.orig_img = img
        self.update_preview()

    # ————— Image transformations —————
    def rotate_left(self):
        if self.orig_img is not None:
            self.orig_img = cv2.rotate(self.orig_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
            self.update_preview()

    def cartoonify(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # edges
        edges = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            self.block_size.get() | 1,
            self.c_param.get()
        )
        # color
        color = cv2.bilateralFilter(
            img,
            d=self.k_size.get()|1,
            sigmaColor=self.color_sigma.get(),
            sigmaSpace=self.space_sigma.get()
        )
        return cv2.bitwise_and(color, color, mask=edges)

    def apply_extra_filters(self, img):
        if self.invert_var.get():
            img = cv2.bitwise_not(img)
        if self.emboss_var.get():
            kernel = np.array([[ -2, -1, 0],
                               [ -1,  1, 1],
                               [  0,  1, 2]], dtype=np.float32)
            img = cv2.filter2D(img, -1, kernel)
        return img

    def apply_retouch(self, img):
        # brightness & contrast: new_img = img*contrast + (brightness-1)*255
        img = cv2.convertScaleAbs(img,
                                  alpha=self.contrast.get(),
                                  beta=(self.brightness.get()-1)*255)
        return img

    # ————— Preview pipeline —————
    def update_preview(self):
        if self.orig_img is None:
            return
        img = self.orig_img.copy()
        # pre-filters
        if self.gray_var.get():
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        if self.sepia_var.get():
            sepia_k = np.array([[0.272,0.534,0.131],
                                [0.349,0.686,0.168],
                                [0.393,0.769,0.189]])
            img = cv2.transform(img, sepia_k)

        # cartoon & extras
        img = self.cartoonify(img)
        img = self.apply_extra_filters(img)

        # retouch
        img = self.apply_retouch(img)

        # draw to Tk canvas
        self.current_img = img
        self._draw_on_canvas(img)

    def _draw_on_canvas(self, img):
        h, w = img.shape[:2]
        # fit to canvas
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        scale = min(cw/w, ch/h, 1.0)
        disp = cv2.resize(img, (int(w*scale), int(h*scale)))
        disp = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
        self.photo = ImageTk.PhotoImage(Image.fromarray(disp))
        self.canvas.delete("all")
        self.canvas.create_image(cw//2, ch//2, image=self.photo, anchor="center")

if __name__ == "__main__":
    app = ImageToolkit()
    app.geometry("1200x700")
    app.mainloop()
