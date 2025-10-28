#!/usr/bin/env python3
"""
CAN Control with Video Monitor
"""

import cv2
import tkinter as tk
from tkinter import ttk, scrolledtext
from PIL import Image, ImageTk
import os
import subprocess
import threading
import time
from datetime import datetime
import can


class CANVideoControl:
    def __init__(self, root):
        self.root = root
        self.root.title("Drive assist debug")
        self.root.configure(bg='#2b2b2b')
        self.root.geometry("1000x550")
        self.root.resizable(False, False)
        
        # Video settings
        self.video_device = '/dev/video6'
        self.video_running = True
        
        # CAN settings
        self.can_interface = "can0"
        self.can_running = False
        self.can_bus = None
        
        # CAN states
        self.fonte1_enabled = tk.BooleanVar(value=False)
        self.fonte1_state = tk.BooleanVar(value=False)
        self.fonte2_enabled = tk.BooleanVar(value=False)
        self.fonte2_state = tk.BooleanVar(value=False)
        self.fonte3_enabled = tk.BooleanVar(value=False)
        self.fonte3_state = tk.BooleanVar(value=False)
        self.turn_signal_enabled = tk.BooleanVar(value=False)
        self.turn_signal_state = tk.StringVar(value="None")
        self.turn_light_left_enabled = tk.BooleanVar(value=False)
        self.turn_light_left_state = tk.BooleanVar(value=False)
        self.turn_light_right_enabled = tk.BooleanVar(value=False)
        self.turn_light_right_state = tk.BooleanVar(value=False)
        self.hazard_switch_enabled = tk.BooleanVar(value=False)
        self.hazard_switch_state = tk.BooleanVar(value=False)
        
        self.setup_ui()
        self.start_video_thread()
        
    def setup_ui(self):
        # Main container
        container = tk.Frame(self.root, bg='#2b2b2b')
        container.pack(fill="both", expand=True)
        
        # Left side - CAN Control
        can_frame = tk.Frame(container, bg='#2b2b2b', padx=10, pady=10)
        can_frame.pack(side="left", fill="y")
        
        self.state_checks = []
        
        # Reverse Group
        reverse_frame = ttk.LabelFrame(can_frame, text="Reverse", padding=5)
        reverse_frame.pack(fill="x", pady=3)
        
        self.create_source_control(reverse_frame, "Switch", self.fonte1_enabled, self.fonte1_state)
        self.create_source_control(reverse_frame, "Gear", self.fonte2_enabled, self.fonte2_state)
        self.create_source_control(reverse_frame, "Lights", self.fonte3_enabled, self.fonte3_state)
        
        # Turn Group
        turn_frame = ttk.LabelFrame(can_frame, text="Turn", padding=5)
        turn_frame.pack(fill="x", pady=3)
        
        # Turn signal with combo
        ts_frame = ttk.Frame(turn_frame)
        ts_frame.pack(fill="x", pady=2)
        ttk.Checkbutton(ts_frame, text="Switch", variable=self.turn_signal_enabled, 
                       command=self.update_ui_state).pack(side="left")
        self.turn_signal_combo = ttk.Combobox(ts_frame, textvariable=self.turn_signal_state,
                                             values=["None", "Left", "Right"], state="disabled", width=6)
        self.turn_signal_combo.pack(side="left", padx=5)
        
        self.create_source_control(turn_frame, "Left Light", self.turn_light_left_enabled, self.turn_light_left_state)
        self.create_source_control(turn_frame, "Right Light", self.turn_light_right_enabled, self.turn_light_right_state)
        
        # Hazard Group
        hazard_frame = ttk.LabelFrame(can_frame, text="Hazard", padding=5)
        hazard_frame.pack(fill="x", pady=3)
        
        self.create_source_control(hazard_frame, "Switch", self.hazard_switch_enabled, self.hazard_switch_state)
        
        # Control button
        self.start_button = ttk.Button(can_frame, text="Start Sending", command=self.toggle_sending)
        self.start_button.pack(fill="x", pady=3)
        
        # Log
        log_frame = ttk.LabelFrame(can_frame, text="Log", padding=3)
        log_frame.pack(fill="both", expand=True, pady=3)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=35, state="disabled", wrap="word", font=('Arial', 8))
        self.log_text.pack(fill="both", expand=True)
        
        ttk.Button(log_frame, text="Clear", command=self.clear_log).pack(fill="x", pady=(3, 0))
        
        # Right side - Video
        video_frame = tk.Frame(container, bg='#2b2b2b', padx=10, pady=10)
        video_frame.pack(side="right", fill="both", expand=True)
        
        self.img_label = tk.Label(video_frame, bg='black', width=640, height=480)
        self.img_label.pack()
        
        self.video_status = tk.Label(
            video_frame, 
            text="Initializing...", 
            bg='#2b2b2b', 
            fg='yellow',
            font=('Arial', 9)
        )
        self.video_status.pack(pady=5)
    
    def create_source_control(self, parent, label, enabled_var, state_var):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=1)
        ttk.Checkbutton(frame, text=label, variable=enabled_var, 
                       command=self.update_ui_state).pack(side="left")
        check = ttk.Checkbutton(frame, text="ON", variable=state_var, state="disabled")
        check.pack(side="left", padx=3)
        self.state_checks.append((enabled_var, check))
    
    def update_ui_state(self):
        for enabled_var, check in self.state_checks:
            check.config(state="normal" if enabled_var.get() else "disabled")
        self.turn_signal_combo.config(state="readonly" if self.turn_signal_enabled.get() else "disabled")
    
    def log_message(self, message):
        self.log_text.config(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
    
    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
    
    def capture_video(self):
        """Video capture thread"""
        while self.video_running:
            if not os.path.exists(self.video_device):
                self.video_status.config(text="Video not available", fg='red')
                time.sleep(1)
                continue
            
            cap = None
            try:
                cap = cv2.VideoCapture(self.video_device, cv2.CAP_V4L2)
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    
                    if ret:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame)
                        imgtk = ImageTk.PhotoImage(image=img)
                        
                        self.img_label.config(image=imgtk)
                        self.img_label.image = imgtk
                        self.video_status.config(text=f"Updated: {datetime.now().strftime('%H:%M:%S')}", fg='green')
                    else:
                        self.video_status.config(text="No signal", fg='orange')
                else:
                    self.video_status.config(text="Failed to open camera", fg='red')
                    
            except Exception as e:
                self.video_status.config(text=f"Error: {str(e)}", fg='red')
            finally:
                if cap is not None:
                    cap.release()
            
            time.sleep(1)
    
    def start_video_thread(self):
        self.video_thread = threading.Thread(target=self.capture_video, daemon=True)
        self.video_thread.start()
    
    def init_can_bus(self):
        """Initialize CAN bus connection"""
        try:
            # Check if interface is UP
            result = subprocess.run(["ip", "link", "show", self.can_interface], 
                                   capture_output=True, text=True)
            if result.returncode == 0 and "UP" not in result.stdout:
                self.log_message(f"{self.can_interface} is not UP, running canup...")
                subprocess.run(["sudo", "ip", "link", "set", self.can_interface, "up", 
                              "type", "can", "bitrate", "500000", "loopback", "on"], check=True)
                subprocess.run(["sudo", "ifconfig", self.can_interface, "txqueuelen", "0"], check=True)
                self.log_message(f"{self.can_interface} configured successfully")
            
            self.can_bus = can.interface.Bus(channel=self.can_interface, interface='socketcan')
            self.log_message(f"CAN bus initialized on {self.can_interface}")
            return True
        except Exception as e:
            self.log_message(f"Error initializing CAN bus: {e}")
            return False
    
    def send_can_message(self, can_id, data):
        """Send CAN message using python-can"""
        if self.can_bus is None:
            return False
        
        try:
            # Convert hex string to bytes
            data_bytes = bytes.fromhex(data)
            
            # Convert hex string ID to integer
            arbitration_id = int(can_id, 16)
            
            # Create and send message
            msg = can.Message(
                arbitration_id=arbitration_id,
                data=data_bytes,
                is_extended_id=True
            )
            self.can_bus.send(msg)
            return True
        except Exception as e:
            self.log_message(f"Error sending CAN: {e}")
            return False
    
    def send_messages(self):
        if self.fonte1_enabled.get():
            data = "FF01FFFFFFFFFFFF" if self.fonte1_state.get() else "FF00FFFFFFFFFFFF"
            self.send_can_message("18FEC3FF", data)
        
        if self.fonte2_enabled.get():
            data = "FFFFFF1AFFFFFFFF" if self.fonte2_state.get() else "FFFFFFDBFFFFFFFF"
            self.send_can_message("18F005FF", data)
        
        if self.fonte3_enabled.get():
            data = "FFFF01FFFFFFFFFF" if self.fonte3_state.get() else "FFFF00FFFFFFFFFF"
            self.send_can_message("18FE41FF", data)
        
        if self.turn_signal_enabled.get():
            state = self.turn_signal_state.get()
            data_map = {"None": "FF00FFFFFFFFFFFF", "Left": "FF01FFFFFFFFFFFF", "Right": "FF02FFFFFFFFFFFF"}
            self.send_can_message("18FDCCFF", data_map.get(state, "FF00FFFFFFFFFFFF"))
        
        if self.turn_light_left_enabled.get() or self.turn_light_right_enabled.get():
            left = 1 if (self.turn_light_left_enabled.get() and self.turn_light_left_state.get()) else 0
            right = 1 if (self.turn_light_right_enabled.get() and self.turn_light_right_state.get()) else 0
            byte_val = (left << 2) | right
            self.send_can_message("18FE41FF", f"FF{byte_val:01X}FFFFFFFFFFFFF")
        
        if self.hazard_switch_enabled.get():
            val = 1 if self.hazard_switch_state.get() else 0
            self.send_can_message("18FDCCFF", f"FF{val:01X}FFFFFFFFFFFFF")
    
    def can_loop(self):
        while self.can_running:
            self.send_messages()
            time.sleep(1)
    
    def toggle_sending(self):
        if not self.can_running:
            if not any([self.fonte1_enabled.get(), self.fonte2_enabled.get(), self.fonte3_enabled.get(),
                       self.turn_signal_enabled.get(), self.turn_light_left_enabled.get(),
                       self.turn_light_right_enabled.get(), self.hazard_switch_enabled.get()]):
                self.log_message("Error: Enable at least one source")
                return
            
            # Initialize CAN bus
            if not self.init_can_bus():
                self.log_message("Failed to initialize CAN bus")
                return
            
            self.can_running = True
            self.start_button.config(text="Stop Sending")
            self.log_message("Started sending messages")
            
            self.can_thread = threading.Thread(target=self.can_loop, daemon=True)
            self.can_thread.start()
        else:
            self.can_running = False
            self.start_button.config(text="Start Sending")
            
            # Shutdown CAN bus
            if self.can_bus:
                self.can_bus.shutdown()
                self.can_bus = None
            
            self.log_message("Stopped sending messages")
    
    def cleanup(self):
        self.video_running = False
        self.can_running = False
        
        # Cleanup CAN bus
        if self.can_bus:
            self.can_bus.shutdown()
        
        self.root.destroy()


def main():
    root = tk.Tk()
    app = CANVideoControl(root)
    root.protocol("WM_DELETE_WINDOW", app.cleanup)
    root.mainloop()


if __name__ == "__main__":
    main()
