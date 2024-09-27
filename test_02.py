import tkinter as tk
from tkinter import messagebox, scrolledtext
import serial
import threading
import time


class SerialApp:
    def __init__(self, master):
        self.master = master
        self.master.title("TK-01 App")
        self.led_onoff_flag = 0
        self.offset_d = [0.0] * 12
        self.offset_s1 = [0.0] * 12
        self.offset_s2 = [0.0] * 12

        self.measure_d = [0.0] * 12
        self.measure_s1 = [0.0] * 12
        self.measure_s2 = [0.0] * 12

        self.measuring_index = None  # 現在計測しているインデックス

        # シリアルポートの初期化
        self.ser = serial.Serial()
        self.ser.port = 'COM8'  # 必要に応じて変更
        self.ser.baudrate = 500000
        self.ser.timeout = 1

        # ウィジェットの配置
        button_font = ("Arial", 16)
        self.start_buttons = []
        self.distance_labels = []
        self.yaw_labels = []
        self.pitch_labels = []

        for i in range(12):
            # 計測開始ボタン
            start_button = tk.Button(master, text=f"計測開始 {i + 1}", font=button_font,
                                     command=lambda i=i: self.toggle_measurement(i))
            start_button.grid(row=i, column=0, padx=10, pady=5)
            self.start_buttons.append(start_button)

            # 計測距離ラベル
            distance_label = tk.Label(master, text="距離: 待機中", font=("Arial", 16))
            distance_label.grid(row=i, column=1, padx=10, pady=5)
            self.distance_labels.append(distance_label)

            # ヨー軸角度ラベル
            yaw_label = tk.Label(master, text="ヨー: 待機中", font=("Arial", 16))
            yaw_label.grid(row=i, column=2, padx=10, pady=5)
            self.yaw_labels.append(yaw_label)

            # ピッチ軸角度ラベル
            pitch_label = tk.Label(master, text="ピッチ: 待機中", font=("Arial", 16))
            pitch_label.grid(row=i, column=3, padx=10, pady=5)
            self.pitch_labels.append(pitch_label)

        # 計測フラグ
        self.measuring = False

        self.result_textbox = scrolledtext.ScrolledText(master, wrap=tk.WORD, width=50, height=10, font=("Arial", 16))
        self.result_textbox.grid(row=13, column=0, columnspan=4, padx=10, pady=20)



        # シリアルポートを開く
        try:
            self.ser.open()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open serial port: {e}")
            for button in self.start_buttons:
                button.config(state='disabled')

    def toggle_measurement(self, index):
        if not self.measuring:
            self.measuring_index = index
            self.measuring = True
            self.start_buttons[index].config(text="計測停止")
            self.thread = threading.Thread(target=self.measurement_loop)
            self.thread.start()
        else:
            self.measuring = False
            self.start_buttons[index].config(text=f"計測開始 {index + 1}")

            self.calculate_a()
            self.calculate_AB()
            self.display_results()


    def measurement_loop(self):
        command = bytes([0x52, 0x01, 0x00, 0x53])  # 計測コマンド
        index = self.measuring_index
        while self.measuring and self.ser.is_open:
            try:
                # コマンドを送信
                self.ser.write(command)
                response = self.ser.read(14)  # 14バイトのレスポンスを読み込む
                gain = 0.95
                self.measure_d[index] = gain * self.measure_d[index] + (1.0 - gain) * (float(int(response[2])) / 10.0)
                self.measure_s1[index] = gain * self.measure_s1[index] + (1.0 - gain) * (
                            float(int(response[3])) / 2.0 - 40.0)
                self.measure_s2[index] = gain * self.measure_s2[index] + (1.0 - gain) * (
                            float(int(response[4])) / 2.0 - 40.0)

                if self.measure_d[index] > 25.4:
                    self.update_gui_d(index, "未検出")
                    self.update_gui_s1(index, "未検出")
                    self.update_gui_s2(index, "未検出")
                else:
                    self.update_gui_d(index, f"{self.measure_d[index] - self.offset_d[index]:04.1f} cm")
                    self.update_gui_s1(index, f"{self.measure_s1[index] - self.offset_s1[index]:04.1f}°")
                    self.update_gui_s2(index, f"{self.measure_s2[index] - self.offset_s2[index]:04.1f}°")

                # self.calculate_a()
            except Exception as e:
                self.update_gui_d(index, f"エラー: {e}")
                break

    def update_gui_d(self, index, text):
        self.distance_labels[index].config(text=f"距離: {text}")

    def update_gui_s1(self, index, text):
        self.yaw_labels[index].config(text=f"ヨー: {text}")

    def update_gui_s2(self, index, text):
        self.pitch_labels[index].config(text=f"ピッチ: {text}")

    def send_offset_command(self, index):
        # 現在の測定値をオフセットとして保存
        self.offset_d[index] = self.measure_d[index]
        self.offset_s1[index] = self.measure_s1[index]
        self.offset_s2[index] = self.measure_s2[index]

    def on_closing(self):
        self.measuring = False
        if self.thread and self.thread.is_alive():
            self.thread.join()
        if self.ser.is_open:
            self.ser.close()
        self.master.destroy()

    def calculate_a(self):
        part1_sum = sum(5.3 - self.measure_d[i] for i in [0, 1, 2, 6, 7, 8])
        part2_sum = sum(0.3 - self.measure_d[i] for i in [3, 4, 5, 9, 10, 11])

        # 合計値を self.a に格納
        self.a = (part1_sum + part2_sum)/12
        print(f"self.a: {self.a}")

    def calculate_AB(self):
        z1 = 0.3
        z2 = 5.3
        r = 7
        if self.measure_s2[0] == 0 or self.measure_s2[3] == 0:
            self.A1 = 0
            self.B1 = 0
        else:
            self.A1 = r * (1 / (z2 - z1)) * (1 / self.measure_s2[0] - 1 / self.measure_s2[3])
            self.B1 = r / self.measure_s2[3] - self.A1 * z1

        if self.measure_s2[2] == 0 or self.measure_s2[5] == 0:
            self.A2 = 0
            self.B2 = 0
        else:
            self.A2 = -r * (1 / (z2 - z1)) * (1 / self.measure_s2[2] - 1 / self.measure_s2[5])
            self.B2 = -r / self.measure_s2[5] - self.A2 * z1

        if self.measure_s1[6] == 0 or self.measure_s1[9] == 0:
            self.A3 = 0
            self.B3 = 0
        else:
            self.A3 = -r * (1 / (z2 - z1)) * (1 / self.measure_s1[6] - 1 / self.measure_s1[9])
            self.B3 = -r / self.measure_s1[9] - self.A3 * z1

        if self.measure_s1[8] == 0 or self.measure_s1[11] == 0:
            self.A4 = 0
            self.B4 = 0
        else:
            self.A4 = r * (1 / (z2 - z1)) * (1 / self.measure_s1[8] - 1 / self.measure_s1[11])
            self.B4 = r / self.measure_s1[11] - self.A4 * z1

        print(f"self.A1: {self.A1}, self.B1: {self.B1}")
        print(f"self.A2: {self.A2}, self.B2: {self.B2}")
        print(f"self.A3: {self.A3}, self.B3: {self.B3}")
        print(f"self.A4: {self.A4}, self.B4: {self.B4}")

        def display_results(self):
            # テキストボックスをクリア
            self.result_textbox.delete(1.0, tk.END)

            # 結果をテキストボックスに追加
            result_text = (
                f"a = {self.a}\n"
                f"A1 = {self.A1}\nB1 = {self.B1}\n"
                f"A2 = {self.A2}\nB2 = {self.B2}\n"
                f"A3 = {self.A3}\nB3 = {self.B3}\n"
                f"A4 = {self.A4}\nB4 = {self.B4}\n"
            )
            self.result_textbox.insert(tk.END, result_text)
            self.result_textbox.config(state=tk.NORMAL)




def main():
    root = tk.Tk()
    app = SerialApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.geometry("1000x700")
    root.resizable(False, False)
    root.mainloop()


if __name__ == "__main__":
    main()
