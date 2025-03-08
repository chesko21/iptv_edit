from email.mime import application
import os
import re
import sys
import chardet
from PySide6.QtWidgets import QProgressDialog, QMessageBox, QFileDialog
from PySide6.QtCore import QCoreApplication

from editor_ui import IPTVEditor


def read_m3u(file_path, progress_dialog=None):
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
            if progress_dialog:  
                progress_dialog.setValue(50)  
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
            if extinf_match:
                extinf_value = extinf_match.group(1)
            else:
                extinf_value = "-1" 

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

    return 


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
    window.show()                  
    sys.exit(app.exec())          