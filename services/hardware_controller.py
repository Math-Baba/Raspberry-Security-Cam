# services/hardware_controller.py

def on_system_activated():
    """
    Appelé quand l'utilisateur active la surveillance.
    Ici tu peux:
    - allumer une LED (GPIO)
    - démarrer un service (systemctl)
    - envoyer une commande à un Arduino (serial)
    """
    pass

def on_system_deactivated():
    """
    Appelé quand l'utilisateur désactive la surveillance.
    """
    pass