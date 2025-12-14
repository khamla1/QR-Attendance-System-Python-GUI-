import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import cv2
from pyzbar.pyzbar import decode
from PIL import Image, ImageTk
import threading
import time
from backend import Database, generate_qr_image
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

# --- Configuration ---
BG_COLOR = "#1e1e2e"
SIDEBAR_COLOR = "#252538"
ACCENT_COLOR = "#00adb5"
TEXT_COLOR = "#eeeeee"
CARD_COLOR = "#2d2d44"
SUCCESS_COLOR = "#4caf50"
ERROR_COLOR = "#f44336"
WARNING_COLOR = "#ff9800"

# Fonts
# "DokChampa" is the standard Lao font on Windows.
FONT_HEADER = ("DokChampa", 24, "bold")
FONT_SUBHEADER = ("DokChampa", 16)
FONT_BODY = ("DokChampa", 12)
FONT_BUTTON = ("DokChampa", 12, "bold")

class AttendanceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ລະບົບເຊັກຊື່ (Teacher Scans Student)")
        self.geometry("1100x750")
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)
        
        # Force Font for everything
        self.option_add("*Font", "DokChampa 12")
        self.option_add("*Treeview.Heading.Font", "DokChampa 12 bold")

        self.db = Database()

        # State Variables
        self.current_mode = None
        self.camera_running = False
        self.cap = None
        self.video_thread = None
        self.last_scan_time = 0
        self.scan_cooldown = 3.0
        
        # Session Variables
        self.active_course = ""
        self.active_room = ""
        
        # History filter
        self.history_filter_subject = None

        self.setup_styles()
        self.create_layout()
        self.show_teacher_mode()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Main.TFrame", background=BG_COLOR)
        style.configure("Sidebar.TFrame", background=SIDEBAR_COLOR)
        style.configure("Card.TFrame", background=CARD_COLOR, relief="flat")
        
        style.configure("Header.TLabel", background=BG_COLOR, foreground=ACCENT_COLOR, font=FONT_HEADER)
        style.configure("SubHeader.TLabel", background=CARD_COLOR, foreground=TEXT_COLOR, font=FONT_SUBHEADER)
        style.configure("Body.TLabel", background=CARD_COLOR, foreground=TEXT_COLOR, font=FONT_BODY)
        style.configure("Status.TLabel", background=CARD_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 14, "bold"))
        
        style.configure("Sidebar.TButton", background=SIDEBAR_COLOR, foreground="white", font=FONT_BUTTON, borderwidth=0)
        style.map("Sidebar.TButton", background=[("active", ACCENT_COLOR)], foreground=[("active", "white")])
        
        style.configure("Action.TButton", background=ACCENT_COLOR, foreground="white", font=FONT_BUTTON)
        style.map("Action.TButton", background=[("active", "#007y7a")])
        
        style.configure("Danger.TButton", background=ERROR_COLOR, foreground="white", font=FONT_BUTTON)
        style.configure("Success.TButton", background=SUCCESS_COLOR, foreground="white", font=FONT_BUTTON)

    def create_layout(self):
        self.sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=250)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        title_lbl = tk.Label(self.sidebar, text="ລະບົບ\nເຊັກຊື່", bg=SIDEBAR_COLOR, fg=ACCENT_COLOR, font=("DokChampa", 28, "bold"), pady=40)
        title_lbl.pack()

        ttk.Button(self.sidebar, text="🎓 ໂຫມດອາຈານ (Scan)", style="Sidebar.TButton", command=self.show_teacher_mode).pack(fill="x", pady=10, ipady=10)
        ttk.Button(self.sidebar, text="👨‍🎓 ໂຫມດນັກຮຽນ (QR)", style="Sidebar.TButton", command=self.show_student_mode).pack(fill="x", pady=10, ipady=10)
        ttk.Button(self.sidebar, text="📊 ປະຫວັດ (History)", style="Sidebar.TButton", command=self.show_history_mode).pack(fill="x", pady=10, ipady=10)
        ttk.Button(self.sidebar, text="📈 ສະຖິຕິ (Graph)", style="Sidebar.TButton", command=self.show_stats_mode).pack(fill="x", pady=10, ipady=10)

        self.content_area = ttk.Frame(self, style="Main.TFrame")
        self.content_area.pack(side="right", fill="both", expand=True)

    def clear_content(self):
        self.stop_camera()
        for widget in self.content_area.winfo_children():
            widget.destroy()

    # ==========================
    # TEACHER MODE (Scanner)
    # ==========================
    def show_teacher_mode(self):
        self.clear_content()
        self.current_mode = "Teacher"
        
        ttk.Label(self.content_area, text="ອາຈານ: ເປີດຫ້ອງຮຽນ & ສະແກນ", style="Header.TLabel").pack(pady=20)
        
        # Container
        container = tk.Frame(self.content_area, bg=BG_COLOR)
        container.pack(fill="both", expand=True, padx=40)
        
        # Left: Controls
        control_frame = ttk.Frame(container, style="Card.TFrame", padding=20)
        control_frame.pack(side="left", fill="y", padx=(0, 20))
        
        ttk.Label(control_frame, text="ຕັ້ງຄ່າຫ້ອງຮຽນ", style="SubHeader.TLabel").pack(pady=(0, 20))
        
        # Subject Combobox with Add/Delete Button
        ttk.Label(control_frame, text="ເລືອກວິຊາ (Subject):", style="Body.TLabel").pack(anchor="w", pady=(15, 5))
        
        sub_frame = tk.Frame(control_frame, bg=CARD_COLOR)
        sub_frame.pack(fill="x")
        
        self.combo_course = ttk.Combobox(sub_frame, font=FONT_BODY, width=20, state="readonly")
        self.combo_course.pack(side="left", fill="x", expand=True)
        self.refresh_subjects()
        
        btn_add_sub = ttk.Button(sub_frame, text="+", width=3, command=self.add_subject_popup)
        btn_add_sub.pack(side="left", padx=5)
        
        btn_del_sub = ttk.Button(sub_frame, text="-", width=3, command=self.delete_subject_action)
        btn_del_sub.pack(side="left", padx=5)
        
        self.create_label_entry(control_frame, "ຫ້ອງຮຽນ (Room):", "entry_room")
        
        # Actions
        self.btn_action = ttk.Button(control_frame, text="ເປີດກ້ອງ (Start Scan)", style="Action.TButton", command=self.toggle_camera_teacher)
        self.btn_action.pack(pady=30, fill="x")
        
        btn_upload = ttk.Button(control_frame, text="ອັບໂຫລດຮູບ (Upload QR)", style="Sidebar.TButton", command=self.upload_qr_teacher_action)
        btn_upload.pack(pady=10, fill="x")
        
        # Status
        self.lbl_status = tk.Label(control_frame, text="ກະລຸນາເລືອກວິຊາ/ຫ້ອງ ແລະກົດເປີດກ້ອງ", bg=CARD_COLOR, fg="#888", font=("Segoe UI", 12), wraplength=200)
        self.lbl_status.pack(pady=20)
        
        # Right: Camera
        self.cam_frame = tk.Frame(container, bg="black", width=640, height=480)
        self.cam_frame.pack(side="right", fill="both", expand=True)
        self.lbl_video = tk.Label(self.cam_frame, bg="black", text="Camera OFF", fg="white")
        self.lbl_video.pack(fill="both", expand=True)

    def refresh_subjects(self):
        subs = self.db.get_subjects()
        self.combo_course['values'] = subs
        if subs:
            self.combo_course.current(0)
        else:
            self.combo_course.set("")

    def add_subject_popup(self):
        new_sub = simpledialog.askstring("ເພີ່ມວິຊາ", "ກະລຸນາປ້ອນຊື່ວິຊາ:")
        if new_sub:
            if self.db.add_subject(new_sub):
                messagebox.showinfo("Success", f"ເພີ່ມວິຊາ {new_sub} ສຳເລັດ")
                self.refresh_subjects()
            else:
                messagebox.showerror("Error", "ເພີ່ມບໍ່ໄດ້ (ອາດຈະຊ້ຳ)")
    
    def delete_subject_action(self):
        selected = self.combo_course.get()
        if not selected: return
        if messagebox.askyesno("Confirm", f"ຕ້ອງການລົບວິຊາ {selected} ຫຼືບໍ່?"):
            self.db.delete_subject(selected)
            self.refresh_subjects()

    def toggle_camera_teacher(self):
        if self.camera_running:
            self.stop_camera()
            self.btn_action.config(text="ເປີດກ້ອງ (Start Scan)")
            self.lbl_status.config(text="ກ້ອງປິດແລ້ວ", fg="#888")
        else:
            course = self.combo_course.get()
            room = self.entry_room.get().strip()
            if not course or not room:
                messagebox.showwarning("Warning", "ກະລຸນາເລືອກວິຊາ ແລະ ຫ້ອງຮຽນ!")
                return
            self.active_course = course
            self.active_room = room
            self.start_camera()
            self.btn_action.config(text="ປິດກ້ອງ (Stop Scan)")
            self.lbl_status.config(text=f"ກຳລັງສະແກນ...\n{course} @ {room}", fg=ACCENT_COLOR)

    def upload_qr_teacher_action(self):
        course = self.combo_course.get()
        room = self.entry_room.get().strip()
        if not course or not room:
            messagebox.showwarning("Warning", "ກະລຸນາເລືອກວິຊາ ແລະ ຫ້ອງຮຽນກ່ອນອັບໂຫລດ!")
            return
        self.active_course = course
        self.active_room = room
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if not file_path: return
        try:
            img = Image.open(file_path)
            decoded = decode(img)
            if decoded:
                for obj in decoded:
                    raw = obj.data.decode("utf-8")
                    self.handle_scanned_data(raw)
                    return
            self.update_status("Scan Failed: No QR found", WARNING_COLOR)
        except Exception as e:
            self.update_status(f"Error: {e}", ERROR_COLOR)

    # ==========================
    # STUDENT MODE
    # ==========================
    def show_student_mode(self):
        self.clear_content()
        self.current_mode = "Student"
        
        ttk.Label(self.content_area, text="ນັກຮຽນ: ສ້າງ QR ບັດປະຈຳຕົວ", style="Header.TLabel").pack(pady=20)
        
        card = ttk.Frame(self.content_area, style="Card.TFrame", padding=30)
        card.pack(pady=20, padx=100, fill="both")
        
        input_frame = tk.Frame(card, bg=CARD_COLOR)
        input_frame.pack(side="left", fill="both", expand=True, padx=20)
        
        self.create_label_entry(input_frame, "ລະຫັດນັກສຶກສາ (ID):", "entry_std_id")
        self.create_label_entry(input_frame, "ຊື່-ນາມສະກຸນ (Name):", "entry_std_name")
        
        bbox = ttk.Button(input_frame, text="ສ້າງ QR Code", style="Action.TButton", command=self.generate_student_qr)
        bbox.pack(pady=30, fill="x")
        
        self.qr_display_frame = tk.Frame(card, bg="white", width=300, height=300)
        self.qr_display_frame.pack(side="right", padx=20)
        self.qr_display_frame.pack_propagate(False)
        self.lbl_qr_image = tk.Label(self.qr_display_frame, text="QR Code ຈະສະແດງຢູ່ບ່ອນນີ້", bg="white", fg="#888")
        self.lbl_qr_image.place(relx=0.5, rely=0.5, anchor="center")

    def generate_student_qr(self):
        sid = self.entry_std_id.get().strip()
        name = self.entry_std_name.get().strip()
        if not sid or not name:
            messagebox.showwarning("Error", "Please fill all fields")
            return
        data = f"{sid}|{name}"
        img = generate_qr_image(data)
        img = img.resize((280, 280))
        self.tk_qr_img = ImageTk.PhotoImage(img)
        self.lbl_qr_image.config(image=self.tk_qr_img, text="")
        self.lbl_qr_image.image = self.tk_qr_img
        messagebox.showinfo("Success", "QR Code ພ້ອມໃຊ້ງານ! ຢື່ນໃຫ້ອາຈານສະແກນໄດ້ເລີຍ")

    # ==========================
    # HISTORY MODE
    # ==========================
    def show_history_mode(self):
        self.clear_content()
        self.current_mode = "History"
        ttk.Label(self.content_area, text="ປະຫວັດການເຂົ້າຮຽນ (ມື້ນີ້)", style="Header.TLabel").pack(pady=20)
        
        # Controls Frame (Filter)
        ctrl_frame = ttk.Frame(self.content_area, style="Card.TFrame", padding=10)
        ctrl_frame.pack(fill="x", padx=40)
        
        ttk.Label(ctrl_frame, text="ຄັດກອງຕາມວິຊາ:", style="Body.TLabel").pack(side="left")
        
        self.history_combo = ttk.Combobox(ctrl_frame, font=FONT_BODY, width=20, state="readonly")
        subs = ["All"] + self.db.get_subjects()
        self.history_combo['values'] = subs
        self.history_combo.current(0)
        self.history_combo.pack(side="left", padx=10)
        
        if self.history_filter_subject:
             # Try to restore selection
             if self.history_filter_subject in subs:
                 self.history_combo.set(self.history_filter_subject)
        
        btn_filter = ttk.Button(ctrl_frame, text="Filter", command=self.refresh_history_table)
        btn_filter.pack(side="left")

        # Table
        table_frame = ttk.Frame(self.content_area, style="Card.TFrame", padding=20)
        table_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        cols = {
            "ID_DB": "ID (Hidden)",
            "Time": "ເວລາ (Time)", 
            "ID": "ລະຫັດ (ID)", 
            "Name": "ຊື່ (Name)", 
            "Course": "ວິຊາ (Subject)", 
            "Room": "ຫ້ອງ (Room)"
        }
        
        columns_list = list(cols.keys())
        self.tree = ttk.Treeview(table_frame, columns=columns_list, show="headings", height=15)
        
        for col_id, text in cols.items():
            self.tree.heading(col_id, text=text)
            self.tree.column(col_id, width=120)
        
        self.tree.column("ID_DB", width=0, stretch=tk.NO)
        self.tree.pack(fill="both", expand=True)
        
        # Buttons
        btn_frame = tk.Frame(table_frame, bg=CARD_COLOR)
        btn_frame.pack(fill="x", pady=10)
        
        btn_del = ttk.Button(btn_frame, text="ລົບຂໍ້ມູນ (Delete)", style="Danger.TButton", command=self.delete_selected_history)
        btn_del.pack(side="right", padx=5)
        
        btn_export = ttk.Button(btn_frame, text="Export Excel", style="Success.TButton", command=self.export_to_excel)
        btn_export.pack(side="right", padx=5)
        
        self.refresh_history_table()

    def refresh_history_table(self):
        # Clear
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        subject = self.history_combo.get()
        if subject == "All": subject = None
        self.history_filter_subject = subject
        
        today = datetime.now().strftime("%Y-%m-%d")
        records = self.db.get_attendance_by_date(today, subject=subject)
        self.current_records = records
        
        for r in records:
            t_str = r[5].split(" ")[1] if " " in r[5] else r[5]
            stats = self.db.get_student_stats(r[1])
            name_display = f"{r[2]} ({stats} ຄັ້ງ)"
            self.tree.insert("", "end", values=(r[0], t_str, r[1], name_display, r[3], r[4]))

    def delete_selected_history(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "ກະລຸນາເລືອກແຖວທີ່ຕ້ອງການລົບ")
            return
            
        if messagebox.askyesno("Confirm", "ຕ້ອງການລົບຂໍ້ມູນນີ້ຫຼືບໍ່?"):
            for item in selected:
                vals = self.tree.item(item, 'values')
                db_id = vals[0]
                self.db.delete_attendance(db_id)
            self.refresh_history_table()

    def export_to_excel(self):
        if not hasattr(self, 'current_records') or not self.current_records:
            messagebox.showwarning("Warning", "ບໍ່ມີຂໍ້ມູນໃຫ້ Export")
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")])
        if not file_path: return
        
        # Prepare Data for Pandas
        data = []
        for r in self.current_records:
            # r: (id, std_id, name, course, room, date_time)
            data.append({
                "Student ID": r[1],
                "Name": r[2],
                "Course": r[3],
                "Room": r[4],
                "Date Time": r[5]
            })
            
        df = pd.DataFrame(data)
        try:
            # Explicitly use openpyxl engine
            df.to_excel(file_path, index=False, engine='openpyxl')
            messagebox.showinfo("Success", f"Export ສຳເລັດ!\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

    # ==========================
    # STATISTICS MODE (Matplotlib)
    # ==========================
    def show_stats_mode(self):
        self.clear_content()
        self.current_mode = "Stats"
        
        ttk.Label(self.content_area, text="ສະຖິຕິການເຂົ້າຮຽນ (Statistics)", style="Header.TLabel").pack(pady=20)

        # Control Frame
        ctrl_frame = ttk.Frame(self.content_area, style="Card.TFrame", padding=20)
        ctrl_frame.pack(fill="x", padx=40)
        
        ttk.Label(ctrl_frame, text="ເລືອກວິຊາເພື່ອເບິ່ງກຣາຟ:", style="Body.TLabel").pack(side="left")
        
        self.combo_stats = ttk.Combobox(ctrl_frame, font=FONT_BODY, width=20, state="readonly")
        self.combo_stats['values'] = self.db.get_subjects()
        self.combo_stats.pack(side="left", padx=10)
        if self.combo_stats['values']: self.combo_stats.current(0)
        
        btn_show = ttk.Button(ctrl_frame, text="ສະແດງກຣາຟ", style="Action.TButton", command=self.render_graph)
        btn_show.pack(side="left")

        # Graph Canvas
        self.graph_frame = tk.Frame(self.content_area, bg="white")
        self.graph_frame.pack(fill="both", expand=True, padx=40, pady=20)

    def render_graph(self):
        subject = self.combo_stats.get()
        if not subject: return
        
        # Clear previous graph
        for widget in self.graph_frame.winfo_children():
            widget.destroy()
            
        # Get data
        data = self.db.get_subject_stats(subject) # [(name, count), ...]
        
        if not data:
            tk.Label(self.graph_frame, text="ບໍ່ມີຂໍ້ມູນສຳລັບວິຊານີ້", font=FONT_HEADER, bg="white").pack(pady=50)
            return
            
        # Prepare Data for Plot
        names = [d[0] for d in data[:10]] # Top 10
        counts = [d[1] for d in data[:10]]
        
        # Create Plot
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(names, counts, color="#00adb5")
        ax.set_title(f"Attendance Stats: {subject}")
        ax.set_ylabel("Check-in Count")
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ==========================
    # HELPERS
    # ==========================
    def create_label_entry(self, parent, text, attr_name):
        lbl = ttk.Label(parent, text=text, style="Body.TLabel")
        lbl.pack(anchor="w", pady=(15, 5))
        entry = ttk.Entry(parent, font=FONT_BODY, width=30)
        entry.pack(fill="x")
        setattr(self, attr_name, entry)
        
    def update_status(self, text, color):
        self.lbl_status.after(0, lambda: self.lbl_status.config(text=text, fg=color))

    # ==========================
    # CAMERA LOGIC
    # ==========================
    def start_camera(self):
        if self.camera_running: return
        self.camera_running = True
        self.video_thread = threading.Thread(target=self.video_loop, daemon=True)
        self.video_thread.start()

    def stop_camera(self):
        self.camera_running = False
        if self.cap:
            self.cap.release()
        self.cap = None

    def video_loop(self):
        self.cap = cv2.VideoCapture(0)
        while self.camera_running:
            ret, frame = self.cap.read()
            if ret:
                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv2image)
                imgtk = ImageTk.PhotoImage(image=img)
                self.lbl_video.after(0, lambda i=imgtk: self.lbl_video.config(image=i) or setattr(self.lbl_video, 'image', i))
                
                # Scan Logic
                current_time = time.time()
                if current_time - self.last_scan_time > self.scan_cooldown:
                    decoded = decode(frame)
                    for obj in decoded:
                        raw = obj.data.decode("utf-8")
                        self.handle_scanned_data(raw)
                        self.last_scan_time = current_time
                        break
            time.sleep(0.03)

    def handle_scanned_data(self, data):
        try:
            parts = data.split('|')
            if len(parts) >= 2:
                std_id = parts[0]
                std_name = parts[1]
                
                success, msg = self.db.save_attendance(std_id, std_name, self.active_course, self.active_room)
                
                if success:
                    self.update_status(f"✓ {msg}\n({std_name})", SUCCESS_COLOR)
                else:
                    self.update_status(f"⚠ {msg}\n({std_name})", WARNING_COLOR)
            else:
                self.update_status("Invalid QR Format", ERROR_COLOR)
        except Exception as e:
            print(e)

if __name__ == "__main__":
    app = AttendanceApp()
    app.mainloop()
