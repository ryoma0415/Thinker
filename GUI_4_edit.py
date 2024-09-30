import tkinter as tk

from PIL import Image, ImageTk
from tkinter import ttk, messagebox
import serial
import threading
import serial.tools.list_ports
import math


class SerialApp:
    def __init__(self, master):
        self.master = master
        self.master.title("TK-01 App")
        self.led_onoff_flag = 0
        self.offset_d = 0.0
        self.offset_s1 = 0.0
        self.offset_s2 = 0.0

        self.measure_d = 0.0
        self.measure_s1 = 0.0
        self.measure_s2 = 0.0
        self.fixed_d = 0.0
        self.fixed_s1 = 0.0
        self.fixed_s2 = 0.0
        self.measure_angle = 0.0

        self.d = [0.0] * 9
        self.s1 = [0.0] * 9
        self.s2 = [0.0] * 9
        self.angle = [0.0] * 9

        self.cal_pitch_p = 1.0
        self.cal_pitch_n = 1.0
        self.cal_yaw_p = 1.0
        self.cal_yaw_n = 1.0

        self.calibration = False

        self.d_max = 5.3

        self.img_x = 300
        self.img_y = 200
        self.img_center_x = 250
        self.img_center_y = 250

        # Canvasを追加
        self.canvas = tk.Canvas(master, width=500, height=500, bg="white")
        self.canvas.pack()
        self.canvas.place(x=self.img_x, y=self.img_y)

        # 画像
        self.img = Image.open("big.png")
        self.back_img = self.img.resize((500, 500), Image.LANCZOS)
        self.background_img = ImageTk.PhotoImage(self.back_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.background_img)
        self.image_label = tk.Label(master, image=self.background_img)

        # 初期の線を描画（座標は0,0から100,100に）
        self.line = self.canvas.create_line(self.img_center_x, self.img_center_x, self.img_center_x + 10,
                                            self.img_center_y + 10, fill="blue", width=2)

        # 接続状態を表示するラベル
        self.connection_status_label = tk.Label(master, text="未接続", font=("Arial", 12))
        self.connection_status_label.pack()
        self.connection_status_label.place(x=10, y=10)

        # COMポート選択のプルダウンメニュー
        self.com_port_var = tk.StringVar()
        self.com_ports = self.get_com_ports()
        self.com_port_menu = ttk.Combobox(master, textvariable=self.com_port_var, values=self.com_ports)
        self.com_port_menu.pack(pady=20)
        self.com_port_menu.place(x=120, y=12)

        # 接続ボタン
        self.connect_button = tk.Button(master, text="接続", command=self.connect_com_port)
        self.connect_button.pack(pady=20)
        self.connect_button.place(x=300, y=10)

        # ボタンの設定
        button_font = ("Arial", 16)
        self.start_button = tk.Button(master, text="計測開始", font=button_font, command=self.toggle_measurement)
        self.start_button.pack(pady=20)
        self.start_button.place(x=10, y=60)

        self.led_on_button = tk.Button(master, text="不透明設定", font=button_font, command=self.send_LED_ON_command)
        self.led_on_button.pack(pady=10)
        self.led_on_button.place(x=200, y=60)

        self.led_off_button = tk.Button(master, text="透明設定", font=button_font, command=self.send_LED_OFF_command)
        self.led_off_button.pack(pady=10)
        self.led_off_button.place(x=400, y=60)

        self.send_offset_button = tk.Button(master, text="原点調整", font=button_font, command=self.send_offset_command)
        self.send_offset_button.pack(pady=10)
        self.send_offset_button.place(x=600, y=60)

        self.calibration_button = tk.Button(master, text="キャリブレーション開始", font=button_font, command=self.calibration_command)
        self.calibration_button.pack(pady=10)
        self.calibration_button.place(x=800, y=60)

        # ラベルのリストを初期化
        self.value_d_labels = []
        self.value_s1_labels = []
        self.value_s2_labels = []
        self.value_angle_labels = []

        # Getボタンをループで定義
        for i in range(9):
            button = tk.Button(master, text=f"Get{i}", font=button_font, command=lambda idx=i: self.get_sensor_command(idx))
            button.pack(pady=10)
            button.place(x=50 + i * 100, y=150)

        # ラベルの定義
        label_font = ("Arial", 18)
        font_color = '#000000'
        self.data_label_d = tk.Label(master, text="計測距離: 待機中", font=label_font, foreground=font_color)
        self.data_label_d.pack(pady=5)
        self.data_label_d.place(x=10, y=120)

        self.data_label_s1 = tk.Label(master, text="計測ヨー軸角度: 待機中", font=label_font, foreground=font_color)
        self.data_label_s1.pack(pady=5)
        self.data_label_s1.place(x=300, y=120)

        self.data_label_s2 = tk.Label(master, text="計測ピッチ軸角度: 待機中", font=label_font, foreground=font_color)
        self.data_label_s2.pack(pady=5)
        self.data_label_s2.place(x=600, y=120)

        self.data_label_angle = tk.Label(master, text="計測θ角度: 待機中", font=label_font, foreground=font_color)
        self.data_label_angle.pack(pady=5)
        self.data_label_angle.place(x=900, y=120)

        for i in range(9):
            self.value_d_labels.append(
                self.create_label(master, 250 + (i % 3) * 250, 200 + (i // 3) * 200, font_color, label_font))
            self.value_s1_labels.append(
                self.create_label(master, 250 + (i % 3) * 250, 230 + (i // 3) * 200, '#FFCC00', label_font))
            self.value_s2_labels.append(
                self.create_label(master, 250 + (i % 3) * 250, 260 + (i // 3) * 200, '#00CCFF', label_font))
            self.value_angle_labels.append(
                self.create_label(master, 250 + (i % 3) * 250, 290 + (i // 3) * 200, '#FFCCFF', label_font))

        # Initialize serial port
        self.ser = serial.Serial()
        self.ser.baudrate = 500000
        self.ser.timeout = 1

        # Measurement control flag
        self.measuring = False

        # Thread for handling the measurement loop
        self.thread = None

    def update_line(self, value_1, value_2):
        """センサの値に応じて線を更新"""
        # 取得した値で線の終点を動的に変更
        x_end = self.img_center_x + value_1 * 20
        y_end = self.img_center_y + value_2 * 20

        # 既存の線を新しい座標に更新
        self.canvas.coords(self.line, self.img_center_x, self.img_center_y, x_end, y_end)

    def measurement_loop(self):
        command = bytes([0x52, 0x01, 0x00, 0x53])
        self.ser.timeout = 0.5
        while self.measuring and self.ser.is_open:
            try:
                self.ser.write(command)
                response = self.ser.read(14)
                if not self.measuring:
                    break
                if len(response) == 14:
                    gain = 0.95
                    self.measure_d = gain * self.measure_d + (1.0 - gain) * (float(int(response[2])) / 10.0)
                    self.measure_s1 = gain * self.measure_s1 + (1.0 - gain) * (float(int(response[3])) / 2.0 - 40.0)
                    self.measure_s2 = gain * self.measure_s2 + (1.0 - gain) * (float(int(response[4])) / 2.0 - 40.0)

                    self.fixed_d = (self.measure_d - self.offset_d)
                    self.fixed_s1 = (self.measure_s1 - self.offset_s1)
                    self.fixed_s2 = (self.measure_s2 - self.offset_s2)

                    if self.calibration:
                        if self.fixed_s1 >= 0:
                            self.fixed_s1 = self.fixed_s1 * self.cal_yaw_p
                        else:
                            self.fixed_s1 = self.fixed_s1 * self.cal_yaw_n

                        if self.fixed_s2 >= 0:
                            self.fixed_s2 = self.fixed_s2 * self.cal_pitch_p
                        else:
                            self.fixed_s2 = self.fixed_s2 * self.cal_pitch_n

                    if not self.calibration:
                        self.measure_angle = math.degrees(math.atan2(self.fixed_s2, self.fixed_s1))
                        self.update_gui_d(f"計測距離: {self.fixed_d:04.1f}")
                        self.update_gui_s1(f"計測ヨー軸角度: {self.fixed_s1:04.1f}")
                        self.update_gui_s2(f"計測ピッチ軸角度: {self.fixed_s2:04.1f}")
                        self.update_gui_angle(f"計測θ角度: {self.measure_angle:04.1f}")
                        self.update_line(self.fixed_s1, self.fixed_s2)
                    else:
                        self.measure_angle = math.degrees(math.atan2(self.fixed_s2, self.fixed_s1))
                        self.update_gui_d(f"計測距離: {self.fixed_d:04.1f}")
                        self.update_gui_s1(f"補償ヨー軸角度: {self.fixed_s1:04.1f}")
                        self.update_gui_s2(f"補償ピッチ軸角度: {self.fixed_s2:04.1f}")
                        self.update_gui_angle(f"補償θ角度: {self.measure_angle:04.1f}")
                        self.update_line(self.fixed_s1, self.fixed_s2)

            except Exception as e:
                self.update_gui_d(f"エラー: {e}")
                break

    def create_label(self, master, x, y, color, font):
        label = tk.Label(master, text="0.0", font=font, foreground=color)
        label.pack(pady=5)
        label.place(x=x, y=y)
        return label

    def get_com_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def connect_com_port(self):
        selected_port = self.com_port_var.get()
        if not selected_port:
            messagebox.showerror("Error", "COMポートを選択してください")
            return
        try:
            self.ser.port = selected_port
            self.ser.open()
            self.connection_status_label.config(text=f"{selected_port} に接続")
            self.connect_button.config(state='disabled')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open serial port: {e}")
            self.start_button.config(state='disabled')

    def toggle_measurement(self):
        if not self.measuring:
            self.measuring = True
            self.led_onoff_flag = 1
            self.start_button.config(text="計測停止")
            self.led_on_button.config(text="計測中")
            self.led_off_button.config(text="計測中")
            self.thread = threading.Thread(target=self.measurement_loop)
            self.thread.daemon = True
            self.thread.start()
        else:
            self.measuring = False
            self.led_onoff_flag = 0
            self.start_button.config(text="計測開始")
            self.led_on_button.config(text="透明設定")
            self.led_off_button.config(text="不透明設定")

    def calibration_command(self):
        if not self.calibration:
            self.calibration = True
            self.calibration_button.config(text="キャリブレーション停止")
            self.cal_pitch()
            self.cal_yaw()
        else:
            self.calibration = False
            self.calibration_button.config(text="キャリブレーション開始")
            self.cal_pitch_p = 1.0
            self.cal_pitch_n = 1.0
            self.cal_yaw_p = 1.0
            self.cal_yaw_n = 1.0

    def send_LED_ON_command(self):
        if self.led_onoff_flag == 0:
            command = bytes([0x4C, 0x01, 0x01, 0x4E])
            self.ser.write(command)
            self.ser.read(22)

    def send_LED_OFF_command(self):
        if self.led_onoff_flag == 0:
            command = bytes([0x4C, 0x01, 0x00, 0x4D])
            self.ser.write(command)
            self.ser.read(22)

    def send_offset_command(self):
        self.offset_d = self.measure_d
        self.offset_s1 = self.measure_s1
        self.offset_s2 = self.measure_s2

    def get_sensor_command(self, idx):
        self.d[idx] = self.fixed_d
        self.s1[idx] = self.fixed_s1
        self.s2[idx] = self.fixed_s2
        self.angle[idx] = self.measure_angle

        self.value_d_labels[idx].config(text=f"{self.d[idx]:.2f}")
        self.value_s1_labels[idx].config(text=f"{self.s1[idx]:.2f}")
        self.value_s2_labels[idx].config(text=f"{self.s2[idx]:.2f}")
        self.value_angle_labels[idx].config(text=f"{self.angle[idx]:.2f}")

    def update_gui_d(self, text):
        self.data_label_d.config(text=text)

    def update_gui_s1(self, text):
        self.data_label_s1.config(text=text)

    def update_gui_s2(self, text):
        self.data_label_s2.config(text=text)

    def update_gui_angle(self, text):
        self.data_label_angle.config(text=text)

    def on_closing(self):
        self.measuring = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.master.quit()
        self.master.destroy()

    def cal_pitch(self):
        if not self.s2[1] == 0:
            self.cal_pitch_n = -7/self.s2[1]
        if not self.s2[7] == 0:
            self.cal_pitch_p = 7/self.s2[7]

    def cal_yaw(self):
        if not self.s1[3] == 0:
            self.cal_yaw_n = -7/self.s1[3]
        if not self.s1[5] == 0:
            self.cal_yaw_p = 7/self.s1[5]



def main():
    root = tk.Tk()
    app = SerialApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.geometry("1200x800")
    root.resizable(False, False)
    root.mainloop()


if __name__ == "__main__":
    main()