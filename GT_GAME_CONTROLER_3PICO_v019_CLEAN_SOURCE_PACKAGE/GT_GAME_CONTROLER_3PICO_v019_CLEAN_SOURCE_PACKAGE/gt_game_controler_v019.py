import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import serial
    from serial.tools import list_ports
except Exception:
    serial = None
    list_ports = None

APP_TITLE = "GT GAME CONTROLER v019"

HID_KEYS = {
    "KAPALI": 0x00,
    "1": 0x1E, "2": 0x1F, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
    "A": 0x04, "B": 0x05, "C": 0x06, "D": 0x07, "E": 0x08,
    "F": 0x09, "G": 0x0A, "H": 0x0B, "I": 0x0C, "J": 0x0D, "K": 0x0E,
    "L": 0x0F, "M": 0x10, "N": 0x11, "O": 0x12, "P": 0x13,
    "Q": 0x14, "R": 0x15, "S": 0x16, "T": 0x17, "U": 0x18,
    "V": 0x19, "W": 0x1A, "X": 0x1B, "Y": 0x1C, "Z": 0x1D,
    "ENTER": 0x28, "ESC": 0x29, "SPACE": 0x2C, "TAB": 0x2B,
    "F1": 0x3A, "F2": 0x3B, "F3": 0x3C, "F4": 0x3D, "F5": 0x3E,
    "F6": 0x3F, "F7": 0x40, "F8": 0x41, "F9": 0x42, "F10": 0x43,
    "F11": 0x44, "F12": 0x45,
}
KEY_CHOICES = list(HID_KEYS.keys())
KEY_PINS = [2,3,4,5,6,7,8,17,18,19,9,10,11,12,13,14,15,16,21,22,28]
DEFAULT_KEYMAP = {2:"1",3:"2",4:"3",5:"4",6:"5",7:"6",8:"7",17:"8",18:"9",19:"0",9:"A",10:"B",11:"C",12:"D",13:"E",14:"F",15:"G",16:"H",21:"I",22:"J",28:"K"}
GP_CHOICES = [f"GP{i}" for i in range(0, 29)]

class SerialDevice:
    def __init__(self, port, hello=""):
        self.port = port
        self.hello = hello.strip()
        self.kind = "UNKNOWN"
        self.player = ""
        self.ser = None
        self.running = False
        self.last_line = self.hello
        self.raw_x = self.raw_y = None
        self.hid_x = self.hid_y = None
        self.active = None
        self.cal = None
        self.filter_shift = None
        self.buttons = {}
        self.relays = {}
        self.cfg_text = ""
        self.relay_mode = "HIGH"
        self.p1_coin = "DRY"
        self.p2_coin = "DRY"
        self.p1_relay_pin = 26
        self.p2_relay_pin = 27
        self.p1_coin_pin = 17
        self.p2_coin_pin = 21
        self.classify(self.hello)

    def classify(self, text):
        if "HELLO,MOUSE,P1" in text or "STATUS,MOUSE,P1" in text:
            self.kind = "MOUSE"; self.player = "P1"
        elif "HELLO,MOUSE,P2" in text or "STATUS,MOUSE,P2" in text:
            self.kind = "MOUSE"; self.player = "P2"
        elif "HELLO,KEYBOARD" in text or "STATUS,KEYBOARD" in text or "GT_GAME_CONTROLER_CONTROLLER" in text:
            self.kind = "KEYBOARD"; self.player = "CONTROLLER"

    def open(self):
        self.ser = serial.Serial(self.port, 115200, timeout=0.05, write_timeout=0.2)
        try:
            self.ser.dtr = True
            self.ser.rts = True
        except Exception:
            pass
        self.running = True
        threading.Thread(target=self.reader, daemon=True).start()

    def close(self):
        self.running = False
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass

    def send(self, line):
        try:
            if self.ser:
                self.ser.write((line.strip()+"\n").encode("ascii", errors="ignore"))
        except Exception:
            pass

    def reader(self):
        while self.running:
            try:
                line = self.ser.readline().decode("ascii", errors="ignore").strip()
                if line:
                    self.parse_line(line)
            except Exception:
                time.sleep(0.1)

    def parse_line(self, line):
        self.last_line = line
        self.classify(line)
        parts = line.split(',')
        if not parts:
            return
        if parts[0] == "STATUS" and len(parts) >= 3 and parts[1] == "MOUSE":
            try:
                self.player = parts[2]
                i = 3
                while i < len(parts):
                    key = parts[i]
                    if key == "RAW": self.raw_x=int(parts[i+1]); self.raw_y=int(parts[i+2]); i+=3
                    elif key == "HID": self.hid_x=int(parts[i+1]); self.hid_y=int(parts[i+2]); i+=3
                    elif key == "ACTIVE": self.active=bool(int(parts[i+1])); i+=2
                    elif key == "CAL": self.cal=tuple(map(int, parts[i+1:i+5])); i+=5
                    elif key == "FILTER": self.filter_shift=int(parts[i+1]); i+=2
                    else: i+=1
            except Exception:
                pass
        elif parts[0] == "STATUS" and len(parts) >= 3 and parts[1] == "KEYBOARD":
            i = 3
            while i < len(parts):
                if parts[i] == "RELAYS" and i+2 < len(parts):
                    for item in parts[i+1:i+3]:
                        if ':' in item:
                            p, v = item.split(':',1); self.relays[p] = (v == '1')
                    i += 3
                elif parts[i] == "CFG":
                    self.cfg_text = line
                    i += 1
                elif ':' in parts[i]:
                    p, v = parts[i].split(':',1)
                    if p.isdigit(): self.buttons[p] = (v == '1')
                    i += 1
                else:
                    i += 1
            self.parse_config_from_text(line)
        elif parts[0] == "CONFIG":
            self.cfg_text = line
            self.parse_config_from_text(line)

    def parse_config_from_text(self, line):
        parts = line.replace(':', ',').split(',')
        try:
            for i, p in enumerate(parts):
                if p == "RELAY" and i+1 < len(parts): self.relay_mode = parts[i+1]
                if p == "P1COIN" and i+1 < len(parts): self.p1_coin = parts[i+1]
                if p == "P2COIN" and i+1 < len(parts): self.p2_coin = parts[i+1]
                if p == "RELAYPINS" and i+2 < len(parts):
                    self.p1_relay_pin = int(parts[i+1]); self.p2_relay_pin = int(parts[i+2])
                if p == "COINPINS" and i+2 < len(parts):
                    self.p1_coin_pin = int(parts[i+1]); self.p2_coin_pin = int(parts[i+2])
        except Exception:
            pass

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1250x820")
        self.minsize(1100, 720)
        self.devices = {}
        self.captures = {"P1": {}, "P2": {}}
        self.key_vars = {p: tk.StringVar(value=DEFAULT_KEYMAP[p]) for p in KEY_PINS}
        self.relay_mode = tk.StringVar(value="HIGH")
        self.p1_coin = tk.StringVar(value="DRY")
        self.p2_coin = tk.StringVar(value="DRY")
        self.p1_relay_gp = tk.StringVar(value="GP26")
        self.p2_relay_gp = tk.StringVar(value="GP27")
        self.p1_coin_gp = tk.StringVar(value="GP17")
        self.p2_coin_gp = tk.StringVar(value="GP21")
        self.controller_fields_dirty = False
        self.controller_loaded_once = False
        self.setup_style()
        self.create_ui()
        self.after(300, self.refresh_ui)

    def setup_style(self):
        self.configure(bg="#0f172a")
        self.style = ttk.Style(self)
        try: self.style.theme_use("clam")
        except Exception: pass
        self.style.configure("TFrame", background="#0f172a")
        self.style.configure("Card.TFrame", background="#1e293b", relief="flat")
        self.style.configure("TLabel", background="#0f172a", foreground="#e5e7eb", font=("Segoe UI", 10))
        self.style.configure("Card.TLabel", background="#1e293b", foreground="#e5e7eb", font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background="#0f172a", foreground="#38bdf8", font=("Segoe UI", 22, "bold"))
        self.style.configure("Sub.TLabel", background="#0f172a", foreground="#a7f3d0", font=("Segoe UI", 11, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=7)
        self.style.map("TButton", background=[("active", "#38bdf8")])
        self.style.configure("Accent.TButton", background="#22c55e", foreground="#07121f")
        self.style.configure("Warn.TButton", background="#f97316", foreground="#07121f")
        self.style.configure("TNotebook", background="#0f172a", borderwidth=0)
        self.style.configure("TNotebook.Tab", background="#334155", foreground="#e5e7eb", padding=(14, 8), font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", "#0ea5e9")], foreground=[("selected", "white")])
        self.style.configure("Treeview", background="#111827", foreground="#e5e7eb", fieldbackground="#111827", rowheight=28)
        self.style.configure("Treeview.Heading", background="#0ea5e9", foreground="white", font=("Segoe UI", 10, "bold"))
        self.style.configure("TLabelframe", background="#0f172a", foreground="#38bdf8")
        self.style.configure("TLabelframe.Label", background="#0f172a", foreground="#38bdf8", font=("Segoe UI", 11, "bold"))
        # Açık renkli combobox: gri kutu içinde yazılar net görünür.
        # Combobox yazıları gri kutu içinde kaybolmasın: açık zemin + siyah yazı.
        self.style.configure("TCombobox", fieldbackground="#f8fafc", background="#f8fafc", foreground="#000000", arrowcolor="#000000")
        self.style.map("TCombobox",
                       fieldbackground=[("readonly", "#f8fafc"), ("disabled", "#e5e7eb")],
                       foreground=[("readonly", "#000000"), ("disabled", "#111827")],
                       selectbackground=[("readonly", "#bfdbfe")],
                       selectforeground=[("readonly", "#000000")])
        self.option_add("*TCombobox*Listbox.background", "#ffffff")
        self.option_add("*TCombobox*Listbox.foreground", "#000000")
        self.option_add("*TCombobox*Listbox.selectBackground", "#0ea5e9")
        self.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    def create_ui(self):
        header = ttk.Frame(self, padding=12); header.pack(fill="x")
        ttk.Label(header, text="GT GAME CONTROLER", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="v019  |  3 Pico + canlı renkli test / kalibrasyon / röle ve coin pin ayar paneli", style="Sub.TLabel").pack(side="left", padx=16)
        ttk.Button(header, text="🔍 Cihazları Tara / Yenile", style="Accent.TButton", command=self.scan).pack(side="right")

        self.status = tk.StringVar(value="3 Pico'yu tak, sonra Cihazları Tara / Yenile yap.")
        ttk.Label(self, textvariable=self.status, padding=8, style="Sub.TLabel").pack(fill="x")

        list_frame = ttk.LabelFrame(self, text="Bağlı cihazlar", padding=8); list_frame.pack(fill="x", padx=10, pady=6)
        self.tree = ttk.Treeview(list_frame, columns=("port","type","hello"), show="headings", height=5)
        for c,t,w in [("port","Port",120),("type","Cihaz",190),("hello","Son cevap",820)]:
            self.tree.heading(c,text=t); self.tree.column(c,width=w)
        self.tree.pack(side="left", fill="x", expand=True)
        side = ttk.Frame(list_frame); side.pack(side="right", padx=6)
        ttk.Button(side, text="Seçiliyi P1 yap", command=lambda:self.force_selected("P1")).pack(fill="x", pady=2)
        ttk.Button(side, text="Seçiliyi P2 yap", command=lambda:self.force_selected("P2")).pack(fill="x", pady=2)
        ttk.Button(side, text="Seçiliyi Controller yap", command=lambda:self.force_selected("CONTROLLER")).pack(fill="x", pady=2)

        self.tabs = ttk.Notebook(self); self.tabs.pack(fill="both", expand=True, padx=10, pady=8)
        self.dev_tab=ttk.Frame(self.tabs); self.p1_tab=ttk.Frame(self.tabs); self.p2_tab=ttk.Frame(self.tabs)
        self.ctrl_tab=ttk.Frame(self.tabs); self.key_tab=ttk.Frame(self.tabs); self.relay_tab=ttk.Frame(self.tabs)
        self.tabs.add(self.dev_tab,text="📡 Cihaz Durumu")
        self.tabs.add(self.p1_tab,text="🎯 P1 Kalibrasyon")
        self.tabs.add(self.p2_tab,text="🎯 P2 Kalibrasyon")
        self.tabs.add(self.ctrl_tab,text="⚙ Controller Ayar")
        self.tabs.add(self.key_tab,text="⌨ Tuş Testi")
        self.tabs.add(self.relay_tab,text="⚡ Röle Testi")

        self.dev_text=tk.Text(self.dev_tab,font=("Consolas",11),bg="#020617",fg="#a7f3d0",insertbackground="white")
        self.dev_text.pack(fill="both",expand=True,padx=8,pady=8)
        self.make_mouse_tab(self.p1_tab,"P1"); self.make_mouse_tab(self.p2_tab,"P2")
        self.make_controller_tab(); self.make_key_tab(); self.make_relay_tab()

    def make_mouse_tab(self,parent,player):
        f=ttk.Frame(parent,padding=14); f.pack(fill="both",expand=True)
        ttk.Label(f,text=f"{player} 4 Köşe Kalibrasyon",style="Title.TLabel").pack(anchor="w")
        vars={k:tk.StringVar(value=f"{k}: -") for k in ["RAW","HID","AKTIF","CAL"]}
        setattr(self, f"{player}_vars", vars)
        for k in ["RAW","HID","AKTIF","CAL"]:
            ttk.Label(f,textvariable=vars[k],font=("Consolas",13),foreground="#fef3c7",background="#0f172a").pack(anchor="w", pady=2)
        cf=ttk.LabelFrame(f,text="Köşe yakalama",padding=10); cf.pack(fill="x",pady=12)
        for name,code in [("Sol Üst","LU"),("Sağ Üst","RU"),("Sağ Alt","RD"),("Sol Alt","LD")]:
            ttk.Button(cf,text=name,command=lambda c=code,p=player:self.capture(p,c)).pack(side="left",padx=4)
        ttk.Button(cf,text="Kalibrasyonu Kaydet",style="Accent.TButton",command=lambda p=player:self.save_cal(p)).pack(side="left",padx=12)
        ttk.Button(cf,text="Kalibrasyonu Sıfırla",style="Warn.TButton",command=lambda p=player:self.send_mouse(p,"RESETCAL")).pack(side="left",padx=4)
        ff=ttk.LabelFrame(f,text="Titreşim filtresi",padding=10); ff.pack(fill="x",pady=12)
        scale=ttk.Scale(ff,from_=0,to=6,orient="horizontal"); scale.set(2); scale.pack(fill="x")
        ttk.Button(ff,text="Filtreyi Kaydet",command=lambda p=player,s=scale:self.send_mouse(p,f"FILTER,{int(float(s.get()))}")).pack(anchor="w",pady=6)

    def make_controller_tab(self):
        f=ttk.Frame(self.ctrl_tab,padding=12); f.pack(fill="both",expand=True)
        ttk.Label(f,text="Controller Ayarları",style="Title.TLabel").pack(anchor="w")
        top=ttk.LabelFrame(f,text="Röle / Coin / Pin seçimi",padding=10); top.pack(fill="x",pady=8)
        ttk.Label(top,text="Röle tipi:").grid(row=0,column=0,sticky="e",padx=5,pady=5)
        self.cb_relay_mode = ttk.Combobox(top,textvariable=self.relay_mode,values=["HIGH","LOW"],width=10,state="readonly")
        self.cb_relay_mode.grid(row=0,column=1,sticky="w")
        ttk.Label(top,text="P1 coin tipi:").grid(row=0,column=2,sticky="e",padx=5)
        self.cb_p1_coin = ttk.Combobox(top,textvariable=self.p1_coin,values=["DRY","HIGH"],width=10,state="readonly")
        self.cb_p1_coin.grid(row=0,column=3,sticky="w")
        ttk.Label(top,text="P2 coin tipi:").grid(row=0,column=4,sticky="e",padx=5)
        self.cb_p2_coin = ttk.Combobox(top,textvariable=self.p2_coin,values=["DRY","HIGH"],width=10,state="readonly")
        self.cb_p2_coin.grid(row=0,column=5,sticky="w")

        ttk.Label(top,text="P1 tetik röle GP:").grid(row=1,column=0,sticky="e",padx=5,pady=5)
        self.cb_p1_relay = ttk.Combobox(top,textvariable=self.p1_relay_gp,values=GP_CHOICES,width=10,state="readonly")
        self.cb_p1_relay.grid(row=1,column=1,sticky="w")
        ttk.Label(top,text="P2 tetik röle GP:").grid(row=1,column=2,sticky="e",padx=5)
        self.cb_p2_relay = ttk.Combobox(top,textvariable=self.p2_relay_gp,values=GP_CHOICES,width=10,state="readonly")
        self.cb_p2_relay.grid(row=1,column=3,sticky="w")

        ttk.Label(top,text="P1 coin GP:").grid(row=2,column=0,sticky="e",padx=5,pady=5)
        self.cb_p1_coin_gp = ttk.Combobox(top,textvariable=self.p1_coin_gp,values=GP_CHOICES,width=10,state="readonly")
        self.cb_p1_coin_gp.grid(row=2,column=1,sticky="w")
        ttk.Label(top,text="P2 coin GP:").grid(row=2,column=2,sticky="e",padx=5)
        self.cb_p2_coin_gp = ttk.Combobox(top,textvariable=self.p2_coin_gp,values=GP_CHOICES,width=10,state="readonly")
        self.cb_p2_coin_gp.grid(row=2,column=3,sticky="w")

        ttk.Button(top,text="Ayarları Controller'a Gönder/Kaydet",style="Accent.TButton",command=self.send_cfg).grid(row=1,column=4,columnspan=2,padx=10,sticky="ew")
        ttk.Button(top,text="Controller Config Oku",command=self.read_controller_config).grid(row=0,column=6,rowspan=3,padx=10,sticky="ns")
        for cb in [self.cb_relay_mode,self.cb_p1_coin,self.cb_p2_coin,self.cb_p1_relay,self.cb_p2_relay,self.cb_p1_coin_gp,self.cb_p2_coin_gp]:
            cb.bind("<<ComboboxSelected>>", lambda e: self.mark_controller_dirty())
            cb.bind("<Button-1>", lambda e: self.mark_controller_dirty())

        km=ttk.LabelFrame(f,text="Tuş atama",padding=10); km.pack(fill="both",expand=True,pady=8)
        for idx,p in enumerate(KEY_PINS):
            r=idx//4; c=(idx%4)*2
            ttk.Label(km,text=f"GP{p}").grid(row=r,column=c,sticky="e",padx=4,pady=3)
            ttk.Combobox(km,textvariable=self.key_vars[p],values=KEY_CHOICES,width=9,state="readonly").grid(row=r,column=c+1,sticky="w",padx=4,pady=3)
        ttk.Button(f,text="Tüm Tuş Atamalarını Controller'a Gönder/Kaydet",style="Accent.TButton",command=self.send_keymap).pack(anchor="w",pady=6)
        self.ctrl_status=tk.StringVar(value="")
        ttk.Label(f,textvariable=self.ctrl_status,font=("Consolas",10),foreground="#fef3c7",background="#0f172a").pack(fill="x")

    def make_key_tab(self):
        f=ttk.Frame(self.key_tab,padding=10); f.pack(fill="both",expand=True)
        self.key_text=tk.Text(f,font=("Consolas",13),bg="#020617",fg="#fef08a",insertbackground="white")
        self.key_text.pack(fill="both",expand=True)

    def make_relay_tab(self):
        f=ttk.Frame(self.relay_tab,padding=12); f.pack(fill="both",expand=True)
        ttk.Label(f,text="Röle Testi",style="Title.TLabel").pack(anchor="w")
        ttk.Label(f,text="Test butonuna basınca seçilen GP röleyi 1 saniye çeker. İlk testte motor 12V bağlı olmasın.",style="Sub.TLabel").pack(anchor="w",pady=4)
        row=ttk.Frame(f); row.pack(anchor="w",pady=8)
        ttk.Button(row,text="⚡ P1 Röle Test Et",style="Accent.TButton",command=lambda:self.controller_send("RELAYTEST,1")).pack(side="left",padx=5)
        ttk.Button(row,text="⚡ P2 Röle Test Et",style="Accent.TButton",command=lambda:self.controller_send("RELAYTEST,2")).pack(side="left",padx=5)
        ttk.Button(row,text="P1 Röleyi Aç",command=lambda:self.controller_send("RELAY,1,1")).pack(side="left",padx=5)
        ttk.Button(row,text="P1 Röleyi Kapat",command=lambda:self.controller_send("RELAY,1,0")).pack(side="left",padx=5)
        ttk.Button(row,text="P2 Röleyi Aç",command=lambda:self.controller_send("RELAY,2,1")).pack(side="left",padx=5)
        ttk.Button(row,text="P2 Röleyi Kapat",command=lambda:self.controller_send("RELAY,2,0")).pack(side="left",padx=5)
        self.relay_text=tk.Text(f,font=("Consolas",13),height=14,bg="#020617",fg="#86efac",insertbackground="white")
        self.relay_text.pack(fill="both",expand=True,pady=8)

    def scan(self):
        if serial is None:
            messagebox.showerror("Eksik modül","pyserial yüklü değil. requirements.txt ile kur."); return
        for d in self.devices.values(): d.close()
        self.devices.clear(); self.tree.delete(*self.tree.get_children())
        found=[]
        for p in list_ports.comports():
            hello=""
            try:
                ser=serial.Serial(p.device,115200,timeout=0.15,write_timeout=0.2)
                try: ser.dtr=True; ser.rts=True; ser.reset_input_buffer(); ser.reset_output_buffer()
                except Exception: pass
                time.sleep(0.25)
                ser.write(b"PING\n")
                t0=time.time(); lines=[]
                while time.time()-t0<1.2:
                    line=ser.readline().decode("ascii",errors="ignore").strip()
                    if line:
                        lines.append(line)
                        if line.startswith("HELLO") or line.startswith("STATUS"):
                            hello=line; break
                if not hello and lines: hello=lines[-1]
                ser.close()
                dev=SerialDevice(p.device,hello)
                dev.open()
                key = dev.player if dev.kind=="MOUSE" else ("CONTROLLER" if dev.kind=="KEYBOARD" else p.device)
                if key in self.devices: key=f"{key}_{p.device}"
                self.devices[key]=dev; found.append(key)
                self.tree.insert("", "end", iid=key, values=(p.device, f"{dev.kind} {dev.player}", hello or "COM var, cevap yok"))
            except Exception:
                continue
        self.status.set("Bulunan: " + (", ".join(found) if found else "Yok"))

    def force_selected(self, role):
        sel=self.tree.selection()
        if not sel: return
        old=sel[0]; dev=self.devices.pop(old)
        if role=="P1": dev.kind="MOUSE"; dev.player="P1"; new="P1"
        elif role=="P2": dev.kind="MOUSE"; dev.player="P2"; new="P2"
        else: dev.kind="KEYBOARD"; dev.player="CONTROLLER"; new="CONTROLLER"
        self.devices[new]=dev; self.scan_tree_refresh()

    def scan_tree_refresh(self):
        self.tree.delete(*self.tree.get_children())
        for k,d in self.devices.items(): self.tree.insert("", "end", iid=k, values=(d.port, f"{d.kind} {d.player}", d.last_line))

    def get_mouse(self,p): return self.devices.get(p)
    def get_ctrl(self): return self.devices.get("CONTROLLER") or self.devices.get("KEYBOARD")

    def send_mouse(self,p,line):
        d=self.get_mouse(p)
        if not d: messagebox.showwarning("Cihaz yok",f"{p} bulunamadı"); return
        d.send(line)

    def controller_send(self,line):
        d=self.get_ctrl()
        if not d: messagebox.showwarning("Controller yok","Controller bulunamadı. Cihazları Tara yap."); return
        d.send(line); self.ctrl_status.set("Gönderildi: "+line)

    def mark_controller_dirty(self):
        self.controller_fields_dirty = True

    def read_controller_config(self):
        self.controller_fields_dirty = False
        self.controller_send("GETCFG")

    def apply_controller_values_from_device(self, kb, force=False):
        # Kullanıcı açılır menüde seçim yaparken program eski değerle üstüne yazmasın.
        if self.controller_fields_dirty and not force:
            return
        self.p1_relay_gp.set(f"GP{kb.p1_relay_pin}")
        self.p2_relay_gp.set(f"GP{kb.p2_relay_pin}")
        self.p1_coin_gp.set(f"GP{getattr(kb, 'p1_coin_pin', 17)}")
        self.p2_coin_gp.set(f"GP{getattr(kb, 'p2_coin_pin', 21)}")
        self.relay_mode.set(kb.relay_mode if kb.relay_mode in ["HIGH","LOW"] else "HIGH")
        self.p1_coin.set(kb.p1_coin if kb.p1_coin in ["DRY","HIGH"] else "DRY")
        self.p2_coin.set(kb.p2_coin if kb.p2_coin in ["DRY","HIGH"] else "DRY")
        self.controller_loaded_once = True

    def gp_num(self, s):
        return int(str(s).replace("GP", ""))

    def send_cfg(self):
        p1 = self.gp_num(self.p1_relay_gp.get())
        p2 = self.gp_num(self.p2_relay_gp.get())
        c1 = self.gp_num(self.p1_coin_gp.get())
        c2 = self.gp_num(self.p2_coin_gp.get())
        used = [p1, p2, c1, c2]
        if len(set(used)) != len(used):
            messagebox.showwarning("Hatalı pin", "P1/P2 röle ve coin pinleri aynı olamaz."); return
        if p1 in KEY_PINS or p2 in KEY_PINS:
            if not messagebox.askyesno("Uyarı", "Seçilen röle GP pinlerinden biri tuş pinleriyle çakışıyor. Bu pin artık tuş olarak çalışmayabilir. Devam edilsin mi?"):
                return
        # V019: Eski V018 firmware SETCFG içinde coin pinlerini okumuyordu.
        # Bu yüzden hem yeni SETCFG formatını gönderiyoruz, hem de uyumluluk için
        # ayrı COINPIN/RELAYPIN komutlarını gönderiyoruz. Böylece P1 coin GP3 kaydedince
        # tekrar GP17'ye dönmez.
        self.controller_fields_dirty = True
        d = self.get_ctrl()
        if not d:
            messagebox.showwarning("Controller yok", "Controller bulunamadı. Cihazları Tara yap."); return
        cmds = [
            f"SETCFG,{self.relay_mode.get()},{self.p1_coin.get()},{self.p2_coin.get()},{p1},{p2},{c1},{c2}",
            f"RELAYPIN,1,{p1}",
            f"RELAYPIN,2,{p2}",
            f"COINPIN,1,{c1}",
            f"COINPIN,2,{c2}",
            "GETCFG",
        ]
        for cmd in cmds:
            d.send(cmd)
            time.sleep(0.04)
        self.ctrl_status.set(f"Kaydedildi: P1 coin GP{c1}, P2 coin GP{c2}, P1 röle GP{p1}, P2 röle GP{p2}")
        self.controller_fields_dirty = False

    def send_keymap(self):
        d=self.get_ctrl()
        if not d: messagebox.showwarning("Controller yok","Controller bulunamadı."); return
        for p in KEY_PINS:
            d.send(f"SETKEY,{p},{HID_KEYS[self.key_vars[p].get()]}")
            time.sleep(0.03)
        self.ctrl_status.set("Tuş atamaları gönderildi.")

    def capture(self,p,corner):
        d=self.get_mouse(p)
        if not d or d.raw_x is None: messagebox.showwarning("Veri yok",f"{p} RAW veri yok"); return
        self.captures[p][corner]=(d.raw_x,d.raw_y)
        messagebox.showinfo("Alındı",f"{p} {corner}: X={d.raw_x} Y={d.raw_y}")

    def save_cal(self,p):
        d=self.get_mouse(p); caps=self.captures[p]
        if not d: messagebox.showwarning("Cihaz yok",f"{p} yok"); return
        need=["LU","RU","RD","LD"]
        if any(k not in caps for k in need): messagebox.showwarning("Eksik","4 köşeyi de al"); return
        xs=[caps[k][0] for k in need]; ys=[caps[k][1] for k in need]
        d.send(f"SETCAL,{min(xs)},{max(xs)},{min(ys)},{max(ys)}")
        messagebox.showinfo("Gönderildi",f"{p} kalibrasyon gönderildi")

    def refresh_ui(self):
        self.dev_text.delete("1.0","end")
        for k,d in self.devices.items():
            self.dev_text.insert("end",f"{k} | {d.port} | {d.kind} {d.player}\n{d.last_line}\n\n")
            if d.kind=="MOUSE" and d.player in ["P1","P2"]:
                vars=getattr(self,f"{d.player}_vars")
                vars["RAW"].set(f"RAW: X={d.raw_x} Y={d.raw_y}")
                vars["HID"].set(f"HID: X={d.hid_x} Y={d.hid_y}")
                vars["AKTIF"].set(f"AKTİF: {'EVET' if d.active else 'HAYIR'}")
                vars["CAL"].set(f"CAL: {d.cal} FILTER:{d.filter_shift}")
        kb=self.get_ctrl()
        self.key_text.delete("1.0","end"); self.relay_text.delete("1.0","end")
        if kb:
            self.apply_controller_values_from_device(kb, force=not self.controller_loaded_once)
            for p in KEY_PINS:
                self.key_text.insert("end",f"GP{p:<2} : {'🟢 BASILDI' if kb.buttons.get(str(p),False) else '⚪ BASILMADI'}\n")
            self.relay_text.insert("end",f"P1 Röle GP{kb.p1_relay_pin}: {'🟢 ÇEKİYOR' if kb.relays.get(str(kb.p1_relay_pin),False) else '⚪ BIRAKTI'}\n")
            self.relay_text.insert("end",f"P2 Röle GP{kb.p2_relay_pin}: {'🟢 ÇEKİYOR' if kb.relays.get(str(kb.p2_relay_pin),False) else '⚪ BIRAKTI'}\n")
            self.relay_text.insert("end",f"Röle tipi: {kb.relay_mode} | P1 coin: {kb.p1_coin} GP{getattr(kb, 'p1_coin_pin', 17)} | P2 coin: {kb.p2_coin} GP{getattr(kb, 'p2_coin_pin', 21)}\n")
            self.relay_text.insert("end",f"Son durum: {kb.last_line}\n")
            self.ctrl_status.set(kb.cfg_text)
        else:
            self.key_text.insert("end","Controller bulunamadı.\n")
            self.relay_text.insert("end","Controller bulunamadı.\n")
        self.after(300,self.refresh_ui)

    def destroy(self):
        for d in self.devices.values(): d.close()
        super().destroy()

if __name__ == "__main__":
    app=App(); app.mainloop()
