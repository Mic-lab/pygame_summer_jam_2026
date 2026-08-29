from pathlib import Path
import shutil

source = Path("data/imgs/animations/aseprite")
destination = Path("./data/imgs/animations")

def move():
    for file in source.iterdir():
        if file.is_file() and file.suffix.lower() in (".png", ".json"):
            shutil.move(file, destination / file.name)
