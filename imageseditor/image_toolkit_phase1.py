import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
import cv2
import numpy as np
from PIL import Image, ImageTk

class ImageToolkitExtended(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Toolkit Extended")
        self.geometry("900x650")

        # Core image state
        self.folder = None
        self.orig_img = None      # Original loaded BGR image
        self.current_img = None   # Working BGR image

        # History for undo/redo
        self.history = []
        self.history_index = -1

        # Crop state
        self.crop_start = None
        self.crop_rect = None
        self.crop_box_id = None

        # Annotation
        self.mode = None
        self.brush_color = (255,0,0)
        self.brush_size = 5

        # Watermark
        self.wm_text = tk.StringVar()
        self.wm_pos = tk.StringVar(value="bottom-right")
        self.wm_opacity = tk.DoubleVar(value=0.5)

        self.create_ui()

    def create_ui(self):
        # Top controls with horizontal scroll
        container = ttk.Frame(self)
        container.pack(side="top", fill="x")
        canvas_ctrl = tk.Canvas(container, height=180)
        scrollbar = ttk.Scrollbar(container, orient="horizontal", command=canvas_ctrl.xview)
        canvas_ctrl.configure(xscrollcommand=scrollbar.set)
        scrollbar.pack(side="bottom", fill="x")
        canvas_ctrl.pack(side="top", fill="x", expand=True)

        self.ctrl_frame = ttk.Frame(canvas_ctrl)
        canvas_ctrl.create_window((0,0), window=self.ctrl_frame, anchor="nw")
        self.ctrl_frame.bind("<Configure>", lambda e: canvas_ctrl.configure(scrollregion=canvas_ctrl.bbox("all")))

        # Browse + file list
        ttk.Button(self.ctrl_frame, text="Browse Folder…", command=self.choose_folder).grid(row=0, column=0, padx=2, pady=2)
        self.file_list = tk.Listbox(self.ctrl_frame, height=4)
        self.file_list.grid(row=0, column=1, rowspan=2, padx=2, pady=2)
        self.file_list.bind("<<ListboxSelect>>", self.on_select)

        col = 2
        def nc():
            nonlocal col; c=col; col+=1; return c

        # Filters & adjustments
        self.gray_var = tk.BooleanVar()
        self.sepia_var = tk.BooleanVar()
        self.inv_var = tk.BooleanVar()
        ttk.Checkbutton(self.ctrl_frame, text="Grayscale", variable=self.gray_var, command=self.apply_pipeline).grid(row=0, column=nc(), padx=2)
        ttk.Checkbutton(self.ctrl_frame, text="Sepia",    variable=self.sepia_var, command=self.apply_pipeline).grid(row=0, column=nc(), padx=2)
        ttk.Checkbutton(self.ctrl_frame, text="Invert",   variable=self.inv_var,   command=self.apply_pipeline).grid(row=0, column=nc(), padx=2)
        ttk.Label(self.ctrl_frame, text="Blur").grid(row=0, column=nc());   self.blur_scale = ttk.Scale(self.ctrl_frame, from_=0, to=5, orient="horizontal", command=lambda e:self.apply_pipeline()); self.blur_scale.grid(row=0, column=nc())
        ttk.Label(self.ctrl_frame, text="Sharpen").grid(row=0, column=nc());self.sharp_scale = ttk.Scale(self.ctrl_frame, from_=0, to=5, orient="horizontal", command=lambda e:self.apply_pipeline()); self.sharp_scale.grid(row=0, column=nc())
        ttk.Label(self.ctrl_frame, text="Brightness").grid(row=0, column=nc()); self.bright_scale = ttk.Scale(self.ctrl_frame, from_=0.2, to=2, orient="horizontal", command=lambda e:self.apply_pipeline()); self.bright_scale.grid(row=0, column=nc())
        ttk.Label(self.ctrl_frame, text="Contrast").grid(row=0, column=nc());  self.contrast_scale = ttk.Scale(self.ctrl_frame, from_=0.2, to=3, orient="horizontal", command=lambda e:self.apply_pipeline()); self.contrast_scale.grid(row=0, column=nc())
        ttk.Label(self.ctrl_frame, text="Cartoon bs").grid(row=0, column=nc()); self.bs_scale = ttk.Scale(self.ctrl_frame, from_=3, to=31, orient="horizontal", command=lambda e:self.apply_pipeline()); self.bs_scale.grid(row=0, column=nc())
        ttk.Label(self.ctrl_frame, text="Cartoon C").grid(row=0, column=nc());  self.c_scale = ttk.Scale(self.ctrl_frame, from_=1, to=50, orient="horizontal", command=lambda e:self.apply_pipeline()); self.c_scale.grid(row=0, column=nc())
        self.emboss_var = tk.BooleanVar(); ttk.Checkbutton(self.ctrl_frame, text="Emboss", variable=self.emboss_var, command=self.apply_pipeline).grid(row=0, column=nc(), padx=2)

        # Annotation
        ttk.Button(self.ctrl_frame, text="Pen", command=lambda:self.set_mode('pen')).grid(row=1, column=nc(), padx=2)
        ttk.Button(self.ctrl_frame, text="Erase", command=lambda:self.set_mode('eraser')).grid(row=1, column=nc(), padx=2)
        ttk.Button(self.ctrl_frame, text="Text", command=lambda:self.set_mode('text')).grid(row=1, column=nc(), padx=2)
        ttk.Button(self.ctrl_frame, text="Color", command=self.choose_color).grid(row=1, column=nc(), padx=2)
        ttk.Label(self.ctrl_frame, text="Size").grid(row=1, column=nc()); 
        self.size_scale = ttk.Scale(self.ctrl_frame, from_=1, to=50, orient="horizontal", command=self.update_brush_size)
        self.size_scale.set(self.brush_size); self.size_scale.grid(row=1, column=nc())

        # Crop & Canvas resize
        ttk.Button(self.ctrl_frame, text="Crop Mode", command=self.enable_crop_mode).grid(row=1, column=nc(), padx=2)
        ttk.Button(self.ctrl_frame, text="Apply Crop", command=self.apply_crop).grid(row=1, column=nc(), padx=2)
        ttk.Button(self.ctrl_frame, text="Canvas Resize", command=self.canvas_resize).grid(row=1, column=nc(), padx=2)

        # Transform
        ttk.Button(self.ctrl_frame, text="Rot L", command=lambda:self.transform(cv2.ROTATE_90_COUNTERCLOCKWISE)).grid(row=1, column=nc(), padx=2)
        ttk.Button(self.ctrl_frame, text="Rot R", command=lambda:self.transform(cv2.ROTATE_90_CLOCKWISE)).grid(row=1, column=nc(), padx=2)
        ttk.Button(self.ctrl_frame, text="Flip H", command=lambda:self.transform('hflip')).grid(row=1, column=nc(), padx=2)
        ttk.Button(self.ctrl_frame, text="Flip V", command=lambda:self.transform('vflip')).grid(row=1, column=nc(), padx=2)

        # History & Save
        ttk.Button(self.ctrl_frame, text="Undo", command=self.undo).grid(row=1, column=nc(), padx=2)
        ttk.Button(self.ctrl_frame, text="Redo", command=self.redo).grid(row=1, column=nc(), padx=2)
        ttk.Button(self.ctrl_frame, text="Save", command=self.save_image).grid(row=1, column=nc(), padx=2)

        # Watermark
        ttk.Label(self.ctrl_frame, text="Watermark").grid(row=2, column=0, padx=2)
        ttk.Entry(self.ctrl_frame, textvariable=self.wm_text).grid(row=2, column=1, padx=2)
        ttk.OptionMenu(self.ctrl_frame, self.wm_pos, self.wm_pos.get(), *["top-left","top-right","bottom-left","bottom-right","center"]).grid(row=2, column=2, padx=2)
        ttk.Scale(self.ctrl_frame, from_=0.0, to=1.0, orient="horizontal", variable=self.wm_opacity).grid(row=2, column=3, padx=2)
        ttk.Button(self.ctrl_frame, text="Apply WM", command=self.apply_watermark).grid(row=2, column=4, padx=2)

        # Image canvas
        self.canvas = tk.Canvas(self, bg="black", cursor="cross")
        self.canvas.pack(side="bottom", fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>",    self.on_mouse_down)
        self.canvas.bind("<B1-Motion>",       self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    # --- Methods from your working version, unchanged --- #

    def choose_folder(self):
        fld = filedialog.askdirectory()
        if not fld: return
        self.folder = fld
        self.file_list.delete(0, tk.END)
        for f in sorted(os.listdir(fld)):
            if f.lower().endswith(('.png','jpg','jpeg','bmp')):
                self.file_list.insert(tk.END, f)

    def on_select(self, evt):
        sel = self.file_list.curselection()
        if not sel: return
        path = os.path.join(self.folder, self.file_list.get(sel[0]))
        img = cv2.imread(path)
        if img is None:
            return messagebox.showerror("Error", "Cannot load image")
        self.orig_img = img
        self.current_img = img.copy()
        self.history.clear(); self.history_index=-1
        self.push_history(self.orig_img)
        self.apply_pipeline()

    def apply_pipeline(self):
        if self.orig_img is None: return
        img = self.orig_img.copy()
        if self.gray_var.get():
            g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        if self.sepia_var.get():
            K = np.array([[0.272,0.534,0.131],[0.349,0.686,0.168],[0.393,0.769,0.189]])
            img = cv2.transform(img, K)
        if self.inv_var.get():
            img = cv2.bitwise_not(img)
        b = self.blur_scale.get()
        if b>0:
            img = cv2.GaussianBlur(img, (0,0), b)
        s = self.sharp_scale.get()
        if s>0:
            kern = np.array([[-1,-1,-1],[-1,9+s,-1],[-1,-1,-1]])
            img = cv2.filter2D(img, -1, kern)
        block = int(self.bs_scale.get())|1; c = int(self.c_scale.get())
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.adaptiveThreshold(gray,255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, block, c)
        color = cv2.bilateralFilter(img, block, 200, 200)
        img = cv2.bitwise_and(color, color, mask=edges)
        if self.emboss_var.get():
            k = np.array([[-2,-1,0],[-1,1,1],[0,1,2]])
            img = cv2.filter2D(img, -1, k)
        alpha = self.contrast_scale.get(); beta = (self.bright_scale.get()-1)*255
        img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
        self.current_img = img
        self.push_history(img)
        self.display(img)

    def transform(self, op):
        if self.current_img is None: return
        img = self.current_img.copy()
        if op=='hflip': img = cv2.flip(img,1)
        elif op=='vflip': img = cv2.flip(img,0)
        else: img = cv2.rotate(img, op)
        self.orig_img = img
        self.push_history(img)
        self.apply_pipeline()

    def set_mode(self, m):
        self.mode = m
        messagebox.showinfo("Mode", f"Switched to {m}")

    def choose_color(self):
        c = colorchooser.askcolor()
        if c[0]:
            r,g,b = map(int, c[0])
            self.brush_color = (b,g,r)

    def update_brush_size(self, v):
        self.brush_size = int(float(v))

    def enable_crop_mode(self):
        self.crop_start = None
        self.crop_rect  = None
        if self.crop_box_id:
            self.canvas.delete(self.crop_box_id)
            self.crop_box_id = None
        messagebox.showinfo("Crop Mode", "Drag to select crop region")

    def on_mouse_down(self, ev):
        if self.mode in ('pen','eraser'):
            self.last_pt = (ev.x, ev.y)
        elif self.mode == 'text' and self.current_img is not None:
            txt = simpledialog.askstring("Text", "Enter text:")
            if not txt: return
            ix, iy = self.canvas_to_image(ev.x, ev.y)
            cv2.putText(self.current_img, txt, (ix, iy),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        self.brush_size/20, self.brush_color, 2)
            self.push_history(self.current_img)
            self.display(self.current_img)
        else:
            self.crop_start = (ev.x, ev.y)

    def on_mouse_drag(self, ev):
        if self.mode in ('pen','eraser') and hasattr(self, 'last_pt'):
            x0,y0 = self.last_pt
            x1,y1 = ev.x, ev.y
            ix0,iy0 = self.canvas_to_image(x0,y0)
            ix1,iy1 = self.canvas_to_image(x1,y1)
            color = (255,255,255) if self.mode=='eraser' else self.brush_color
            cv2.line(self.current_img, (ix0,iy0),(ix1,iy1), color, self.brush_size)
            self.last_pt = (x1,y1)
            self.display(self.current_img)
        elif self.crop_start:
            if self.crop_box_id:
                self.canvas.delete(self.crop_box_id)
            x0,y0 = self.crop_start
            self.crop_box_id = self.canvas.create_rectangle(x0,y0,ev.x,ev.y, outline='yellow')

    def on_mouse_up(self, ev):
        if self.mode in ('pen','eraser'):
            self.push_history(self.current_img)
        elif self.mode!='text' and self.crop_start:
            x0,y0 = self.crop_start
            self.crop_rect = (min(x0,ev.x),min(y0,ev.y),max(x0,ev.x),max(y0,ev.y))
            messagebox.showinfo("Crop", "Click 'Apply Crop' to commit.")
        self.last_pt = None

    def canvas_to_image(self, x, y):
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        ih, iw = self.current_img.shape[:2]
        scale = min(cw/iw, ch/ih)
        off_x, off_y = (cw-iw*scale)/2, (ch-ih*scale)/2
        ix = int((x-off_x)/scale)
        iy = int((y-off_y)/scale)
        return max(0,min(iw-1,ix)), max(0,min(ih-1,iy))

    def apply_crop(self):
        if not self.crop_rect or self.orig_img is None: return
        x0,y0,x1,y1 = self.crop_rect
        ix0,iy0 = self.canvas_to_image(x0,y0)
        ix1,iy1 = self.canvas_to_image(x1,y1)
        if ix1<=ix0 or iy1<=iy0:
            return messagebox.showerror("Error","Invalid crop region")
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
        new_w = simpledialog.askinteger("Canvas Resize","New width:",minvalue=1)
        new_h = simpledialog.askinteger("Canvas Resize","New height:",minvalue=1)
        if not new_w or not new_h: return
        ih, iw = self.orig_img.shape[:2]
        canvas = np.zeros((new_h,new_w,3),dtype=np.uint8)
        off_x, off_y = (new_w-iw)//2, (new_h-ih)//2
        canvas[off_y:off_y+ih, off_x:off_x+iw] = self.orig_img
        self.orig_img = canvas
        self.push_history(canvas)
        self.apply_pipeline()

    def push_history(self, img):
        self.history = self.history[:self.history_index+1]
        self.history.append(img.copy())
        self.history_index = len(self.history)-1
        if len(self.history)>20:
            self.history.pop(0)
            self.history_index -= 1

    def undo(self):
        if self.history_index>0:
            self.history_index -= 1
            self.orig_img = self.history[self.history_index].copy()
            self.apply_pipeline()

    def redo(self):
        if self.history_index < len(self.history)-1:
            self.history_index += 1
            self.orig_img = self.history[self.history_index].copy()
            self.apply_pipeline()

    def display(self, img):
        ih, iw = img.shape[:2]
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        scale = min(cw/iw, ch/ih)
        disp = cv2.resize(img, (int(iw*scale), int(ih*scale)))
        disp = cv2.cvtColor(disp, cv2.COLOR_BGR2RGB)
        self.photo = ImageTk.PhotoImage(Image.fromarray(disp))
        self.canvas.delete("all")
        self.canvas.create_image(cw//2, ch//2, image=self.photo, anchor='center')

    def save_image(self):
        if self.orig_img is None: return
        p = filedialog.asksaveasfilename(defaultextension=".png",
            filetypes=[("PNG","*.png"),("JPEG","*.jpg;*.jpeg")])
        if not p: return
        cv2.imwrite(p, self.orig_img)
        messagebox.showinfo("Saved", f"Image saved to {p}")

    def apply_watermark(self):
        if self.orig_img is None or not self.wm_text.get().strip():
            return messagebox.showwarning("Watermark","Load image and enter text first")
        img = self.current_img.copy()
        h, w = img.shape[:2]
        text = self.wm_text.get()
        font_scale = w / 800
        thickness = max(1, int(2 * font_scale))
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        pos = self.wm_pos.get()
        margin = 10
        if pos=="top-left":    x,y = margin, margin+th
        elif pos=="top-right": x,y = w-tw-margin, margin+th
        elif pos=="bottom-left":x,y = margin, h-th-margin
        elif pos=="bottom-right":x,y= w-tw-margin, h-margin
        else:                  x,y = (w-tw)//2,(h+th)//2
        overlay = img.copy()
        cv2.putText(overlay, text, (int(x),int(y)), cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, (255,255,255), thickness, cv2.LINE_AA)
        alpha = self.wm_opacity.get()
        blended = cv2.addWeighted(overlay, alpha, img, 1-alpha, 0)
        self.orig_img = blended
        self.current_img = blended
        self.push_history(blended)
        self.display(blended)

if __name__=="__main__":
    ImageToolkitExtended().mainloop()
