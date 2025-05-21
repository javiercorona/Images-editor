import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2, numpy as np, os
from enum import Enum

class MediaEditorToolkit(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Media Editor Toolkit")
        self.geometry("1200x700")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # shared
        self.folder = None
        self.orig = None
        self.proc = None

        # video state
        self.video_cap = None
        self.video_playing = False
        self.video_frame_count = 0
        self.video_current_frame = 0
        self.video_fps = 30
        self.video_update_id = None
        self.trim_start = 0
        self.trim_end = 0
        self.cut_ranges = []

        # image state
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.history = []
        self.history_index = -1

        self.create_ui()

    def create_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Video Editor Tab
        vid_tab = ttk.Frame(notebook)
        notebook.add(vid_tab, text="Video Editor")
        self.build_video_ui(vid_tab)

        # Image Editor Tab
        img_tab = ttk.Frame(notebook)
        notebook.add(img_tab, text="Image Editor")
        self.build_image_ui(img_tab)

    # --- Video UI ---
    def build_video_ui(self, parent):
        left = ttk.Frame(parent, width=300)
        left.pack(side="left", fill="y", padx=5, pady=5)

        ttk.Button(left, text="Browse Videos", command=self.browse_videos).pack(fill="x")
        self.video_list = tk.Listbox(left, height=15)
        self.video_list.pack(fill="both", expand=True, pady=5)
        self.video_list.bind("<<ListboxSelect>>", self.load_video)

        self.video_info = ttk.Label(left, text="No video loaded")
        self.video_info.pack(fill="x", pady=5)

        ctrls = ttk.LabelFrame(left, text="Video Controls")
        ctrls.pack(fill="x", pady=5)

        btnf = ttk.Frame(ctrls); btnf.pack(fill="x", pady=2)
        self.play_btn = ttk.Button(btnf, text="▶", width=3, command=self.toggle_playback)
        self.play_btn.pack(side="left", padx=2)
        ttk.Button(btnf, text="⏮", width=3, command=lambda: self.seek_video(-5)).pack(side="left", padx=2)
        ttk.Button(btnf, text="⏭", width=3, command=lambda: self.seek_video(5)).pack(side="left", padx=2)
        ttk.Button(btnf, text="⟲", width=3, command=lambda: self.seek_frame(0)).pack(side="left", padx=2)

        trimf = ttk.Frame(ctrls); trimf.pack(fill="x", pady=2)
        ttk.Button(trimf, text="Set Start", command=self.set_trim_start).pack(side="left", fill="x", expand=True)
        ttk.Button(trimf, text="Set End",   command=self.set_trim_end).pack(side="left", fill="x", expand=True)
        ttk.Button(trimf, text="Trim",      command=self.apply_trim).pack(side="left", fill="x", expand=True)

        cutf = ttk.Frame(ctrls); cutf.pack(fill="x", pady=2)
        ttk.Button(cutf, text="Cut Start", command=self.mark_cut_start).pack(side="left", fill="x", expand=True)
        ttk.Button(cutf, text="Cut End",   command=self.mark_cut_end).pack(side="left", fill="x", expand=True)
        ttk.Button(cutf, text="Apply Cut", command=self.apply_cuts).pack(side="left", fill="x", expand=True)

        self.timeline = ttk.Scale(ctrls, from_=0, to=1, command=self.on_timeline_scroll)
        self.timeline.pack(fill="x", pady=5)

        self.status_bar = ttk.Label(parent, text="Ready", relief="sunken")
        self.status_bar.pack(side="bottom", fill="x")

        self.video_canvas = tk.Canvas(parent, bg="black")
        self.video_canvas.pack(side="right", fill="both", expand=True)

    # --- Image UI ---
    def build_image_ui(self, parent):
        left = ttk.Frame(parent, width=300)
        left.pack(side="left", fill="y", padx=5, pady=5)

        ttk.Button(left, text="Browse Images", command=self.browse_images).pack(fill="x")
        self.img_list = tk.Listbox(left, height=10)
        self.img_list.pack(fill="both", expand=True, pady=5)
        self.img_list.bind("<<ListboxSelect>>", lambda e: self.load_image())

        self.img_info = ttk.Label(left, text="No image loaded")
        self.img_info.pack(fill="x", pady=5)

        ff = ttk.LabelFrame(left, text="Filters & Adjustments")
        ff.pack(fill="x", pady=5)
        self.gray  = tk.BooleanVar()
        self.sepia = tk.BooleanVar()
        self.inv   = tk.BooleanVar()
        for txt,var in [("Grayscale",self.gray),("Sepia",self.sepia),("Invert",self.inv)]:
            ttk.Checkbutton(ff, text=txt, variable=var, command=self.update_image).pack(anchor="w")

        ttk.Label(ff, text="Brightness").pack(anchor="w")
        self.bright = tk.DoubleVar(value=1.0)
        ttk.Scale(ff, from_=0.2, to=2.0, variable=self.bright,
                  command=lambda e: self.update_image()).pack(fill="x")

        ttk.Label(ff, text="Contrast").pack(anchor="w")
        self.contrast = tk.DoubleVar(value=1.0)
        ttk.Scale(ff, from_=0.2, to=3.0, variable=self.contrast,
                  command=lambda e: self.update_image()).pack(fill="x")

        af = ttk.LabelFrame(left, text="Actions")
        af.pack(fill="x", pady=5)
        ttk.Button(af, text="Zoom In",  command=lambda:self.adjust_zoom(1.2)).pack(fill="x", pady=2)
        ttk.Button(af, text="Zoom Out", command=lambda:self.adjust_zoom(0.8)).pack(fill="x", pady=2)
        ttk.Button(af, text="Undo",     command=self.undo).pack(fill="x", pady=2)
        ttk.Button(af, text="Redo",     command=self.redo).pack(fill="x", pady=2)
        ttk.Button(af, text="Save As",  command=self.save_image).pack(fill="x", pady=2)

        # reuse video_canvas for image preview
        self.img_canvas = self.video_canvas
        self.img_canvas.bind("<ButtonPress-1>", self.start_pan)
        self.img_canvas.bind("<B1-Motion>",    self.do_pan)
        self.img_canvas.bind("<MouseWheel>",   self.on_mousewheel)

    # --- Video Methods ---
    def browse_videos(self):
        fld = filedialog.askdirectory()
        if not fld: return
        self.folder = fld
        self.video_list.delete(0, tk.END)
        for f in sorted(os.listdir(fld)):
            if f.lower().endswith((".mp4",".avi",".mov",".mkv")):
                self.video_list.insert(tk.END, f)

    def load_video(self, _):
        sel = self.video_list.curselection()
        if not sel: return
        fn = self.video_list.get(sel[0])
        path = os.path.join(self.folder, fn)
        self.stop_playback()
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return messagebox.showerror("Error","Cannot open video")
        self.video_cap = cap
        self.video_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_fps = cap.get(cv2.CAP_PROP_FPS)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.trim_start, self.trim_end = 0, self.video_frame_count-1
        self.cut_ranges = []
        self.video_current_frame = 0
        self.video_info.config(
            text=f"{fn}\n{w}×{h} @ {self.video_fps:.1f}fps\nFrames: {self.video_frame_count}"
        )
        self.timeline.config(to=self.video_frame_count-1)
        self.seek_frame(0)

    def toggle_playback(self):
        if not self.video_cap: return
        if self.video_playing:
            self.stop_playback(); self.play_btn.config(text="▶")
        else:
            self.video_playing = True; self.play_btn.config(text="⏸"); self._play_step()

    def _play_step(self):
        if not self.video_playing: return
        ret, frame = self.video_cap.read()
        if not ret:
            return self.stop_playback()
        pos = int(self.video_cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.seek_frame(pos, update_slider=False)
        self.video_update_id = self.after(int(1000/self.video_fps), self._play_step)

    def stop_playback(self):
        self.video_playing = False
        if self.video_update_id:
            self.after_cancel(self.video_update_id)
            self.video_update_id = None

    def seek_video(self, secs):
        self.seek_frame(self.video_current_frame + int(secs*self.video_fps))

    def on_timeline_scroll(self, val):
        try:
            fno = int(float(val))
        except ValueError:
            return
        self.seek_frame(fno)

    def seek_frame(self, fno, update_slider=True):
        if not self.video_cap: return
        fno = max(0, min(self.video_frame_count-1, fno))
        self.stop_playback()
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, fno)
        ret, frame = self.video_cap.read()
        if not ret: return
        self.video_current_frame = fno
        if update_slider:
            self.timeline.set(fno)
        self._show_frame(frame)

    def _show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        img = self.resize_image(img)
        self.tkimg = ImageTk.PhotoImage(img)
        self.video_canvas.create_image(0,0,anchor="nw",image=self.tkimg)

    def set_trim_start(self):
        self.trim_start = self.video_current_frame
        self.status_bar.config(text=f"Trim start = {self.trim_start}")

    def set_trim_end(self):
        self.trim_end = self.video_current_frame
        self.status_bar.config(text=f"Trim end   = {self.trim_end}")

    def apply_trim(self):
        if self.trim_start >= self.trim_end:
            return messagebox.showerror("Error","Invalid trim range")
        out = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4","*.mp4"),("AVI","*.avi")]
        )
        if not out: return
        w = int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.video_fps
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out, fourcc, fps, (w,h))
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.trim_start)
        for fn in range(self.trim_start, self.trim_end+1):
            ret, frm = self.video_cap.read()
            if ret:
                writer.write(frm)
        writer.release()
        messagebox.showinfo("Done","Trim saved")

    def mark_cut_start(self):
        self.cut_ranges.append({"start":self.video_current_frame,"end":-1})
        self.status_bar.config(text=f"Cut start @ {self.video_current_frame}")

    def mark_cut_end(self):
        if not self.cut_ranges or self.cut_ranges[-1]["end"]!=-1:
            return messagebox.showerror("Error","No cut to end")
        if self.video_current_frame<=self.cut_ranges[-1]["start"]:
            return messagebox.showerror("Error","End must follow start")
        self.cut_ranges[-1]["end"] = self.video_current_frame
        self.status_bar.config(text=f"Cut end @ {self.video_current_frame}")

    def apply_cuts(self):
        if not self.cut_ranges:
            return messagebox.showerror("Error","No cuts marked")
        out = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4","*.mp4"),("AVI","*.avi")]
        )
        if not out: return
        w = int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.video_fps
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out, fourcc, fps, (w,h))
        segs, prev = [], 0
        for c in sorted(self.cut_ranges, key=lambda x:x["start"]):
            if c["start"]>prev:
                segs.append((prev, c["start"]-1))
            prev = c["end"]+1
        if prev<self.video_frame_count-1:
            segs.append((prev,self.video_frame_count-1))
        for st, ed in segs:
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, st)
            for fn in range(st,ed+1):
                ret,frm = self.video_cap.read()
                if ret:
                    writer.write(frm)
        writer.release()
        messagebox.showinfo("Done","Cuts applied")

    # --- Image Methods ---
    def browse_images(self):
        fld = filedialog.askdirectory()
        if not fld: return
        self.folder = fld
        self.img_list.delete(0,tk.END)
        for f in sorted(os.listdir(fld)):
            if f.lower().endswith((".png",".jpg",".jpeg",".bmp")):
                self.img_list.insert(tk.END, f)

    def load_image(self):
        sel = self.img_list.curselection()
        if not sel: return
        fn = self.img_list.get(sel[0])
        path = os.path.join(self.folder,fn)
        arr = cv2.imread(path)
        if arr is None:
            return messagebox.showerror("Error","Cannot load image")
        self.orig = arr
        h,w = arr.shape[:2]
        self.img_info.config(text=f"{fn} — {w}×{h}")
        self.zoom_level = 1.0
        self.pan_x = self.pan_y = 0
        self.history = []; self.history_index = -1
        self.update_image(); self.add_to_history()

    def update_image(self):
        if self.orig is None: return
        img = self.orig.copy()
        if self.gray.get():
            img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            img = cv2.cvtColor(img,cv2.COLOR_GRAY2BGR)
        if self.sepia.get():
            K = np.array([[0.272,0.534,0.131],
                          [0.349,0.686,0.168],
                          [0.393,0.769,0.189]])
            img = cv2.transform(img,K)
        if self.inv.get():
            img = cv2.bitwise_not(img)
        c,b = self.contrast.get(), self.bright.get()
        img = np.clip(img*c + (b-1)*128,0,255).astype(np.uint8)
        pil = Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB))
        if self.zoom_level!=1.0:
            w,h = pil.size
            pil = pil.resize((int(w*self.zoom_level), int(h*self.zoom_level)),Image.LANCZOS)
        self.proc = pil
        self._draw_image(pil)

    def _draw_image(self,pil):
        c = self.img_canvas
        c.delete("all")
        self.tkimg = ImageTk.PhotoImage(pil)
        c.create_image(self.pan_x,self.pan_y,anchor="nw",image=self.tkimg)
        c.config(scrollregion=c.bbox("all"))

    def adjust_zoom(self,f):
        self.zoom_level = max(0.1,min(10.0,self.zoom_level*f))
        self.update_image()

    def start_pan(self,ev):
        self.pan_start_x, self.pan_start_y = ev.x, ev.y
    def do_pan(self,ev):
        dx,dy = ev.x-self.pan_start_x, ev.y-self.pan_start_y
        self.pan_x+=dx; self.pan_y+=dy
        self.pan_start_x, self.pan_start_y = ev.x, ev.y
        self._draw_image(self.proc)
    def on_mousewheel(self,ev):
        self.adjust_zoom(1.1 if ev.delta>0 else 0.9)

    def add_to_history(self):
        if self.proc is None: return
        self.history = self.history[:self.history_index+1]
        self.history.append(self.proc.copy())
        self.history_index = len(self.history)-1
        if len(self.history)>20:
            self.history.pop(0); self.history_index-=1

    def undo(self):
        if self.history_index>0:
            self.history_index-=1
            self.proc = self.history[self.history_index].copy()
            self._draw_image(self.proc)
    def redo(self):
        if self.history_index<len(self.history)-1:
            self.history_index+=1
            self.proc = self.history[self.history_index].copy()
            self._draw_image(self.proc)

    def save_image(self):
        if not self.proc: return
        ftypes=[("PNG","*.png"),("JPEG","*.jpg;*.jpeg"),("All","*.*")]
        p=filedialog.asksaveasfilename(defaultextension=".png",filetypes=ftypes)
        if not p: return
        self.proc.save(p)
        messagebox.showinfo("Saved",f"Image saved to {p}")

    def resize_image(self,img):
        cw = self.video_canvas.winfo_width()
        ch = self.video_canvas.winfo_height()
        if cw<2 or ch<2: return img
        ir = img.width/img.height; cr = cw/ch
        if cr>ir:
            nh=ch; nw=int(nh*ir)
        else:
            nw=cw; nh=int(nw/ir)
        return img.resize((nw,nh),Image.LANCZOS)

    def on_close(self):
        self.stop_playback()
        if self.video_cap: self.video_cap.release()
        self.destroy()

if __name__ == "__main__":
    app = MediaEditorToolkit()
    app.mainloop()
