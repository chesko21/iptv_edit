import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from editor_ui import IPTVEditor 

def resource_path(relative_path):
    """Get the absolute path to the resource, works for dev and for PyInstaller."""
    try:
      
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    app.setStyleSheet("""
    QTextEdit {
        background: #205781;
        color: black;
    }
    QTextEdit:focus {
        background: #2C3E50;
        color: black;
    }
    QLineEdit {
        background: #205781;
        color: black;
    }
    QLineEdit:focus {
        background: #2C3E50;
        color: black;
    }
    """)

    window = IPTVEditor()
    window.setWindowTitle("IPTV Editor")  
    window.resize(800, 600)
    window.setWindowIcon(QIcon(resource_path("icons/maskable.png")))  # Menerapkan resource_path di sini
    window.show()                  
    
    sys.exit(app.exec())