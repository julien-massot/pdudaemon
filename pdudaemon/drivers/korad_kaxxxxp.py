# pdudaemon/drivers/korad_kaxxxxp.py
import time
import serial
import logging
import os
from pdudaemon.drivers.driver import PDUDriver
log = logging.getLogger("pdud.drivers." + os.path.basename(__file__))

class KoradKAxxxxP(PDUDriver):
    """
    Config parameters (pdudaemon.conf):
      device: "/dev/ttyACM0" (or /dev/ttyUSB0)
      baudrate: 9600 (default)
    """
    def __init__(self, hostname, settings):
        super().__init__()
        self.dev = settings.get("device", "/dev/ttyACM0")
        self.baudrate = int(settings.get("baudrate", 9600))
        self.idn = None
        #log.info("Connected to: " + self._identify())

    @classmethod
    def accepts(cls, drivername):
        log.info("accepts: " + drivername)
        if drivername == "korad-kaxxxxp":
            return True
        return False

    def _open(self):
        # No newline protocol; use short timeouts.
        return serial.Serial(
            self.dev,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.2,
            write_timeout=0.5,
        )

    def _write(self, ser, s: str):
        ser.reset_input_buffer()
        ser.write(s.encode("ascii"))
        ser.flush()

    def _read_until_idle(self, ser) -> bytes:
        # For unterminated variable-length replies (e.g. *IDN?)
        buf = bytearray()
        last_rx = time.time()
        # 2 second timeout
        deadline = time.time() + 2.0
        while time.time() < deadline:
            chunk = ser.read(64)
            if chunk:
                buf += chunk
                last_rx = time.time()
            else:
                if time.time() - last_rx >= 0.15:
                    break
        return bytes(buf)

    def _identify(self, ser):
        self._write(ser, "*IDN?")
        self.idn = self._read_until_idle(ser).decode("ascii", errors="replace").strip()

    def port_interaction(self, command, port_number):
        if command == "on":
            cmd = "OUT1"
        elif command == "off":
            cmd = "OUT0"
        else:
            log.error("Unknown command %s.", (command))
            return

        with self._open() as ser:
            if self.idn is None:
                self._identify(ser)
                log.info("Connected to: %s", self.idn)
            self._write(ser, cmd)
