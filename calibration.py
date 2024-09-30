
"""
以下のパラメータa0~D2までを削除して、コピーしたパラメータをペースト
38行目あたり:self.ser.port = 'COM8'
COM8は接続されているシリアルポートに変更
"""

a0 = -1.14
A1, B1 = 0.28, 0.25
A2, B2 = 0.32, 0.35
A3, B3 = 0.23, 0.28
A4, B4 = 0.23, 0.24
C1, D1 = 0.23, 0.24
C2, D2 = 0.25, 0.31




import tkinter as tk
from tkinter import messagebox
import serial
import threading


class SerialApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Calibration App")
        self.measure_d = 0.0
        self.measure_s1 = 0.0
        self.measure_s2 = 0.0
        self.calibrate_d = 0.0
        self.calibrate_s1 = 0.0
        self.calibrate_s2 = 0.0

        # resetting of Serial port
        self.ser = serial.Serial()
        self.ser.port = 'COM8'  # Update as needed
        self.ser.baudrate = 500000
        self.ser.timeout = 1

        # Measurement control flag
        self.measuring = False

        # Thread for handling the measurement loop
        self.thread = None

#------- Create a button to start and stop measurement------------------------------------------------------------------
        button_font = ("Arial", 16)
        self.start_button = tk.Button(master, text="計測開始", font=button_font,command=self.toggle_measurement)
        self.start_button.grid(row=0, column=0, padx=10, pady=10)

#------- Labels for displaying data-------------------------------------------------------------------------------------
        label_font = ("Arial", 42)
        self.data_label_d = tk.Label(master, text="計測距離: 待機中", font=label_font)
        self.data_label_d.grid(row=1, column=0, padx=10, pady=10)

        self.label_cal_d = tk.Label(master, text="補償後距離: ", font=label_font)
        self.label_cal_d.grid(row=1, column=1, padx=10, pady=10)

        self.yaw_label = tk.Label(master, text="計測ヨー角: 待機中", font=label_font)
        self.yaw_label.grid(row=2, column=0, padx=10, pady=10)

        self.cal_yaw_label = tk.Label(master, text="補償後ヨー角: ", font=label_font)
        self.cal_yaw_label.grid(row=2, column=1, padx=10, pady=10)

        self.pitch_label = tk.Label(master, text="計測ピッチ角: 待機中", font=label_font)
        self.pitch_label.grid(row=3, column=0, padx=10, pady=10)

        self.cal_pitch_label = tk.Label(master, text="補償後ピッチ角: ", font=label_font)
        self.cal_pitch_label.grid(row=3, column=1, padx=10, pady=10)

        # Try to open the serial port
        try:
            self.ser.open()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open serial port: {e}")
            self.start_button.config(state='disabled')



    def toggle_measurement(self):
        if not self.measuring:
            self.measuring = True
            self.start_button.config(text="計測停止")
            self.thread = threading.Thread(target=self.measurement_loop)
            self.thread.start()
        else:
            self.measuring = False
            self.start_button.config(text="計測開始")

            # Calibration after finishing measurement
            self.calibration_d()
            self.calibration_s1()
            self.calibration_s2()

            # Display the calibrated data
            if self.calibrate_d == 0:
                self.label_cal_d.config(text="Error")
            else:
                self.label_cal_d.config(text=f"補償後距離: {self.calibrate_d:04.1f}")

            self.cal_yaw_label.config(text=f"補償後ヨー角: {self.calibrate_s1:04.1f}")
            self.cal_pitch_label.config(text=f"補償後ピッチ角: {self.calibrate_s2:04.1f}")


    def measurement_loop(self):
        command = bytes([0x52, 0x01, 0x00, 0x53])
        while self.measuring and self.ser.is_open:
            try:
                # Send the command to the device
                self.ser.write(command)
#--------------- Wait for the response of 14 bytes ---------------------------------------------------------------------
                # information of distance: 3rd number of 14 bytes(response[2])
                # information of yaw: 4th number of 14 bytes(response[3])
                # information of pitch: 5th number of 14 bytes(response[4])
                # by using int(), change byte data for number
                # by using float(), maintain the accuracy
                response = self.ser.read(14)
                gain = 0.95
                self.measure_d = gain*self.measure_d + (1.0-gain)*(float(int(response[2])) / 10.0)
                self.measure_s1 = gain*self.measure_s1 + (1.0-gain)*(float(int(response[3])) / 2.0 - 40.0)
                self.measure_s2 = gain*self.measure_s2 + (1.0-gain)*(float(int(response[4])) / 2.0 - 40.0)

                if self.measure_d > 25.4:
                    self.update_gui_d(f"計測距離: 未検出")
                    self.update_gui_s1(f"計測ヨー角度: 未検出")
                    self.update_gui_s2(f"計測ピッチ角度: 未検出")
                else:
                    # by using 04.1f, easy to read
                    self.update_gui_d(f"計測距離: {self.measure_d}:04.1f")
                    self.update_gui_s1(f"計測ヨー角度: {self.measure_s1}:04.1f")
                    self.update_gui_s2(f"計測ピッチ角度: {self.measure_s2}:04.1f")

            except Exception as e:
                self.update_gui_d(f"エラー: {e}")
                break

    def update_gui_d(self, text):
        self.data_label_d.config(text=text)
    def update_gui_s1(self, text):
        self.yaw_label.config(text=text)
    def update_gui_s2(self, text):
        self.pitch_label.config(text=text)

    def on_closing(self):
        self.measuring = False
        # when thread is moving
        if self.thread and self.thread.is_alive():
            # Main program wait for thread working by using thread.join() command
            self.thread.join()
        if self.ser.is_open:
            self.ser.close()
        self.master.destroy()

    def calibration_d(self):
        if self.measure_s2 >= 0:
            if 0.98 <= C1*self.measure_s2 <= 1.02:
                self.calibrate_d = (self.measure_d + D1*self.measure_s2 + a0) / (1 - C1*self.measure_s2)
        else:
            if 0.98 <= C2*self.measure_s2 <= 1.02:
                self.calibrate_d = (self.measure_d + D2*self.measure_s2 + a0) / (1 - C2*self.measure_s2)

    def calibration_s1(self):
        if self.measure_s1 >= 0:
            self.calibrate_s1 = (A1*self.calibrate_d + B1)*self.measure_s1
        else:
            self.calibrate_s1 = (A2*self.calibrate_d + B2)*self.measure_s1

    def calibration_s2(self):
        if self.measure_s2 >= 0:
            self.calibrate_s2 = (A4*self.calibrate_d + B4)*self.measure_s2
        else:
            self.calibrate_s2 = (A3*self.calibrate_d + B3)*self.measure_s2

def main():
    root = tk.Tk()
    app = SerialApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.geometry("1200x800")
    root.resizable(False, False)
    root.mainloop()

# Run the app
if __name__ == "__main__":
    main()