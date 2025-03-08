from email.mime import application
import os
import sys
import requests
from PySide6.QtGui import QPixmap ,  QIcon
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from editor_ui import IPTVEditor
from utils import read_m3u, save_m3u, parse_m3u_with_progress, update_m3u_info


class IPTVEditorLogic:
    def __init__(self) -> None:
        self.thread_pool = ThreadPoolExecutor(max_workers=5)
        self.channels = []
        self.current_file = None

    def open_file(self, file_path: str) -> tuple[bool, str]:
        if not file_path:
            return False, "Please provide a valid file path."

        self.current_file = file_path
        try:
            content = read_m3u(file_path)
            self.channels = parse_m3u_with_progress(content)
            return True, "File opened successfully!"
        except Exception as e:
            return False, f"Failed to open file: {str(e)}"

    def load_from_url(self, url: str) -> tuple[bool, str]:
        if not url:
            return False, "Please enter a valid M3U URL."

        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            content = response.text.strip()

            if not content:
                raise ValueError("Downloaded M3U file is empty.")

            self.channels = parse_m3u_with_progress(content)
            return True, "M3U loaded from URL!"
        except requests.exceptions.RequestException as e:
            return False, f"Failed to download M3U: {str(e)}"
        except ValueError as e:
            return False, f"Invalid M3U file: {str(e)}"

    def save_file(self) -> tuple[bool, str]:
        if not self.current_file:
            return False, "No file opened."

        try:
            m3u_content = update_m3u_info(self.channels)
            save_m3u(self.current_file, m3u_content)
            return True, "File saved!"
        except Exception as e:
            return False, f"Failed to save file: {str(e)}"

    def save_file_as(self, file_path: str) -> tuple[bool, str]:
        if not self.channels:
            return False, "No channels to save."

        if file_path:
            try:
                m3u_content = update_m3u_info(self.channels)
                save_m3u(file_path, m3u_content)
                self.current_file = file_path
                return True, "File saved as!"
            except Exception as e:
                return False, f"Failed to save file: {str(e)}"

    def load_logo(self, item, url: str) -> QPixmap | None:
        if not url:
            return None
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                return pixmap
        except requests.exceptions.RequestException:
            return None

    def update_channel(self, channel_name: str, new_data: dict) -> tuple[bool, str]:
 
        for channel in self.channels:
            if channel["name"] == channel_name:
                channel.update(new_data)
                return True, "Channel updated!"
        return False, "Channel not found."
    

    if __name__ == "__main__":
        app = application(sys.argv)
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
        window.setWindowIcon(QIcon("icons/maskable.png")) 
        window.show()                  
        sys.exit(app.exec())
