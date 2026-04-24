import os
import sys


def get_runtime_base_paths():
    paths = []

    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        paths.append(meipass)

    executable_dir = os.path.dirname(os.path.abspath(getattr(sys, "executable", "")))
    if executable_dir:
        paths.append(executable_dir)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths.append(project_root)
    paths.append(os.getcwd())

    unique_paths = []
    for path in paths:
        normalized = os.path.normpath(path)
        if normalized and normalized not in unique_paths:
            unique_paths.append(normalized)
    return unique_paths


def get_data_path(*relative_parts):
    for base_path in get_runtime_base_paths():
        candidate = os.path.join(base_path, "data", *relative_parts)
        if os.path.exists(candidate):
            return candidate

    return os.path.join(get_runtime_base_paths()[0], "data", *relative_parts)

