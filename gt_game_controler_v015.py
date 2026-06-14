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

APP_TITLE = "GT GAME CONTROLER v015"

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

class SerialDevice:
    def __init__(self, port, hello=""):
        self.port = port
        self.hello = hello
        self.kind = "UNKNOWN"
        self.player = ""
        self.ser = None
        self.running = False
        self.last_line = hello
        self.raw_x = self.raw_y = None
        self.hid_x = self.hid_y = None
        self.active = None
        self.cal = None
        self.filter_shift = None
        self.buttons = {}
        self.relays = {}
        self.cfg_text = ""
        self.classify(hello)

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
            self.ser.dtr = True; self.ser.rts = True
            self.ser.reset_input_buffer(); self.ser.reset_output_buffer()
        except Exception:
            pass
        self.running = True
        threading.Thread(target=self.reader, daemon=True).start()

    def close(self):
        self.running = False
        try:
            if self.ser: self.ser.close()
        except Exception: pass

    def send(self, line):
        if not self.ser or not self.ser.is_open: return
        try: self.ser.write((line.strip()+"\n").encode("ascii", errors="ignore"))
        except Exception: pass

    def reader(self):
        while self.running:
            try:
                line = self.ser.readline().decode("ascii", errors="ignore").strip()
                if line: self.parse_line(line)
            except Exception:
                time.sleep(0.1)

    def parse_line(self, line):
        self.last_line = line
        self.classify(line)
        parts = line.split(',')
        if len(parts) < 2: return
        if parts[0] == "STATUS" and parts[1] == "MOUSE":
            try:
                self.player = parts[2]
                i = 3
                while i < len(parts):
                    if parts[i] == "RAW": self.raw_x=int(parts[i+1]); self.raw_y=int(parts[i+2]); i+=3
                    elif parts[i] == "HID": self.hid_x=int(parts[i+1]); self.hid_y=int(parts[i+2]); i+=3
                    elif parts[i] == "ACTIVE": self.active=bool(int(parts[i+1])); i+=2
                    elif parts[i] == "CAL": self.cal=tuple(map(int, parts[i+1:i+5])); i+=5
                    elif parts[i] == "FILTER": self.filter_shift=int(parts[i+1]); i+=2
                    else: i+=1
            except Exception: pass
        elif parts[0] == "STATUS" and parts[1] == "KEYBOARD":
            for item in parts[3:]:
                if ':' in item:
                    p,v = item.split(':',1)
                    if p.isdigit():
                        if p in ("26","27"): self.relays[p] = (v == '1')
                        else: self.buttons[p] = (v == '1')
            self.cfg_text = line
        elif parts[0] == "CONFIG":
            self.cfg_text = line

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x780")
        self.devices = {}
        self.captures = {"P1":{}, "P2":{}}
        self.key_vars = {p: tk.StringVar(value=DEFAULT_KEYMAP[p]) for p in KEY_PINS}
        self.relay_mode = tk.StringVar(value="HIGH")
        self.p1_coin = tk.StringVar(value="DRY")
        self.p2_coin = tk.StringVar(value="DRY")
        self.create_ui()
        self.after(300, self.refresh_ui)

    def create_ui(self):
        top = ttk.Frame(self, padding=8); top.pack(fill="x")
        ttk.Label(top, text=APP_TITLE, font=("Segoe UI",16,"bold")).pack(side="left")
        ttk.Button(top, text="Cihazları Tara / Yenile", command=self.scan).pack(side="right")
        self.status = tk.StringVar(value="3 Pico'yu tak, sonra Cihazları Tara / Yenile yap.")
        ttk.Label(self, textvariable=self.status, padding=6).pack(fill="x")
        list_frame = ttk.LabelFrame(self, text="Bağlı cihazlar", padding=6); list_frame.pack(fill="x", padx=8, pady=4)
        self.tree = ttk.Treeview(list_frame, columns=("port","type","hello"), show="headings", height=5)
        for c,t,w in [("port","Port",120),("type","Cihaz",180),("hello","Son cevap",760)]:
            self.tree.heading(c,text=t); self.tree.column(c,width=w)
        self.tree.pack(side="left", fill="x", expand=True)
        b = ttk.Frame(list_frame); b.pack(side="right", padx=6)
        ttk.Button(b, text="Seçiliyi P1 yap", command=lambda:self.force_selected("P1")).pack(fill="x", pady=2)
        ttk.Button(b, text="Seçiliyi P2 yap", command=lambda:self.force_selected("P2")).pack(fill="x", pady=2)
        ttk.Button(b, text="Seçiliyi Controller yap", command=lambda:self.force_selected("CONTROLLER")).pack(fill="x", pady=2)

        self.tabs = ttk.Notebook(self); self.tabs.pack(fill="both", expand=True, padx=8, pady=8)
        self.dev_tab=ttk.Frame(self.tabs); self.p1_tab=ttk.Frame(self.tabs); self.p2_tab=ttk.Frame(self.tabs)
        self.ctrl_tab=ttk.Frame(self.tabs); self.key_tab=ttk.Frame(self.tabs); self.relay_tab=ttk.Frame(self.tabs)
        self.tabs.add(self.dev_tab,text="Cihaz Durumu"); self.tabs.add(self.p1_tab,text="P1 Kalibrasyon")
        self.tabs.add(self.p2_tab,text="P2 Kalibrasyon"); self.tabs.add(self.ctrl_tab,text="Controller Ayar")
        self.tabs.add(self.key_tab,text="Tuş Testi"); self.tabs.add(self.relay_tab,text="Röle Testi")
        self.dev_text=tk.Text(self.dev_tab,font=("Consolas",11)); self.dev_text.pack(fill="both",expand=True)
        self.make_mouse_tab(self.p1_tab,"P1"); self.make_mouse_tab(self.p2_tab,"P2")
        self.make_controller_tab(); self.make_key_tab(); self.make_relay_tab()

    def make_mouse_tab(self,parent,player):
        f=ttk.Frame(parent,padding=12); f.pack(fill="both",expand=True)
        ttk.Label(f,text=f"{player} 4 Köşe Kalibrasyon",font=("Segoe UI",14,"bold")).pack(anchor="w")
        vars={k:tk.StringVar(value=f"{k}: -") for k in ["RAW","HID","AKTIF","CAL"]}
        setattr(self, f"{player}_vars", vars)
        for k in ["RAW","HID","AKTIF","CAL"]: ttk.Label(f,textvariable=vars[k],font=("Consolas",12)).pack(anchor="w")
        cf=ttk.LabelFrame(f,text="Köşe yakalama",padding=8); cf.pack(fill="x",pady=10)
        for name,code in [("Sol Üst","LU"),("Sağ Üst","RU"),("Sağ Alt","RD"),("Sol Alt","LD")]:
            ttk.Button(cf,text=name,command=lambda c=code,p=player:self.capture(p,c)).pack(side="left",padx=4)
        ttk.Button(cf,text="Kalibrasyonu Kaydet",command=lambda p=player:self.save_cal(p)).pack(side="left",padx=12)
        ttk.Button(cf,text="Kalibrasyonu Sıfırla",command=lambda p=player:self.send_mouse(p,"RESETCAL")).pack(side="left",padx=4)
        ff=ttk.LabelFrame(f,text="Titreşim filtresi",padding=8); ff.pack(fill="x",pady=10)
        scale=ttk.Scale(ff,from_=0,to=6,orient="horizontal"); scale.set(2); scale.pack(fill="x")
        ttk.Button(ff,text="Filtreyi Kaydet",command=lambda p=player,s=scale:self.send_mouse(p,f"FILTER,{int(float(s.get()))}")).pack(anchor="w",pady=4)

    def make_controller_tab(self):
        f=ttk.Frame(self.ctrl_tab,padding=10); f.pack(fill="both",expand=True)
        ttk.Label(f,text="Controller Ayarları",font=("Segoe UI",14,"bold")).pack(anchor="w")
        row=ttk.Frame(f); row.pack(fill="x",pady=4)
        ttk.Label(row,text="Röle tipi:").pack(side="left"); ttk.Combobox(row,textvariable=self.relay_mode,values=["HIGH","LOW"],width=8,state="readonly").pack(side="left",padx=5)
        ttk.Label(row,text="P1 coin:").pack(side="left",padx=(20,0)); ttk.Combobox(row,textvariable=self.p1_coin,values=["DRY","HIGH"],width=8,state="readonly").pack(side="left",padx=5)
        ttk.Label(row,text="P2 coin:").pack(side="left",padx=(20,0)); ttk.Combobox(row,textvariable=self.p2_coin,values=["DRY","HIGH"],width=8,state="readonly").pack(side="left",padx=5)
        ttk.Button(row,text="Ayarları Controller'a Gönder/Kaydet",command=self.send_cfg).pack(side="left",padx=20)
        ttk.Button(row,text="Controller Config Oku",command=lambda:self.controller_send("GETCFG")).pack(side="left")
        km=ttk.LabelFrame(f,text="Tuş atama",padding=8); km.pack(fill="both",expand=True,pady=8)
        for idx,p in enumerate(KEY_PINS):
            r=idx//3; c=(idx%3)*2
            ttk.Label(km,text=f"GP{p}").grid(row=r,column=c,sticky="e",padx=4,pady=3)
            ttk.Combobox(km,textvariable=self.key_vars[p],values=KEY_CHOICES,width=9,state="readonly").grid(row=r,column=c+1,sticky="w",padx=4,pady=3)
        ttk.Button(f,text="Tüm Tuş Atamalarını Controller'a Gönder/Kaydet",command=self.send_keymap).pack(anchor="w",pady=6)
        self.ctrl_status=tk.StringVar(value="")
        ttk.Label(f,textvariable=self.ctrl_status,font=("Consolas",10)).pack(fill="x")

    def make_key_tab(self):
        f=ttk.Frame(self.key_tab,padding=10); f.pack(fill="both",expand=True)
        self.key_text=tk.Text(f,font=("Consolas",12)); self.key_text.pack(fill="both",expand=True)

    def make_relay_tab(self):
        f=ttk.Frame(self.relay_tab,padding=10); f.pack(fill="both",expand=True)
        ttk.Label(f,text="Röle Testi",font=("Segoe UI",14,"bold")).pack(anchor="w")
        ttk.Label(f,text="P1 röle GP26, P2 röle GP27. İlk testte motor 12V bağlı olmasın; sadece röle LED'i ile dene.").pack(anchor="w",pady=4)
        row=ttk.Frame(f); row.pack(anchor="w",pady=8)
        ttk.Button(row,text="P1 Röle Test Et",command=lambda:self.controller_send("RELAYTEST,1")).pack(side="left",padx=5)
        ttk.Button(row,text="P2 Röle Test Et",command=lambda:self.controller_send("RELAYTEST,2")).pack(side="left",padx=5)
        self.relay_text=tk.Text(f,font=("Consolas",12),height=12); self.relay_text.pack(fill="both",expand=True,pady=8)

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
                t0=time.time()
                lines=[]
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
                self.devices[key]=dev
                found.append(key)
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
        self.devices[new]=dev
        self.scan_tree_refresh()

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
        d.send(line)
        self.ctrl_status.set("Gönderildi: "+line)

    def send_cfg(self):
        self.controller_send(f"SETCFG,{self.relay_mode.get()},{self.p1_coin.get()},{self.p2_coin.get()}")

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
        self.key_text.delete("1.0","end")
        self.relay_text.delete("1.0","end")
        if kb:
            for p in KEY_PINS:
                self.key_text.insert("end",f"GP{p:<2} : {'BASILDI' if kb.buttons.get(str(p),False) else 'BASILMADI'}\n")
            self.relay_text.insert("end",f"P1 Röle GP26: {'ÇEKİYOR' if kb.relays.get('26',False) else 'BIRAKTI'}\n")
            self.relay_text.insert("end",f"P2 Röle GP27: {'ÇEKİYOR' if kb.relays.get('27',False) else 'BIRAKTI'}\n")
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
