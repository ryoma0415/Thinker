import math
import tkinter as tk
import serial
import threading
from PIL import Image, ImageTk
from tkinter import ttk, messagebox
import serial.tools.list_ports
import pickle

max_angle = 3.5

class SerialApp:
    def __init__(self, master):
        self.master = master
        self.master.title("TK-01 App")

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

        # ラベルのリストを初期化
        self.value_d_labels = []
        self.value_s1_labels = []
        self.value_s2_labels = []
        self.value_angle_labels = []

        self.cal_yaw_p = [1.0, 1.0]
        self.cal_yaw_n = [1.0, 1.0]
        self.cal_pitch_p = [1.0, 1.0]
        self.cal_pitch_n = [1.0, 1.0]
        self.cal_z = 1.0

        self.d = [0.0] * 10
        self.s1 = [0.0] * 10
        self.s2 = [0.0] * 10
        self.angle = [0.0] * 10

        self.img_x = 600
        self.img_y = 150

        self.calibration = False

        # Canvasを追加
        self.canvas = tk.Canvas(master, width=500, height=500, bg="white")
        self.canvas.pack()
        self.canvas.place(x=self.img_x, y=self.img_y)

        # 画像
        self.img = Image.open("sensor.png")
        self.back_img = self.img.resize((500, 500), Image.LANCZOS)
        self.background_img = ImageTk.PhotoImage(self.back_img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.background_img)
        self.image_label = tk.Label(master, image=self.background_img)

        # 接続状態を表示するラベル
        self.connection_status_label = tk.Label(master, text="未接続", font=("Arial", 12))
        self.connection_status_label.pack()
        self.connection_status_label.place(x=10, y=10)

        # COMポート選択のプルダウンメニュー
        self.com_port_var = tk.StringVar()
        self.com_ports = self.get_com_ports
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

        self.reset_button = tk.Button(master, text="リセット", font=button_font, command=self.reset_command)
        self.reset_button.pack(pady=20)
        self.reset_button.place(x=190, y=60)

        self.send_offset_button = tk.Button(master, text="原点調整 ニュートラル", font=button_font, command=self.send_offset_a_command)
        self.send_offset_button.pack(pady=10)
        self.send_offset_button.place(x=10, y=260)

        self.send_offset_button = tk.Button(master, text="原点調整 押し込み", font=button_font, command=self.send_offset_b_command)
        self.send_offset_button.pack(pady=10)
        self.send_offset_button.place(x=10, y=320)

        self.calibration_button = tk.Button(master, text="キャリブレーション ON", font=button_font, command=self.calibration_command)
        self.calibration_button.pack(pady=10)
        self.calibration_button.place(x=10, y=380)

        # self.calibration_load_button = tk.Button(master, text="キャリブレーションファイル　読み込み", font=button_font, command=self.load_calibration)
        # self.calibration_load_button.pack(pady=10)
        # self.calibration_load_button.place(x=10, y=440)


        # キャリブレーション用の計測ボタン作成
        button_place = [[670, 280],[470, 470],[920, 280],[1050, 470],[785, 690],[750, 280],[550, 470],[1000, 280],[1130, 470],[865, 690]]
        button_font_2 = ("Arial", 12)

        for i in range(10):
            button = tk.Button(master, text="計測開始", font=button_font_2, command=lambda idx=i: self.get_sensor_command(idx))
            button.pack(pady=5)
            button.place(x=button_place[i][0], y=button_place[i][1])

        # キャリブレーション用測定値のフレームと値
        label_font = ("Arial", 18)
        font_color = '#000000'
        frame_color = ["#ADD8E6", "#FFFFE0", "#90EE90"]

        for i in range(10):
            if i in (0,4,5,9):
                frame = tk.LabelFrame(master, bg=frame_color[0], text="")
            elif i in (1,3,6,8):
                frame = tk.LabelFrame(master, bg=frame_color[1], text="")
            else:
                frame = tk.LabelFrame(master, bg=frame_color[2], text="")
            frame.pack()
            frame.place(x=button_place[i][0], y=button_place[i][1]-120, width=80, height=125)

        set_label_font = ("Arial", 10)
        for i in range(10):
            x, y = button_place[i][0]+5, button_place[i][1]-5
            self.value_d_labels.append(self.create_label(master, "d:0.0", x, y-104, set_label_font, font_color))
            self.value_s1_labels.append(self.create_label(master, "Y:0.0", x, y-78, set_label_font, font_color))
            self.value_s2_labels.append(self.create_label(master, "P:0.0", x, y-52, set_label_font, font_color))
            self.value_angle_labels.append(self.create_label(master, "θ:0.0", x, y-26, set_label_font, font_color))

        # ラベルの定義
        self.binary_label_d = tk.Label(master, text="d  Binary : 255", font=label_font, foreground=font_color)
        self.binary_label_d.pack(pady=5)
        self.binary_label_d.place(x=10, y=120)

        self.binary_label_s1 = tk.Label(master, text="Y  Binary : 255", font=label_font, foreground=font_color)
        self.binary_label_s1.pack(pady=5)
        self.binary_label_s1.place(x=10, y=165)

        self.binary_label_s2 = tk.Label(master, text="P  Binary : 255", font=label_font, foreground=font_color)
        self.binary_label_s2.pack(pady=5)
        self.binary_label_s2.place(x=10, y=210)

        self.data_label_d = tk.Label(master, text="距離 : 0.0 mm", font=label_font, foreground=font_color)
        self.data_label_d.pack(pady=5)
        self.data_label_d.place(x=180, y=120)

        self.data_label_s1 = tk.Label(master, text="角度 : 0.0 deg", font=label_font, foreground=font_color)
        self.data_label_s1.pack(pady=5)
        self.data_label_s1.place(x=180, y=165)

        self.data_label_s2 = tk.Label(master, text="角度 : 0.0 deg", font=label_font, foreground=font_color)
        self.data_label_s2.pack(pady=5)
        self.data_label_s2.place(x=180, y=210)

        # Initialize serial port
        self.ser = serial.Serial()
        self.ser.baudrate = 500000
        self.ser.timeout = 1

        # Measurement control flag
        self.measuring = False

        # Thread for handling the measurement loop
        self.thread = None


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

                    if not self.offset_b_d == 0:
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

                    self.update_gui_binary_d(f"d  Binary : {int(response[2])}")
                    self.update_gui_binary_s1(f"Y  Binary : {int(response[3])}")
                    self.update_gui_binary_s2(f"P  Binary : {int(response[4])}")
                    self.update_gui_d(f"距離 : {self.fixed_d:04.1f} mm")
                    self.update_gui_s1(f"角度 : {self.fixed_s1:04.1f} deg")
                    self.update_gui_s2(f"角度 : {self.fixed_s2:04.1f} deg")

            except Exception as e:
                self.update_gui_d(f"エラー: {e}")
                break


    def toggle_measurement(self):
        if not self.measuring:
            self.measuring = True
            self.start_button.config(text="計測停止")
            self.thread = threading.Thread(target=self.measurement_loop)
            self.thread.daemon = True
            self.thread.start()
        else:
            self.measuring = False
            self.start_button.config(text="計測開始")

    def send_offset_a_command(self):
        self.offset_a_d = self.measure_d
        self.offset_a_s1 = self.measure_s1
        self.offset_a_s2 = self.measure_s2

    def send_offset_b_command(self):
        self.offset_b_d = self.fixed_d
        self.offset_b_s1 = self.fixed_s1
        self.offset_b_s2 = self.fixed_s2

    def reset_command(self):
        self.d = [0.0] * 10
        self.s1 = [0.0] * 10
        self.s2 = [0.0] * 10
        self.angle = [0.0] * 10

        for i in range(10):
            self.value_d_labels[i].config(text="d:0.0")
            self.value_s1_labels[i].config(text="Y:0.0")
            self.value_s2_labels[i].config(text="P:0.0")
            self.value_angle_labels[i].config(text="θ:0.0")

    def get_sensor_command(self, idx):
        self.d[idx] = self.fixed_d
        self.s1[idx] = self.fixed_s1
        self.s2[idx] = self.fixed_s2
        self.angle[idx] = math.atan2(self.s1[idx], self.s2[idx])

        self.value_d_labels[idx].config(text=f"d:{self.d[idx]:.2f}")
        self.value_s1_labels[idx].config(text=f"Y:{self.s1[idx]:.2f}")
        self.value_s2_labels[idx].config(text=f"P:{self.s2[idx]:.2f}")
        self.value_angle_labels[idx].config(text=f"θ:{self.angle[idx]:.2f}")


    def calibration_command(self):
        if not self.calibration:
            self.calibration = True
            self.calibration_button.config(text="キャリブレーション OFF")
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
            self.calibration_button.config(text="キャリブレーション ON")

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


    def create_label(self, master,text, x, y, font, color):
        label = tk.Label(master, text=text, font=font, foreground=color)
        label.pack()
        label.place(x=x, y=y)
        return label

    def update_gui_d(self, text):
        self.data_label_d.config(text=text)

    def update_gui_s1(self, text):
        self.data_label_s1.config(text=text)

    def update_gui_s2(self, text):
        self.data_label_s2.config(text=text)

    def update_gui_binary_d(self, text):
        self.binary_label_d.config(text=text)

    def update_gui_binary_s1(self, text):
        self.binary_label_s1.config(text=text)

    def update_gui_binary_s2(self, text):
        self.binary_label_s2.config(text=text)

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

    # def load_calibration(self):
    #     try:
    #         with open('TK-01_Calibration.pkl', 'rb') as f:
    #             self.calibration_data = pickle.load(f)
    #     except FileNotFoundError:
    #         messagebox.showerror("Error", "Calibration file not found.")
    #     except Exception as e:
    #         messagebox.showerror("Error", f"Failed to load calibration file: {e}")
    #
    #     if self.calibration_data:
    #         self.cal_pitch_n = self.calibration_data[0]
    #         self.cal_pitch_p = self.calibration_data[1]
    #         self.cal_delta_pitch_n = self.calibration_data[2]
    #         self.cal_delta_pitch_p = self.calibration_data[3]
    #         self.cal_yaw_n = self.calibration_data[4]
    #         self.cal_yaw_p = self.calibration_data[5]
    #         self.cal_delta_yaw_n = self.calibration_data[6]
    #         self.cal_delta_yaw_p = self.calibration_data[7]
    #         self.cal_z = self.calibration_data[8]
    #         self.offset_a_d = self.calibration_data[9]
    #         self.offset_b_d = self.calibration_data[10]
    #         self.offset_a_s1 = self.calibration_data[11]
    #         self.offset_b_s1 = self.calibration_data[12]
    #         self.offset_a_s2 = self.calibration_data[13]
    #         self.offset_b_s2 = self.calibration_data[14]


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


def main():
    root = tk.Tk()
    app = SerialApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.geometry("1500x900")
    root.resizable(False, False)
    root.mainloop()

if __name__ == "__main__":
    main()