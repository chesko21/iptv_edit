import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class RestartOnChangeHandler(FileSystemEventHandler):
    def __init__(self, command):
        self.command = command
        self.process = None
        self.start_process()

    def start_process(self):
        if self.process:
            self.process.kill()
        self.process = subprocess.Popen(self.command, shell=True)

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            print(f"File changed: {event.src_path}, restarting...")
            self.start_process()


if __name__ == "__main__":
    path = "."  
    command = "python main.py"  

    event_handler = RestartOnChangeHandler(command)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)

    print("Watching for file changes... Press Ctrl+C to stop.")
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
       
        observer.stop()
    observer.join()