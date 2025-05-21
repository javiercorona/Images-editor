import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2, numpy as np, os

class ImageEditorToolkit(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Editor Toolkit")
        self.geometry("1100x650")

        self.orig = None
        self.proc = None
        self.zoom = 1.0
        self.pan_x = self.pan_y = 0
        self.hist = []; self.hi = -1

        self.build_ui()

    def build_ui(self):
        left = ttk.Frame(self, width=300)
        left.pack(side="left", fill="y", padx=5, pady=5)

        ttk.Button(left, text="Browse Images", command=self.browse).pack(fill="x")
        self.lst = tk.Listbox(left, height=10)
        self.lst.pack(fill="both", expand=True, pady=5)
        self.lst.bind("<<ListboxSelect>>", lambda e: self.load())

        self.info = ttk.Label(left, text="No image")
        self.info.pack(fill="x", pady=5)

        ff = ttk.LabelFrame(left, text="Filters")
        ff.pack(fill="x", pady=5)
        self.gray  = tk.BooleanVar()
        self.sepia = tk.BooleanVar()
        self.inv   = tk.BooleanVar()
        for t,v in [("Gray",self.gray),("Sepia",self.sepia),("Invert",self.inv)]:
            ttk.Checkbutton(ff, text=t, variable=v, command=self.update).pack(anchor="w")

        ttk.Label(ff, text="Brightness").pack(anchor="w")
        self.b = tk.DoubleVar(value=1.0)
        ttk.Scale(ff, from_=0.2, to=2.0, variable=self.b, command=lambda e:self.update()).pack(fill="x")

        ttk.Label(ff, text="Contrast").pack(anchor="w")
        self.c = tk.DoubleVar(value=1.0)
        ttk.Scale(ff, from_=0.2, to=3.0, variable=self.c, command=lambda e:self.update()).pack(fill="x")

        af = ttk.LabelFrame(left, text="Actions")
        af.pack(fill="x", pady=5)
        ttk.Button(af, text="Zoom In",  command=lambda:self.zoom_by(1.2)).pack(fill="x", pady=2)
        ttk.Button(af, text="Zoom Out", command=lambda:self.zoom_by(0.8)).pack(fill="x", pady=2)
        ttk.Button(af, text="Undo",     command=self.undo).pack(fill="x", pady=2)
        ttk.Button(af, text="Redo",     command=self.redo).pack(fill="x", pady=2)
        ttk.Button(af, text="Save As",  command=self.save).pack(fill="x", pady=2)

        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(side="right", fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.sp)
        self.canvas.bind("<B1-Motion>",   self.dp)
        self.canvas.bind("<MouseWheel>",  self.wheel)

    def browse(self):
        d = filedialog.askdirectory()
        if not d: return
        self.lst.delete(0, "end")
        self.folder = d
        for f in sorted(os.listdir(d)):
            if f.lower().endswith((".png",".jpg",".jpeg",".bmp")):
                self.lst.insert("end", f)

    def load(self):
        sel = self.lst.curselection()
        if not sel: return
        fn=self.lst.get(sel[0])
        p=os.path.join(self.folder,fn)
        arr=cv2.imread(p)
        if arr is None: return messagebox.showerror("Error","Bad image")
        self.orig=arr; h,w=arr.shape[:2]
        self.info.config(text=f"{fn} — {w}×{h}")
        self.zoom, self.pan_x, self.pan_y = 1.0, 0,0
        self.hist=[]; self.hi=-1
        self.update(); self.push()

    def update(self):
        if self.orig is None: return
        img=self.orig.copy()
        if self.gray.get():
            img=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            img=cv2.cvtColor(img,cv2.COLOR_GRAY2BGR)
        if self.sepia.get():
            K=np.array([[0.272,0.534,0.131],[0.349,0.686,0.168],[0.393,0.769,0.189]])
            img=cv2.transform(img,K)
        if self.inv.get():
            img=cv2.bitwise_not(img)
        img=np.clip(img*self.c.get()+(self.b.get()-1)*128,0,255).astype(np.uint8)
        pil=Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB))
        if self.zoom!=1.0:
            w,h=pil.size; pil=pil.resize((int(w*self.zoom),int(h*self.zoom)),Image.LANCZOS)
        self.proc=pil; self.draw(pil)

    def draw(self,pil):
        self.canvas.delete("all")
        self.tk=ImageTk.PhotoImage(pil)
        self.canvas.create_image(self.pan_x,self.pan_y,anchor="nw",image=self.tk)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def zoom_by(self,f):
        self.zoom=max(0.1,min(10.0,self.zoom*f))
        self.update()

    def sp(self,e): self.sx, self.sy = e.x,e.y
    def dp(self,e):
        dx,dy=e.x-self.sx,e.y-self.sy
        self.pan_x+=dx; self.pan_y+=dy
        self.sx,self.sy=e.x,e.y
        self.draw(self.proc)

    def wheel(self,e): self.zoom_by(1.1 if e.delta>0 else 0.9)

    def push(self):
        if self.proc is None: return
        self.hist=self.hist[:self.hi+1]; self.hist.append(self.proc.copy())
        self.hi=len(self.hist)-1
        if len(self.hist)>20: self.hist.pop(0); self.hi-=1

    def undo(self):
        if self.hi>0:
            self.hi-=1; self.proc=self.hist[self.hi].copy(); self.draw(self.proc)
    def redo(self):
        if self.hi<len(self.hist)-1:
            self.hi+=1; self.proc=self.hist[self.hi].copy(); self.draw(self.proc)

    def save(self):
        if self.proc is None: return
        p=filedialog.asksaveasfilename(defaultextension=".png",
                                       filetypes=[("PNG","*.png"),("JPEG","*.jpg;*.jpeg")])
        if not p: return
        self.proc.save(p)
        messagebox.showinfo("Saved","Image saved")

if __name__=="__main__":
    ImageEditorToolkit().mainloop()
