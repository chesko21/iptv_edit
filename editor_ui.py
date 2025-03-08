import os
import re
import sys
import requests
import chardet
from PySide6.QtWidgets import (
    QMainWindow, QPushButton, QFileDialog, QListWidget, QTextEdit,
    QLineEdit, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QMessageBox,
    QSplitter, QListWidgetItem, QProgressDialog, QMenuBar, QMenu,
    QGridLayout , QDialog
)
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QIcon, QPixmap, QAction
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor


def read_m3u(file_path):
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
    except IOError as e:
        QMessageBox.critical(None, "Error", f"Failed to read file:\n{e}")
        return ""

    encoding = chardet.detect(raw_data)["encoding"]
    if encoding is None or encoding.lower() not in ["utf-8", "ascii", "iso-8859-1"]:
        encoding = "utf-8"

    try:
        return raw_data.decode(encoding)
    except UnicodeDecodeError:
        QMessageBox.warning(None, "Warning", "Error decoding file. Some data may be lost.")
        return raw_data.decode(encoding, errors="ignore")


def save_m3u(file_path, content):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        QMessageBox.critical(None, "Error", f"Failed to save file:\n{e}")
        return False
    return True


def is_valid_url(url):
    regex = re.compile(
        r'^(?:http|ftp)s?://'  
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' 
        r'localhost|' 
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|' 
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)' 
        r'(?::\d+)?' 
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return re.match(regex, url) is not None


def parse_m3u_with_progress(content, progress_dialog):
    channels = []
    lines = content.splitlines()
    total_lines = len(lines)
    progress_dialog.setMaximum(total_lines)

    for i in range(total_lines):
        QCoreApplication.processEvents()  

        if progress_dialog.wasCanceled(): 
            QMessageBox.warning(None, "Canceled", "M3U parsing was canceled.")
            return channels

        progress_dialog.setValue(i + 1)

        if lines[i].startswith("#EXTINF"):
            extinf_match = re.match(r"#EXTINF:(-?\d+)", lines[i])
            extinf_value = extinf_match.group(1) if extinf_match else "-1"

            match = re.search(r'tvg-id="(.*?)".*?tvg-logo="(.*?)".*?group-title="(.*?)",(.*)', lines[i])
            if match:
                tvg_id, tvg_logo, group_title, channel_name = match.groups()
                url = None
                license_type, license_key, http_referrer = "", "", ""

                j = i + 1
                while j < total_lines and not lines[j].startswith("#EXTINF"):
                    if lines[j].startswith("#KODIPROP:inputstream.adaptive.license_type="):
                        license_type = lines[j].split("=")[-1].strip()
                    elif lines[j].startswith("#KODIPROP:inputstream.adaptive.license_key="):
                        license_key = lines[j].split("=")[-1].strip()
                    elif lines[j].startswith("#EXTVLCOPT:http-referrer="):
                        http_referrer = lines[j].split("=")[-1].strip()
                    elif not lines[j].startswith("#") and lines[j].strip():
                        url = lines[j].strip()
                    j += 1

                if url and is_valid_url(url):
                    channels.append({
                        "extinf": extinf_value.strip(),
                        "name": channel_name.strip(),
                        "tvg_id": tvg_id.strip(),
                        "tvg_logo": tvg_logo.strip(),
                        "group_title": group_title.strip(),
                        "url": url.strip(),
                        "license_type": license_type.strip(),
                        "license_key": license_key.strip(),
                        "http_referrer": http_referrer.strip()
                    })
                i = j - 1

    progress_dialog.setValue(total_lines)
    return channels


def update_m3u_info(channels):
    m3u_content = "#EXTM3U\n"
    for channel in channels:
        m3u_content += f'#EXTINF:{channel.get("extinf", "-1")} ' \
                       f'tvg-id="{channel.get("tvg_id", "")}" ' \
                       f'tvg-logo="{channel.get("tvg_logo", "")}" ' \
                       f'group-title="{channel.get("group_title", "")}",{channel["name"]}\n'
        if channel.get("license_type", ""):
            m3u_content += f'#KODIPROP:inputstream.adaptive.license_type={channel["license_type"]}\n'
        if channel.get("license_key", ""):
            m3u_content += f'#KODIPROP:inputstream.adaptive.license_key={channel["license_key"]}\n'
        if channel.get("http_referrer", ""):
            m3u_content += f'#EXTVLCOPT:http-referrer={channel["http_referrer"]}\n'
        m3u_content += f'{channel["url"]}\n'

    return m3u_content


class IPTVEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread_pool = ThreadPoolExecutor(max_workers=5)
        self.channels = []
        self.current_file = None

        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)
        self.setStyleSheet("background-color: #EAEAEA;")
        self.menu_bar.setStyleSheet("QMenuBar { background-color: #205781; color: white; }")

        file_menu = QMenu("File", self)
        self.menu_bar.addMenu(file_menu)

        # Build icon paths using os.path
        icon_path = lambda icon_name: os.path.join(os.path.dirname(__file__), "icons", icon_name)

        new_file_action = QAction(QIcon(icon_path("open_file.png")), "New M3U", self)
        new_file_action.triggered.connect(self.create_new_file)
        file_menu.addAction(new_file_action)

        open_action = QAction(QIcon(icon_path("folder-open.png")), "Open M3U", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction(QIcon(icon_path("save.png")), "Save", self) 
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction(QIcon(icon_path("save_as.png")), "Save As", self)  
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)

        exit_action = QAction(QIcon(icon_path("exit.png")), "Exit", self)  
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = QMenu("Edit", self)
        self.menu_bar.addMenu(edit_menu)

        update_channel_action = QAction(QIcon(icon_path("update.png")), "Update Channel", self)  
        update_channel_action.triggered.connect(self.update_channel)
        edit_menu.addAction(update_channel_action)

        delete_channel_action = QAction(QIcon(icon_path("delete.png")), "Delete Channel", self)  
        delete_channel_action.triggered.connect(self.delete_channel)
        edit_menu.addAction(delete_channel_action)

        about_action = QAction(QIcon(icon_path("about.png")), "About", self)
        about_action.triggered.connect(self.show_about)
        self.menu_bar.addAction(about_action)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Horizontal)

        self.channel_list = QListWidget()
        self.channel_list.setMinimumWidth(300)
        self.channel_list.setMaximumWidth(500) 
        self.channel_list.setStyleSheet("QListWidget { background: #EAEAEA; border: 1px solid #ccc; }")
        self.channel_list.itemClicked.connect(self.load_channel_data)
        splitter.addWidget(self.channel_list)

        input_widget = QWidget()
        input_layout = QGridLayout(input_widget)
        input_layout.setSpacing(10)

        self.extinf_value_input = QLineEdit()
        self.channel_name_input = QLineEdit()
        self.tvg_id_input = QLineEdit() 
        self.logo_url_input = QLineEdit()
        self.group_title_input = QLineEdit()
        self.license_type_input = QLineEdit()
        self.license_key_input = QLineEdit()
        self.http_referrer_input = QLineEdit()
        self.url_input = QTextEdit()
        self.url_input.setStyleSheet("""
            background: #205781;  
            color: white; 
        """)
        fields = [
            ("Extinf:", self.extinf_value_input),
            ("Channel Name:", self.channel_name_input),
            ("TVG ID:", self.tvg_id_input),
            ("Logo URL:", self.logo_url_input),
            ("Group Title:", self.group_title_input),
            ("License Type:", self.license_type_input),
            ("License Key:", self.license_key_input),
            ("HTTP Referrer:", self.http_referrer_input),
            ("Channel URL:", self.url_input),
        ]

        for row, (label, field) in enumerate(fields):
            input_layout.addWidget(QLabel(label), row, 0)
            input_layout.addWidget(field, row, 1)

        splitter.addWidget(input_widget)
        main_layout.addWidget(splitter)

        button_layout = QHBoxLayout()
        for btn_name, callback, icon_name in [
            ("Open M3U", self.open_file, "folder-open.png"),
            ("Load from URL", self.load_from_url, "load_from_url.png"),
            ("Save", self.save_file, "save.png"),
            ("Save As", self.save_file_as, "save_as.png"),
            ("Update Channel", self.update_channel, "update.png"),
            ("Add Channel", self.add_channel, "open_file.png"),
            ("Delete Channel", self.delete_channel, "delete.png")
        ]:
            button = QPushButton(btn_name)
            button.clicked.connect(callback)
            button.setIcon(QIcon(icon_path(icon_name))) 
            button.setStyleSheet("""
                QPushButton {
                    font-weight: bold; 
                    padding: 10px; 
                    margin-right: 5px;
                    background-color: #4D55CC; 
                    color: white; 
                    border: none; 
                    border-radius: 5px;
                }
                
                QPushButton:hover {
                    background-color: #45a049; 
                }
                
                QPushButton:pressed {
                    background-color: #205781; 
                }
            """)

            button_layout.addWidget(button)

        main_layout.addWidget(QLabel("🔗 Enter M3U URL:"))
        self.url_download_input = QLineEdit()
        main_layout.addWidget(self.url_download_input)
        main_layout.addLayout(button_layout)

        container = QWidget()
        container.setLayout(main_layout)
        container.setStyleSheet("background-color: #F8F5E9;")
        self.setCentralWidget(container)

    def create_new_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save New M3U File", "", "M3U Files (*.m3u)")

        if file_path:
            self.current_file = file_path  
            self.channels.clear() 
            self.channel_list.clear()  
            self.clear_input_fields() 

            QMessageBox.information(self, "New File", f"New M3U file created: {self.current_file}")

    def clear_input_fields(self):
        self.extinf_value_input.clear()
        self.channel_name_input.clear()
        self.tvg_id_input.clear() 
        self.logo_url_input.clear()
        self.group_title_input.clear()
        self.license_type_input.clear()
        self.license_key_input.clear()
        self.http_referrer_input.clear()
        self.url_input.clear()

    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About IPTV Editor")
        dialog.setFixedSize(300, 300)

        layout = QVBoxLayout()

        about_text = """<b>IPTV Editor v1.0</b><br>
                        A simple editor for M3U files ,  Created by Chesko.<br>
                        Free Software.<br><br>
                        Support this project by donating:<br>
                        <a href="https://saweria.co/Chesko">Visit: https://saweria.co/Chesko</a>"""

        about_label = QLabel()
        about_label.setTextFormat(Qt.TextFormat.RichText)
        about_label.setText(about_text)
        about_label.setOpenExternalLinks(True)  
        layout.addWidget(about_label)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.close)
        layout.addWidget(ok_button)

        dialog.setLayout(layout)
        dialog.exec()

    def open_file(self):
        if self.current_file: 
            response = QMessageBox.question(
                self,
                "Confirm",
                "You have an unsaved file. Are you sure you want to open a new file?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if response == QMessageBox.No:
                return  

        file_path, _ = QFileDialog.getOpenFileName(self, "Open M3U", "", "M3U Files (*.m3u)")
        if file_path:
            self.current_file = file_path
            try:
                progress_dialog = QProgressDialog("IPTV Editor - Parsing...", "Cancel", 0, 100, self)
                progress_dialog.setWindowModality(Qt.WindowModal)
                progress_dialog.show()
                
                content = read_m3u(file_path)  
                self.channels = parse_m3u_with_progress(content, progress_dialog)
                self.populate_channel_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file:\n{e}")
            finally:
                progress_dialog.close()

    def load_from_url(self):
        url = self.url_download_input.text().strip()
        if not url:
            return QMessageBox.warning(self, "Error", "Please enter a valid M3U URL.")

        progress_dialog = QProgressDialog("IPTV Editor - Downloading M3U...", "Cancel", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setValue(10)
        progress_dialog.show()

        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()

            progress_dialog.setValue(50)
            content = response.text

            if not content.strip():
                raise ValueError("Downloaded M3U file is empty.")

            progress_dialog.setValue(70)
            self.channels = parse_m3u_with_progress(content, progress_dialog)
            self.populate_channel_list()

            QMessageBox.information(self, "Success", "M3U loaded from URL!")

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error", f"Failed to download M3U:\n{e}")
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Invalid M3U file:\n{e}")
        finally:
            progress_dialog.setValue(100)
            progress_dialog.close()

    def save_file(self):
        if not self.current_file:
            return QMessageBox.warning(self, "Error", "No file opened.")

        try:
            save_m3u(self.current_file, update_m3u_info(self.channels))
            QMessageBox.information(self, "Success", "File saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")

    def save_file_as(self):
        if not self.channels:
            return QMessageBox.warning(self, "Error", "No channels to save.")

        file_path, _ = QFileDialog.getSaveFileName(self, "Save M3U", "", "M3U Files (*.m3u)")
        if file_path:
            try:
                save_m3u(file_path, update_m3u_info(self.channels))
                self.current_file = file_path
                QMessageBox.information(self, "Success", "File saved as!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")

    def populate_channel_list(self):

        self.channel_list.clear()
        for channel in self.channels:
            item = QListWidgetItem(channel["name"])
            self.channel_list.addItem(item)

            if channel.get("tvg_logo"):
                self.thread_pool.submit(self.load_logo, item, channel["tvg_logo"])

    def load_logo(self, item, url):

        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(BytesIO(response.content).read())
                icon = QIcon(pixmap)
                item.setIcon(icon)
        except requests.exceptions.RequestException:
            pass

    def load_channel_data(self, item):

        selected_channel = next((ch for ch in self.channels if ch["name"] == item.text()), None)
        if not selected_channel:
            return
        self.extinf_value_input.setText(selected_channel["extinf"])
        self.channel_name_input.setText(selected_channel["name"])
        self.tvg_id_input.setText(selected_channel.get("tvg_id", ""))  
        self.logo_url_input.setText(selected_channel.get("tvg_logo", ""))
        self.group_title_input.setText(selected_channel.get("group_title", ""))
        self.license_type_input.setText(selected_channel.get("license_type", ""))
        self.license_key_input.setText(selected_channel.get("license_key", ""))
        self.http_referrer_input.setText(selected_channel.get("http_referrer", ""))
        self.url_input.setText(selected_channel["url"])

    def update_channel(self):
        current_item = self.channel_list.currentItem()
        if not current_item:
            return QMessageBox.warning(self, "Error", "No channel selected.")

        for channel in self.channels:
            if channel["name"] == current_item.text():
                channel["extinf"] = self.extinf_value_input.text()
                channel["name"] = self.channel_name_input.text()
                channel["tvg_id"] = self.tvg_id_input.text()
                channel["tvg_logo"] = self.logo_url_input.text()
                channel["group_title"] = self.group_title_input.text()
                channel["license_type"] = self.license_type_input.text()
                channel["license_key"] = self.license_key_input.text()
                channel["http_referrer"] = self.http_referrer_input.text()
                channel["url"] = self.url_input.toPlainText()
                break

        QMessageBox.information(self, "Updated", "Channel updated!")

    def add_channel(self):
        extinf_value = self.extinf_value_input.text().strip()
        channel_name = self.channel_name_input.text().strip()
        tvg_id = self.tvg_id_input.text().strip()
        tvg_logo = self.logo_url_input.text().strip()
        group_title = self.group_title_input.text().strip()
        license_type = self.license_type_input.text().strip()
        license_key = self.license_key_input.text().strip()
        http_referrer = self.http_referrer_input.text().strip()
        url = self.url_input.toPlainText().strip()
        
        if not channel_name or not url:
            QMessageBox.warning(self, "Error", "Channel Name and URL cannot be empty!")
            return

        if not is_valid_url(url):
            QMessageBox.warning(self, "Error", "The provided URL is not valid!")
            return
        
        if any(channel["name"] == channel_name for channel in self.channels):
            QMessageBox.warning(self, "Error", f"A channel with the name '{channel_name}' already exists.")
            return

        new_channel = {
            "extinf": extinf_value,
            "name": channel_name,
            "tvg_id": tvg_id,
            "tvg_logo": tvg_logo,
            "group_title": group_title,
            "license_type": license_type,
            "license_key": license_key,
            "http_referrer": http_referrer,
            "url": url
        }

        self.channels.append(new_channel)
        item = QListWidgetItem(channel_name)
        self.channel_list.addItem(item)

        self.clear_input_fields()
        QMessageBox.information(self, "Success", "Channel added!")

    def delete_channel(self):
        current_item = self.channel_list.currentItem()
        if not current_item:
            return QMessageBox.warning(self, "Error", "No channel selected.")

        channel_name = current_item.text()
        response = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the channel '{channel_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if response == QMessageBox.Yes:
            self.channels = [channel for channel in self.channels if channel["name"] != channel_name]
            self.channel_list.takeItem(self.channel_list.row(current_item))
            self.clear_input_fields()
            QMessageBox.information(self, "Deleted", "Channel deleted successfully!")

    def closeEvent(self, event):
        """Handle the close event to ensure cleanup."""
        self.thread_pool.shutdown(wait=True)
        event.accept()


if __name__ == "__main__":
    app = QCoreApplication(sys.argv)
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
    window.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "icons", "maskable.png"))) 
    window.show()                  
    sys.exit(app.exec())