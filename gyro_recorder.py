# import serial
import serial
import threading
import time
import datetime
import pathlib
import os
import configparser
import sys
import re

import serial_dummy

VERSION = "1.0.0"
SETTINGFILENAME = "config.ini"


class TA7573:
    read_thread = None
    key_interrupt = False
    write_buffer_counter = 1
    write_buffer = []
    fail_record = False
    com_record = False

    def __init__(self, line_num=100, debug=False):
        self.line_num = line_num
        self.start_date = None
        baudrate = 115200
        if pathlib.Path(SETTINGFILENAME).exists():
            inifile = configparser.ConfigParser()
            inifile.read(SETTINGFILENAME, 'utf-8')
            self.msg_speed = int(inifile.get('settings', 'msg_speed'))
            output_dir = inifile.get('settings', 'output_dir')
            serial_name = inifile.get('settings', 'comport')
            self.fail_record = inifile.getboolean('settings', 'fail_record')
            self.com_record = inifile.getboolean('settings', 'com_record')
            baudrate = int(inifile.get('settings', 'baudrate'))
        else:
            with open(SETTINGFILENAME, 'w') as f:
                f.write("[settings]\nmsg_speed = 1\noutput_dir = output\ncomport = COM10\n")
            self.msg_speed = 1
            output_dir = "output"
            serial_name = "COM10"
        self.serial = serial.Serial(serial_name, baudrate=baudrate) if not debug else serial_dummy.SerialDummy()
        self.save_dir = pathlib.Path('{}/'.format(output_dir))
        if not self.save_dir.exists():
            self.save_dir.mkdir()

    def __del__(self):
        self.serial_stop()
        self.serial.close()

    def get_filename(self):
        #return datetime.datetime.now().strftime('%Y%m%d_%H00.csv')
        return datetime.datetime.now().strftime('%Y%m%d_%H%M%S.csv')

    def chechsum(self, check_string):
        xor = 0
        for character in check_string:
            xor ^= ord(character)

        return xor

    def data_check(self, data):
        if ("$TSC," in data) and ('*' in data):
            if (not self.com_record) and ("$TSC,COM" in data):
                return False
            result = re.match(r'^\$([\s\S]*)\*(\w{2})', data)
            if self.chechsum(result.group(1)) == int(result.group(2), 16):
                return result.group(1)
            elif self.fail_record:
                return "checksum error," + data
        elif self.fail_record:
            return "header not found error," + data
        return False

    def add_write_buffer(self, data):
        if len(self.write_buffer) >= self.line_num:
            self.write_buffer = self.write_buffer[1:]

        append_data = self.data_check(data[:-2].decode('utf-8'))
        if append_data:
            append_data = ",".join(append_data.split(',')[1:-4])
        else:
            return
        self.start_date += datetime.timedelta(milliseconds=int(1000/self.msg_speed))
        self.write_buffer.append("{},{},{}".format(
            datetime.datetime.now(),
            self.start_date,
            append_data
        ))

        if self.write_buffer_counter >= self.line_num:
            with open(self.save_dir / self.get_filename(), 'a', encoding='utf-8') as f:
                write_string = ""
                for data in self.write_buffer:
                    write_string += data + "\n"
                f.write(write_string)
            self.write_buffer_counter = 1
        else:
            self.write_buffer_counter += 1

    def serial_start(self):
        self.start_date = datetime.datetime.now()
        self.serial.write(b"$TSC,COM\r\n")
        self.read_thread = threading.Thread(target=self.serial_read)
        self.write_buffer_counter = 0
        self.read_thread.start()

    def serial_stop(self):
        self.serial.write(b"$TSC,MSG1,000\r\n")
        line_data = self.serial.readline()
        if b'$TSC,ACK,*0D\r\n' in line_data:
            return True
        return False

    def serial_read(self):
        self.serial.write("$TSC,MSG1,{:03}\r\n".format(self.msg_speed).encode())
        self.key_interrupt = False
        counter = 0
        while not self.key_interrupt:
            try:
                line_data = self.serial.readline()
                self.add_write_buffer(line_data)
                if counter > self.msg_speed:
                    os.system('cls')
                    for data in self.write_buffer[:10]:
                        sys.stdout.write(data + "\r\n")
                    sys.stdout.write("終了するにはEnterキーを入力してください。")
                    sys.stdout.flush()
                    counter = 0
                else:
                    counter += 1
            except:
                print("Exception raised.")
        self.serial_stop()

    def key_wait(self):
        input()
        self.key_interrupt = True
        self.read_thread.join()
        self.serial_stop()
        if self.write_buffer_counter != 1:
            with open(self.save_dir / self.get_filename(), 'a', encoding='utf-8') as f:
                write_string = ""
                for data in self.write_buffer[self.write_buffer_counter - 1:]:
                    write_string += data + "\n"
                f.write(write_string)

    def set_msg_speed(self):
        print('1, 2, 5, 10, 20, 50, 100 [Hz]のいずれかの')
        print('データ送信周波数を入力してください。')
        input_num = int(input('->'))
        if (input_num == 1) or (input_num == 2) or (input_num == 5) or (input_num == 10) or (input_num == 20) or (input_num == 50) or (input_num == 100):
            self.msg_speed = input_num

    def angle_reset_requirement(self):
        while True:
            if self.serial_stop():
                break
        self.serial.write(b"$TSC,RALN,1\r\n")
        line_data = self.serial.readline()
        print(line_data)
        if line_data == b'$TSC,ACK,*0D\r\n':
            print('角度リセット要求成功。')
            input('->(Enter)')
        else:
            print('角度リセット失敗、もう一度試してください。')
            input('->(Enter)')

    def offset_cancel_requirement(self):
        while True:
            if self.serial_stop():
                break
        self.serial.write(b"$TSC,OFC,X,Y,Z\r\n")
        line_data = self.serial.readline()
        print(line_data)
        if line_data == b'$TSC,ACK,*0D\r\n':
            print('オフセットキャンセル要求成功。')
            input('->(Enter)')
        else:
            print('オフセットキャンセル失敗、もう一度試してください。')
            input('->(Enter)')

    def speed_change(self, speed):
        self.serial.write(b"$TSC,COM\r\n")
        line_data = self.serial.readline()
        print(line_data.decode())
        time.sleep(0.5)
        self.serial.write("$TSC,COM,{:06},8,NON,1,\r\n".format(speed).encode())
        line_data = self.serial.readline()
        print(line_data)
        if line_data == b'$TSC,ACK,*0D\r\n':
            print('通信速度設定変更成功。本体を再起動して下さい。')
            input('->(Enter)')
        else:
            print('通信速度設定失敗、もう一度試してください。')
            input('->(Enter)')

    def main(self):
        while True:
            os.system('cls')
            print("実行したい処理の数字を入力してください。")
            print("計測開始\t\t\t:1\n取得周波数変更\t\t\t:2\n角度リセット要求\t\t:3\nオフセットキャンセル要求\t:4\n通信速度変更\t:5\n終了\t\t\t:0")
            print("現在の取得周波数：{} Hz".format(self.msg_speed))
            input_str = input("->")
            
            if input_str == "1":
                self.serial_start()
                self.key_wait()
            elif input_str == "2":
                self.set_msg_speed()
            elif input_str == "3":
                self.angle_reset_requirement()
            elif input_str == "4":
                self.offset_cancel_requirement()
            elif input_str == "5":
                speed = int(input("Input speed ->"))
                self.speed_change(speed)
            elif input_str == "0":
                exit()
            else:
                print("0～4を入力してください。")


if __name__ == '__main__':
    gyro = TA7573(debug=False)
    gyro.main()


