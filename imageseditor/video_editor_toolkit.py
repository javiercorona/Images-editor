import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import os
from enum import Enum
import imageio

class MediaType(Enum):
    IMAGE = 1
    VIDEO = 2

class VideoEditorToolkit(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Editor Toolkit")
        self.geometry("1200x700")
        
        # Video state variables
        self.video_cap = None
        self.video_playing = False
        self.video_frame_count = 0
        self.video_current_frame = 0
        self.video_fps = 30
        self.video_update_id = None
        self.trim_start = 0
        self.trim_end = 0
        self.cut_ranges = []
        
        # UI setup
        self.create_ui()
        
    def create_ui(self):
        # Left panel - Media browser
        left_panel = ttk.Frame(self, width=300)
        left_panel.pack(side="left", fill="y", padx=5, pady=5)
        
        # Media selection
        ttk.Button(left_panel, text="Browse Videos", command=self.browse_videos).pack(fill="x")
        self.video_list = tk.Listbox(left_panel, height=15)
        self.video_list.pack(fill="both", expand=True, pady=5)
        self.video_list.bind("<<ListboxSelect>>", self.load_video)
        
        # Video info display
        self.video_info = ttk.Label(left_panel, text="No video loaded")
        self.video_info.pack(fill="x")
        
        # Video controls frame
        control_frame = ttk.LabelFrame(left_panel, text="Video Controls")
        control_frame.pack(fill="x", pady=10)
        
        # Playback controls
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x", pady=5)
        
        self.play_btn = ttk.Button(btn_frame, text="▶", width=3, command=self.toggle_playback)
        self.play_btn.pack(side="left", padx=2)
        ttk.Button(btn_frame, text="⏮", width=3, command=lambda: self.seek_video(-5)).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="⏭", width=3, command=lambda: self.seek_video(5)).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="⟲", width=3, command=self.rewind_to_start).pack(side="left", padx=2)
        
        # Trim controls
        trim_frame = ttk.Frame(control_frame)
        trim_frame.pack(fill="x", pady=5)
        
        ttk.Button(trim_frame, text="Set Start", command=self.set_trim_start).pack(side="left", fill="x", expand=True)
        ttk.Button(trim_frame, text="Set End", command=self.set_trim_end).pack(side="left", fill="x", expand=True)
        ttk.Button(trim_frame, text="Apply Trim", command=self.apply_trim).pack(side="left", fill="x", expand=True)
        
        # Cut controls
        cut_frame = ttk.Frame(control_frame)
        cut_frame.pack(fill="x", pady=5)
        
        ttk.Button(cut_frame, text="Mark Cut Start", command=self.mark_cut_start).pack(side="left", fill="x", expand=True)
        ttk.Button(cut_frame, text="Mark Cut End", command=self.mark_cut_end).pack(side="left", fill="x", expand=True)
        ttk.Button(cut_frame, text="Apply Cuts", command=self.apply_cuts).pack(side="left", fill="x", expand=True)
        
        # Timeline slider
        self.timeline = ttk.Scale(control_frame, from_=0, to=100, command=self.on_timeline_scroll)
        self.timeline.pack(fill="x", pady=5)
        
        # Video preview canvas
        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(side="right", fill="both", expand=True)
        
        # Status bar
        self.status_bar = ttk.Label(self, text="Ready", relief="sunken")
        self.status_bar.pack(side="bottom", fill="x")
        
    def browse_videos(self):
        folder = filedialog.askdirectory()
        if not folder: return
        
        self.video_list.delete(0, tk.END)
        for f in sorted(os.listdir(folder)):
            if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                self.video_list.insert(tk.END, f)
        
        self.video_folder = folder
    
    def load_video(self, event):
        selection = self.video_list.curselection()
        if not selection: return
        
        self.stop_playback()
        
        video_file = self.video_list.get(selection[0])
        video_path = os.path.join(self.video_folder, video_file)
        
        try:
            self.video_cap = cv2.VideoCapture(video_path)
            if not self.video_cap.isOpened():
                raise ValueError("Could not open video")
            
            self.video_frame_count = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.video_fps = self.video_cap.get(cv2.CAP_PROP_FPS)
            width = int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            self.trim_start = 0
            self.trim_end = self.video_frame_count - 1
            self.cut_ranges = []
            
            self.video_info.config(text=f"{video_file}\n{width}x{height} | {self.video_fps:.1f}fps\nFrames: {self.video_frame_count}")
            self.timeline.config(to=self.video_frame_count-1)
            
            self.seek_video(0)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load video:\n{str(e)}")
    
    def toggle_playback(self):
        if not self.video_cap: return
        
        if self.video_playing:
            self.stop_playback()
            self.play_btn.config(text="▶")
        else:
            self.video_playing = True
            self.play_btn.config(text="⏸")
            self.play_video()
    
    def play_video(self):
        if not self.video_playing or not self.video_cap:
            return
        
        ret, frame = self.video_cap.read()
        if not ret:
            self.stop_playback()
            return
        
        self.video_current_frame = int(self.video_cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.timeline.set(self.video_current_frame)
        
        # Display frame
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        img = self.resize_image(img)
        self.tkimg = ImageTk.PhotoImage(image=img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tkimg)
        
        # Schedule next frame
        delay = int(1000 / self.video_fps)
        self.video_update_id = self.after(delay, self.play_video)
    
    def stop_playback(self):
        self.video_playing = False
        if self.video_update_id:
            self.after_cancel(self.video_update_id)
            self.video_update_id = None
    
    def seek_video(self, seconds):
        if not self.video_cap: return
        
        self.stop_playback()
        frame_offset = int(seconds * self.video_fps)
        new_frame = max(0, min(self.video_frame_count-1, 
                         self.video_current_frame + frame_offset))
        
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, new_frame)
        ret, frame = self.video_cap.read()
        
        if ret:
            self.video_current_frame = new_frame
            self.timeline.set(new_frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img = self.resize_image(img)
            self.tkimg = ImageTk.PhotoImage(image=img)
            self.canvas.create_image(0, 0, anchor="nw", image=self.tkimg)
    
    def rewind_to_start(self):
        self.seek_video(-self.video_current_frame / self.video_fps)
    
    def on_timeline_scroll(self, value):
        if not self.video_cap: return
        
        frame_pos = int(float(value))
        if frame_pos == self.video_current_frame:
            return
        
        self.stop_playback()
        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
        ret, frame = self.video_cap.read()
        
        if ret:
            self.video_current_frame = frame_pos
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img = self.resize_image(img)
            self.tkimg = ImageTk.PhotoImage(image=img)
            self.canvas.create_image(0, 0, anchor="nw", image=self.tkimg)
    
    def set_trim_start(self):
        self.trim_start = self.video_current_frame
        self.status_bar.config(text=f"Trim start set to frame {self.trim_start}")
    
    def set_trim_end(self):
        self.trim_end = self.video_current_frame
        self.status_bar.config(text=f"Trim end set to frame {self.trim_end}")
    
    def apply_trim(self):
        if not self.video_cap: return
        
        if self.trim_start >= self.trim_end:
            messagebox.showerror("Error", "Trim start must be before trim end")
            return
        
        # Create trimmed video
        output_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("AVI", "*.avi")]
        )
        
        if not output_path: return
        
        # Get video properties
        width = int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.video_cap.get(cv2.CAP_PROP_FPS)
        
        # Create progress window
        progress_win = tk.Toplevel(self)
        progress_win.title("Trimming Video")
        ttk.Label(progress_win, text="Processing...").pack(padx=20, pady=5)
        progress = ttk.Progressbar(progress_win, maximum=self.trim_end-self.trim_start)
        progress.pack(padx=20, pady=5)
        progress_win.grab_set()
        self.update()
        
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.trim_start)
            
            for frame_num in range(self.trim_start, self.trim_end + 1):
                ret, frame = self.video_cap.read()
                if not ret: break
                
                out.write(frame)
                progress['value'] = frame_num - self.trim_start
                progress_win.update()
            
            out.release()
            messagebox.showinfo("Success", f"Trimmed video saved to {output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to trim video:\n{str(e)}")
        finally:
            progress_win.destroy()
            self.seek_video(0)
    
    def mark_cut_start(self):
        self.cut_ranges.append({"start": self.video_current_frame, "end": -1})
        self.status_bar.config(text=f"Cut start marked at frame {self.video_current_frame}")
    
    def mark_cut_end(self):
        if not self.cut_ranges or self.cut_ranges[-1]["end"] != -1:
            messagebox.showerror("Error", "No active cut range to mark end")
            return
        
        if self.video_current_frame <= self.cut_ranges[-1]["start"]:
            messagebox.showerror("Error", "Cut end must be after cut start")
            return
        
        self.cut_ranges[-1]["end"] = self.video_current_frame
        self.status_bar.config(text=f"Cut end marked at frame {self.video_current_frame}")
    
    def apply_cuts(self):
        if not self.video_cap or not self.cut_ranges:
            messagebox.showerror("Error", "No cuts marked")
            return
        
        # Validate all cuts
        for cut in self.cut_ranges:
            if cut["end"] == -1:
                messagebox.showerror("Error", "Incomplete cut range detected")
                return
        
        output_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4", "*.mp4"), ("AVI", "*.avi")]
        )
        
        if not output_path: return
        
        # Get video properties
        width = int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.video_cap.get(cv2.CAP_PROP_FPS)
        
        # Create progress window
        progress_win = tk.Toplevel(self)
        progress_win.title("Applying Cuts")
        ttk.Label(progress_win, text="Processing...").pack(padx=20, pady=5)
        progress = ttk.Progressbar(progress_win)
        progress.pack(padx=20, pady=5)
        progress_win.grab_set()
        self.update()
        
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # Sort cuts by start frame
            sorted_cuts = sorted(self.cut_ranges, key=lambda x: x["start"])
            
            # Determine segments to keep (between cuts)
            keep_segments = []
            prev_end = 0
            
            for cut in sorted_cuts:
                if cut["start"] > prev_end:
                    keep_segments.append({"start": prev_end, "end": cut["start"]-1})
                prev_end = cut["end"] + 1
            
            if prev_end < self.video_frame_count - 1:
                keep_segments.append({"start": prev_end, "end": self.video_frame_count-1})
            
            # Calculate total frames to process for progress bar
            total_frames = sum(seg["end"] - seg["start"] + 1 for seg in keep_segments)
            progress.config(maximum=total_frames)
            
            # Process each segment
            processed_frames = 0
            for seg in keep_segments:
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, seg["start"])
                
                for frame_num in range(seg["start"], seg["end"] + 1):
                    ret, frame = self.video_cap.read()
                    if not ret: break
                    
                    out.write(frame)
                    processed_frames += 1
                    progress['value'] = processed_frames
                    progress_win.update()
            
            out.release()
            messagebox.showinfo("Success", f"Video with cuts applied saved to {output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply cuts:\n{str(e)}")
        finally:
            progress_win.destroy()
            self.seek_video(0)
    
    def resize_image(self, img):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return img
        
        img_ratio = img.width / img.height
        canvas_ratio = canvas_width / canvas_height
        
        if canvas_ratio > img_ratio:
            new_height = canvas_height
            new_width = int(new_height * img_ratio)
        else:
            new_width = canvas_width
            new_height = int(new_width / img_ratio)
        
        return img.resize((new_width, new_height), Image.LANCZOS)

if __name__ == "__main__":
    app = VideoEditorToolkit()
    app.mainloop()