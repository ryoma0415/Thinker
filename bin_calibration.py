import tkinter as tk
from tkinter import messagebox
import serial
import threading
import time



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

        #ボタン
        #---------------------------------------------------------------------------------------------------------------
        # Create a button to start and stop measurement
        button_font = ("Arial", 16)
        self.start_button = tk.Button(master, text="計測開始",font=button_font, command=self.toggle_measurement)
        self.start_button.pack(pady=20)
        self.start_button.place(x=10,y=10)

        # Create a button to send a specific command
        self.led_on_button = tk.Button(master, text="不透明設定",font=button_font, command=self.send_LED_ON_command)
        self.led_on_button.pack(pady=10)
        self.led_on_button.place(x=200,y=10)

        # Create a button to send a specific command
        self.led_off_button = tk.Button(master, text="透明設定",font=button_font, command=self.send_LED_OFF_command)
        self.led_off_button.pack(pady=10)
        self.led_off_button.place(x=400,y=10)

        # Create a button to send a specific command
        self.send_offset_button = tk.Button(master, text="原点調整",font=button_font, command=self.send_offset_command)
        self.send_offset_button.pack(pady=10)
        self.send_offset_button.place(x=600,y=10)
        #ラベル
        #---------------------------------------------------------------------------------------------------------------
        # Labels for displaying data
        label_font = ("Arial", 64)
        self.data_label_d = tk.Label(master, text="計測距離: 待機中", font=label_font)
        self.data_label_d.pack(pady=5)
        self.data_label_d.place(x=10, y=100)

        self.data_label_s1 = tk.Label(master, text="計測ヨー軸角度: 待機中", font=label_font)
        self.data_label_s1.pack(pady=5)
        self.data_label_s1.place(x=10, y=300)

        self.data_label_s2 = tk.Label(master, text="計測ピッチ軸角度: 待機中", font=label_font)
        self.data_label_s2.pack(pady=5)
        self.data_label_s2.place(x=10, y=500)

        # Initialize serial port
        self.ser = serial.Serial()
        self.ser.port = 'COM8'  # Update as needed
        self.ser.baudrate = 500000
        self.ser.timeout = 1

        # Measurement control flag
        self.measuring = False

        # Thread for handling the measurement loop
        self.thread = None

        # Try to open the serial port
        try:
            self.ser.open()
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
            self.thread.start()
        else:
            self.measuring = False
            self.led_onoff_flag = 0
            self.start_button.config(text="計測開始")
            self.led_on_button.config(text="透明設定")
            self.led_off_button.config(text="不透明設定")

    def send_LED_ON_command(self):

        if self.led_onoff_flag == 0:
            # Define the specific command to send
            command = bytes([0x4C, 0x01, 0x01, 0x4E])  # Update with your specific command
            self.ser.write(command)
            response_LED = self.ser.read(22)  # Update based on expected response length
            #self.data_label.config(text=f"受信データ: {response_LED}")

    def send_LED_OFF_command(self):

        if self.led_onoff_flag == 0:
            # Define the specific command to send
            command = bytes([0x4C, 0x01, 0x00, 0x4D])  # Update with your specific command
            self.ser.write(command)
            response_LED = self.ser.read(22)  # Update based on expected response length
            #self.data_label.config(text=f"受信データ: {response_LED}")

    def send_offset_command(self):
        self.offset_d  = self.measure_d
        self.offset_s1 = self.measure_s1
        self.offset_s2 = self.measure_s2

    def measurement_loop(self):
        command = bytes([0x52, 0x01, 0x00, 0x53])
        while self.measuring and self.ser.is_open:
            try:
                # Send the command to the device
                self.ser.write(command)
                # Wait for the response of 14 bytes
                response = self.ser.read(14)
                gain = 0.95
                self.measure_d = gain*self.measure_d + (1.0-gain)*(float(int(response[2])) / 10.0)
                self.measure_s1 = gain*self.measure_s1 + (1.0-gain)*(float(int(response[3])) / 2.0 - 40.0)
                self.measure_s2 = gain*self.measure_s2 + (1.0-gain)*(float(int(response[4])) / 2.0 - 40.0)

                if self.measure_d > 25.4:
                    self.update_gui_d(f"計測距離: 未検出")
                    self.update_gui_s1(f"計測ヨー軸角度: 未検出")
                    self.update_gui_s2(f"計測ピッチ軸角度: 未検出")
                else:
                    self.update_gui_d(f"計測距離: {self.measure_d - self.offset_d:04.1f}")
                    self.update_gui_s1(f"計測ヨー軸角度: {self.measure_s1 - self.offset_s1:04.1f}")
                    self.update_gui_s2(f"計測ピッチ軸角度: {self.measure_s2 - self.offset_s2:04.1f}")
                    #self.data_label.config(text=f"Data: {response_LED}")
            except Exception as e:
                self.update_gui_d(f"エラー: {e}")
                break
            #time.sleep(0.1)

    def update_gui_d(self, text):
        self.data_label_d.config(text=text)

    def update_gui_s1(self, text):
        self.data_label_s1.config(text=text)

    def update_gui_s2(self, text):
        self.data_label_s2.config(text=text)

    def on_closing(self):
        self.measuring = False
        if self.thread and self.thread.is_alive():
            self.thread.join()
        if self.ser.is_open:
            self.ser.close()
        self.master.destroy()

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