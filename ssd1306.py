import framebuf

class SSD1306_I2C(framebuf.FrameBuffer):
    def __init__(self, width, height, i2c, addr=0x3C):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.pages = height // 8
        self.buffer = bytearray(self.pages * width)

        super().__init__(
            self.buffer,
            width,
            height,
            framebuf.MONO_VLSB
        )

        self.init_display()

    def write_cmd(self, cmd):
        self.i2c.writeto(self.addr, bytes([0x80, cmd]))

    def init_display(self):
        cmds = [
            0xAE,
            0x20, 0x00,
            0x40,
            0xA1,
            0xC8,
            0xA8, self.height - 1,
            0xD3, 0x00,
            0xDA, 0x12,
            0x81, 0x7F,
            0xA4,
            0xA6,
            0xD5, 0x80,
            0xD9, 0xF1,
            0xDB, 0x30,
            0x8D, 0x14,
            0xAF
        ]

        for cmd in cmds:
            self.write_cmd(cmd)

        self.fill(0)
        self.show()

    def show(self):
        self.write_cmd(0x21)
        self.write_cmd(0)
        self.write_cmd(self.width - 1)

        self.write_cmd(0x22)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)

        self.i2c.writeto(
            self.addr,
            b'\x40' + self.buffer
        )