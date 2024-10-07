import tkinter as tk

from PIL import Image, ImageTk
from tkinter import ttk, messagebox
import serial
import threading
import serial.tools.list_ports
import math
import pickle

max_angle = 7.0

class SerialApp:
    def __init__(self, master):
        self.master = master
        self.master.title("TK-01 App")
        self.led_onoff_flag = 0
        self.offset_a_d = 0.0
        self.offset_a_s1 = 0.0
        self.offset_a_s2 = 0.0

        self.offset_b_d = 0.0
        self.offset_b_s1 = 0.0
        self.offset_b_s2 = 0.0

        self.measure_d = 0.0
        self.measure_s1 = 0.0
        self.measure_s2 = 0.0
        self.fixed_d = 0.0
        self.fixed_s1 = 0.0
        self.fixed_s2 = 0.0
        self.measure_angle = 0.0

        self.d = [0.0] * 10
        self.s1 = [0.0] * 10
        self.s2 = [0.0] * 10
        self.angle = [0.0] * 10

        self.cal_yaw_p = [1.0, 1.0]
        self.cal_yaw_n = [1.0, 1.0]
        self.cal_pitch_p = [1.0, 1.0]
        self.cal_pitch_n = [1.0, 1.0]

        self.cal_yaw_p_z = 1.0
        self.cal_yaw_n_z = 1.0
        self.cal_pitch_p_z = 1.0
        self.cal_pitch_n_z = 1.0

        self.cal_delta_yaw_p = 1.0
        self.cal_delta_yaw_n = 1.0
        self.cal_delta_pitch_p = 1.0
        self.cal_delta_pitch_n = 1.0

        self.cal_z = 1.0

        self.calibration = False

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

        self.send_offset_button = tk.Button(master, text="原点調整A", font=button_font, command=self.send_offset_a_command)
        self.send_offset_button.pack(pady=10)
        self.send_offset_button.place(x=450, y=60)

        self.send_offset_button = tk.Button(master, text="原点調整B", font=button_font, command=self.send_offset_b_command)
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

        label_font = ("Arial", 18)
        font_color = '#000000'

        # Getボタンをループで定義
        button_labels = {0: "P-", 1: "Y-", 2: "N", 3: "Y+", 4: "P+", 5: "P-Z", 6: "Y-Z", 7: "NZ", 8: "Y+Z", 9: "P+Z"}

        for idx, i in enumerate(button_labels):
            button = tk.Button(master, text=button_labels[i], font=button_font, command=lambda idx=i: self.get_sensor_command(idx))
            button.pack(pady=10)
            if i < 5:
                button.place(x=50 + idx * 100, y=150)
            else:
                button.place(x=50 + idx * 100 + 50, y=150)

        get_button_positions = {
            0: (580, 200),  # P-
            1: (330, 400),  # Y-
            2: (580, 400),  # N
            3: (830, 400), # Y+
            4: (580, 600),  # P+
            5: (580 + 50, 200),  # P-
            6: (330 + 50, 400),  # Y-
            7: (580 + 50, 400),  # N
            8: (830 + 50, 400), # Y+
            9: (580 + 50, 600)  # P+
        }

        set_label_font = ("Arial", 12)
        for idx, i in enumerate([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]):
            x, y = get_button_positions[i]
            self.value_d_labels.append(
                self.create_label(master, x, y, font_color, set_label_font))
            self.value_s1_labels.append(
                self.create_label(master, x, y + 20, '#FFCC00', set_label_font))
            self.value_s2_labels.append(
                self.create_label(master, x, y + 40, '#00CCFF', set_label_font))
            self.value_angle_labels.append(
                self.create_label(master, x, y + 60, '#FFCCFF', set_label_font))

        # ラベルの定義
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

                    self.fixed_d = (self.measure_d - self.offset_a_d)

                    if self.offset_b_d != 0:
                        error_gain = self.fixed_d / self.offset_b_d
                    else:
                        error_gain = 0

                    self.fixed_s1 = (self.measure_s1 - self.offset_a_s1) - error_gain * self.offset_b_s1
                    self.fixed_s2 = (self.measure_s2 - self.offset_a_s2) - error_gain * self.offset_b_s2

                    if self.calibration:
                        # ヨー軸キャリブレーション処理
                        if self.fixed_s1 >= 0:
                            self.cal_yaw_p_z = (self.cal_delta_yaw_p / self.cal_z) * self.fixed_d + self.cal_yaw_p[0] # ゲイン計算
                            self.fixed_s1 = self.fixed_s1 * self.cal_yaw_p_z
                        else:
                            self.cal_yaw_n_z = (self.cal_delta_yaw_n / self.cal_z) * self.fixed_d + self.cal_yaw_n[0]
                            self.fixed_s1 = self.fixed_s1 * self.cal_yaw_n_z

                        # ピッチ軸キャリブレーション処理
                        if self.fixed_s2 >= 0:
                            self.cal_pitch_p_z = (self.cal_delta_pitch_p / self.cal_z) * self.fixed_d + self.cal_pitch_p[0] # ゲイン計算
                            self.fixed_s2 = self.fixed_s2 * self.cal_pitch_p_z
                        else:
                            self.cal_pitch_n_z = (self.cal_delta_pitch_n / self.cal_z) * self.fixed_d + self.cal_pitch_n[0]
                            self.fixed_s2 = self.fixed_s2 * self.cal_pitch_n_z

                        if self.fixed_s1 >= max_angle:
                            self.fixed_s1 = max_angle
                        elif self.fixed_s1 <= -max_angle:
                            self.fixed_s1 = -max_angle
                        if self.fixed_s2 >= max_angle:
                            self.fixed_s2 = max_angle
                        elif self.fixed_s2 <= -max_angle:
                            self.fixed_s2 = -max_angle

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
            self.thread = threading.Thread(target=self.measurement_loop)
            self.thread.daemon = True
            self.thread.start()
        else:
            self.measuring = False
            self.led_onoff_flag = 0
            self.start_button.config(text="計測開始")

    def calibration_command(self):
        if not self.calibration:
            self.calibration = True
            self.calibration_button.config(text="キャリブレーション停止")
            self.cal_pitch()
            self.cal_yaw()
            self.cal_d()
            with open('TK-01_Calibration.pkl', 'wb') as f:
                pickle.dump([self.cal_pitch_n, self.cal_pitch_p, self.cal_delta_pitch_n, self.cal_delta_pitch_p,
                             self.cal_yaw_n, self.cal_yaw_p, self.cal_delta_yaw_n, self.cal_delta_yaw_p, self.cal_z,
                             self.offset_a_d, self.offset_b_d, self.offset_a_s1, self.offset_b_s1,
                             self.offset_a_s2, self.offset_b_s2], f)
        else:
            self.calibration = False
            self.calibration_button.config(text="キャリブレーション開始")
            self.cal_pitch_p = 1.0
            self.cal_pitch_n = 1.0
            self.cal_yaw_p = 1.0
            self.cal_yaw_n = 1.0
            self.cal_z = 1.0

    def send_offset_a_command(self):
        self.offset_a_d = self.measure_d
        self.offset_a_s1 = self.measure_s1
        self.offset_a_s2 = self.measure_s2

    def send_offset_b_command(self):
        self.offset_b_d = self.fixed_d
        self.offset_b_s1 = self.fixed_s1
        self.offset_b_s2 = self.fixed_s2

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
        if not self.s2[0] == 0:
            self.cal_pitch_n[0] = -max_angle/self.s2[0] #gain0
        if not self.s2[4] == 0:
            self.cal_pitch_p[0] = max_angle/self.s2[4] #gain0

        if not self.s2[5] == 0:
            self.cal_pitch_n[1] = -max_angle/self.s2[5] #gain1
        if not self.s2[9] == 0:
            self.cal_pitch_p[1] = max_angle/self.s2[9] #gain1

        self.cal_delta_pitch_p = self.cal_pitch_p[1] - self.cal_pitch_p[0] # gain1 - gain0
        self.cal_delta_pitch_n = self.cal_pitch_n[1] - self.cal_pitch_n[0] # gain1 - gain0

    def cal_yaw(self):
        if not self.s1[1] == 0:
            self.cal_yaw_n[0] = -max_angle/self.s1[1] #gain0
        if not self.s1[3] == 0:
            self.cal_yaw_p[0] = max_angle/self.s1[3] #gain0

        if not self.s1[6] == 0:
            self.cal_yaw_n[1] = -max_angle/self.s1[6] #gain1
        if not self.s1[8] == 0:
            self.cal_yaw_p[1] = max_angle/self.s1[8] #gain1

        self.cal_delta_yaw_p = self.cal_yaw_p[1] - self.cal_yaw_p[0] # gain1 - gain0
        self.cal_delta_yaw_n = self.cal_yaw_n[1] - self.cal_yaw_n[0] # gain1 - gain0

    def cal_d(self):
        self.cal_z = self.d[7] - self.d[2]


def main():
    root = tk.Tk()
    app = SerialApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.geometry("1200x800")
    root.resizable(False, False)
    root.mainloop()


if __name__ == "__main__":
    main()