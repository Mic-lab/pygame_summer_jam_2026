import platform
import sys
import subprocess
from pathlib import Path
from cx_Freeze import setup
from dataclasses import dataclass, field

def scrape_files(directory_path:str, excluded_extensions:set[str] = set(), excluded_files:set[str] = set(), excluded_directories:set[str] = set()):
    excluded_files = {Path(path) for path in excluded_files}
    excluded_directories = {Path(path) for path in excluded_directories}

    root_directory = Path(directory_path)

    def process_directory(directory:Path):
        relative_directory = directory.relative_to(root_directory)
        if relative_directory in excluded_directories:
            return [], False
        
        scraped_paths = []
        whole_scrape = True
        for path in directory.iterdir():
            relative_path = path.relative_to(root_directory)
            if path.is_dir():
                sub_directory_scraped_paths, sub_directoy_whole_scrape = process_directory(path)
                if sub_directoy_whole_scrape:
                    scraped_paths.append(relative_path)
                else:
                    scraped_paths.extend(sub_directory_scraped_paths)
                    whole_scrape = False
            elif path.is_file():
                if path.suffix.lower() in excluded_extensions:
                    whole_scrape = False
                    continue
                if path in excluded_files:
                    whole_scrape = False
                    continue
                scraped_paths.append(relative_path)
        if whole_scrape:
            return [directory], whole_scrape
        else:
            return scraped_paths, whole_scrape

    return process_directory(root_directory)[0]

@dataclass
class Scraper:
    directory_path:str
    excluded_extensions:set[str] = field(default_factory=set)
    excluded_files:set[str] = field(default_factory=set)
    excluded_directories:set[str] = field(default_factory=set)

    def run(self):
        return scrape_files(**self.__dict__)

def build(source_file_path:str, app_name:str, build_options:dict = {}, scraper:Scraper|None = None):
    os = "mac" if (_ := platform.system().lower()) == "darwin" else _

    if scraper != None:
        scraper.excluded_extensions.update({".py", ".pyc", ".pyo", ".pyd"})
        files = scraper.run()
        files = [(str(file), str(file)) for file in files]
        if "include_files" not in build_options:
            build_options["include_files"] = []
        build_options["include_files"].extend(files)

    setup_options = {}
    
    if os == "mac":
        sys.argv.append("bdist_mac")
        
        setup_options["bdist_mac"] = {
            "bundle_name": app_name
        }
        setup_options["build"] = {
            "build_base": "dist/" + os
        }

    else:
        sys.argv.append("build")
        build_options["build_exe"] = "dist/" + os

    setup_options["build_exe"] = build_options

    setup(
        name=app_name,
        options=setup_options,
        executables=[{"script":source_file_path, "base":"gui"}]
    )

build(
    "main.py", "game",
    scraper=Scraper(
        ".", 
        excluded_files={".gitignore", "TODO"},
        excluded_directories={".git", ".github"}
    )
)