import os
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def hash_file(filepath):
    sha = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)
        return sha.hexdigest()
    except (FileNotFoundError, PermissionError):
        return None


def hash_directory(directory):
    sha = hashlib.sha256()
    for root, _, files in os.walk(directory):
        for file in sorted(files):  
            filepath = os.path.join(root, file)
            file_hash = hash_file(filepath)
            if file_hash:
                sha.update(file_hash.encode())
    return sha.hexdigest()


class HashEventHandler(FileSystemEventHandler):
    def __init__(self, directory):
        self.directory = os.path.abspath(directory)  
        print(f"Monitoring directory: {self.directory}")

    def on_any_event(self, event):
        dir_hash = hash_directory(self.directory)
        print(f"Updated directory hash for {self.directory}: {dir_hash}")


def start_watcher(path):
    path = os.path.abspath(path) 
    if not os.path.exists(path):
        raise ValueError(f"Path does not exist: {path}")

    event_handler = HashEventHandler(path)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while observer.is_alive():
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
    finally:
        observer.stop()
        observer.join()
