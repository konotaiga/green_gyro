class SerialDummy:
    status = "stop"

    def __init__(self):
        pass

    def close(self):
        print("close.")

    def write(self, message):
        print("write:", message)
        if "MSG1" in message:
            status = "message1"

    def chechsum(self, check_string):
        xor = 0
        for character in check_string:
            xor ^= ord(character)

        return xor

    def readline(self):
        information_str = "TSC,MSG1,{},{},{},{},{},{},{},{},{},{},{},{},{}".format(
            (1 << 9) | 0x0F,  # ステータス
            123.45,  # ロール角[deg]
            12.34,  # ピッチ角[deg]
            123.45,  # ヨー角[deg]
            123.45,  # X軸角速度[deg/s]
            123.45,  # Y軸角速度[deg/s]
            123.45,  # Z軸角速度[deg/s]
            123.45,  # X軸加速度[m/s^2]
            123.45,  # Y軸加速度[m/s^2]
            123.45,  # Z軸加速度[m/s^2]
            11.111,  # 外部アナログ信号
            00.000,  # 予備
            00.000,  # 予備
        )
        return "${}*{}\r\n".format(
            information_str,
            self.chechsum(information_str)
        )

if __name__ == "__main__":
    dummy = SerialDummy()
    print(dummy.readline())

