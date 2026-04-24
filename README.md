# SENTINEL — Système de Surveillance IoT

Surveillance de chambre avec détection d'intrusion laser, caméra en direct, alertes et interface web — Arduino Uno + Raspberry Pi.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Composants

| Composant | Pin Arduino |
|---|---|
| Servomoteur (signal) | 6 |
| Laser KY-008 | 7 |
| Buzzer passif | 8 |
| LED RGB — Rouge | 9 |
| LED RGB — Vert | 10 |
| LED RGB — Bleu | 11 |
| LDR | A0 |

---

## Branchements essentiels

**LED RGB** — cathode commune vers GND, chaque broche couleur via résistance 220 Ω.

**LDR** — diviseur de tension : `5V → LDR → A0 → R 10kΩ → GND`.

**Servomoteur** — alimenter sur **alimentation externe 5V** (jamais sur le 5V Arduino), masse commune avec Arduino, condensateur 100–470 µF entre VCC et GND du servo, résistance 220 Ω sur le fil signal.

**Arduino → Raspberry Pi** — câble USB, port `/dev/ttyACM0`.

**Caméra** — nappe CSI du Raspberry Pi (côté bleu vers l'extérieur).

---

## Installation

**1 — Raspberry Pi**

```bash
sudo apt update && sudo apt upgrade -y
sudo raspi-config                      # Interface Options → Camera → Enable
sudo usermod -a -G dialout $USER       # accès port série, puis se reconnecter
pip install flask picamera2 opencv-python pyserial
```

**2 — Arduino (via arduino-cli, depuis le Raspberry Pi en SSH)**

```bash
# Installer arduino-cli
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
sudo mv bin/arduino-cli /usr/local/bin/

# Installer le core Arduino AVR
arduino-cli core update-index
arduino-cli core install arduino:avr

# Installer la bibliothèque Servo
arduino-cli lib install "Servo"

# Compiler le sketch (depuis le dossier parent)
arduino-cli compile --fqbn arduino:avr:uno sentinel_arduino

# Téléverser sur l'Arduino
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno sentinel_arduino
```

> Le dossier du sketch doit porter le même nom que le fichier `.ino` (ex: `sentinel_arduino/sentinel_arduino.ino`).

**3 — Lancer le serveur**

```bash
cd sentinel/
python app.py
```

Accès depuis le réseau : `http://<ip-du-raspberry>:5000`

```bash
hostname -I   # pour trouver l'IP
```

---

## Utilisation

- **PIN par défaut : `1234`** — modifiable dans `app.py` (`PIN_CODE = "1234"`)
- Le PIN est demandé à la connexion, et à chaque activation/désactivation du système
- En mode **automatique**, le servo balaye 0°→180° en continu
- En mode **manuel**, les boutons ◀ ▶ déplacent la caméra de 15° par appui
- Quand une intrusion est détectée, la LED et le buzzer sonnent **jusqu'à acquittement** depuis l'interface
- Le journal des intrusions est sauvegardé dans `data.json`

---

## Structure des fichiers

```
sentinel/
├── app.py
├── data.json               # généré automatiquement
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/app.js
```

---

## Dépannage rapide

| Problème | Solution |
|---|---|
| Servo instable / positions aléatoires | Alimentation externe 5V + condensateur 100µF |
| Port `/dev/ttyACM0` introuvable | `sudo usermod -a -G dialout $USER` puis reconnecter |
| Caméra ne démarre pas | Vérifier `raspi-config` et la nappe CSI |
| Interface inaccessible depuis le réseau | Vérifier que `host="0.0.0.0"` dans `app.py` |
| Trop de fausses alertes | Augmenter `threshold` dans le `.ino` (défaut : 25) |