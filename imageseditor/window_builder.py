import tkinter as tk
from tkinter import ttk, messagebox

class WindowBuilder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Window Builder")
        self.geometry("300x250")
        self.resizable(False, False)

        # Options
        self.opts = {
            "Title Bar": tk.BooleanVar(value=True),
            "Menu Bar":  tk.BooleanVar(value=True),
            "Vertical Scroll":   tk.BooleanVar(value=True),
            "Horizontal Scroll": tk.BooleanVar(value=True),
            "Sizing Border":     tk.BooleanVar(value=True),
        }

        frm = ttk.LabelFrame(self, text="Select Window Elements")
        frm.pack(padx=10, pady=10, fill="both", expand=True)

        for i,(label,var) in enumerate(self.opts.items()):
            ttk.Checkbutton(frm, text=label, variable=var).grid(row=i, column=0, sticky="w", pady=2)

        ttk.Button(self, text="Preview", command=self.preview).pack(pady=10)

    def preview(self):
        # Create a top‐level window with chosen chrome
        w = tk.Toplevel(self)
        # Title bar
        if self.opts["Title Bar"].get():
            w.title("Preview Window")
        else:
            w.overrideredirect(True)

        # Sizing border
        w.resizable(self.opts["Sizing Border"].get(), self.opts["Sizing Border"].get())

        # Client area
        txt = tk.Text(w, wrap="none")
        txt.insert("end", "This is the client area.\n" * 10)
        txt.pack(side="top", fill="both", expand=True)

        # Menu bar
        if self.opts["Menu Bar"].get():
            menubar = tk.Menu(w)
            filem = tk.Menu(menubar, tearoff=0)
            filem.add_command(label="Exit", command=w.destroy)
            menubar.add_cascade(label="File", menu=filem)
            w.config(menu=menubar)

        # Scrollbars
        if self.opts["Vertical Scroll"].get():
            vscroll = ttk.Scrollbar(w, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=vscroll.set)
            vscroll.pack(side="right", fill="y")
        if self.opts["Horizontal Scroll"].get():
            hscroll = ttk.Scrollbar(w, orient="horizontal", command=txt.xview)
            txt.configure(xscrollcommand=hscroll.set)
            hscroll.pack(side="bottom", fill="x")

        # Center the preview
        w.update_idletasks()
        x = self.winfo_x() + 50
        y = self.winfo_y() + 50
        w.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    WindowBuilder().mainloop()
