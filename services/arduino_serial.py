# services/arduino_serial.py
import time
from typing import Optional
 
try:
    import serial  # pyserial
except ImportError:
    serial = None
 
 
class ArduinoSerial:
    """
    Wrapper simple et robuste pour communiquer avec un Arduino via USB Serial.
 
    Commandes typiques envoyées:
      - ON
      - OFF
      - PING
    Réponses attendues (optionnel):
      - OK / ACK / PONG / etc.
    """
 
    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        baudrate: int = 9600,
        timeout: float = 1.0,
        boot_delay: float = 2.0
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.boot_delay = boot_delay
 
    def _ensure_pyserial(self):
        if serial is None:
            raise RuntimeError(
                "pyserial n'est pas installé. Installe-le avec: pip install pyserial"
            )
 
    def send(self, command: str, expect_reply: bool = False) -> Optional[str]:
        """
        Envoie une commande à l'Arduino.
        - command: ex 'ON', 'OFF'
        - expect_reply: si True, lit une ligne de réponse
 
        Retour:
          - réponse (str) si expect_reply=True et réponse reçue
          - None sinon
        """
        self._ensure_pyserial()
 
        cmd = (command.strip() + "\n").encode("utf-8")
 
        with serial.Serial(self.port, self.baudrate, timeout=self.timeout) as ser:
            # Beaucoup d'Arduino rebootent à l'ouverture du port série
            time.sleep(self.boot_delay)
 
            # Nettoyage buffer
            try:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
            except Exception:
                pass
 
            ser.write(cmd)
            ser.flush()
 
            if not expect_reply:
                return None
 
            # Lire une réponse (1 ligne)
            reply = ser.readline().decode("utf-8", errors="ignore").strip()
            return reply if reply else None
 
 
# Helper simple (utilisation rapide)
_default = ArduinoSerial()
 
 
def send_command(command: str, expect_reply: bool = False) -> Optional[str]:
    """
    Fonction utilitaire rapide.
    Exemple:
        send_command("ON")
        resp = send_command("PING", expect_reply=True)
    """
    return _default.send(command, expect_reply=expect_reply)