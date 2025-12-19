# main.py
import os
from gui.app_gui import StegoApp

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    weights_path = os.path.join(base_dir, "weights", "StegFormer-S_baseline.pt")  # rename to your .pt
    app = StegoApp(weights_path)
    app.mainloop()
