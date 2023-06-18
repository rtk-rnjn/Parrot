from __future__ import annotations

import os
import json

ROOT_DIR = "./extra/tutorials/roadmaps"
data: dict[str, list[str]] = {
    dir: []
    for dir in os.listdir(ROOT_DIR)
    if os.path.isdir(f"{ROOT_DIR}/{dir}")
}


def is_dir(path: str) -> bool:
    return os.path.isdir(path)

def is_file(path: str) -> bool:
    return os.path.isfile(path)

# for dir in data:
#     gen = os.walk(f"{ROOT_DIR}/{dir}")
#     for root, dirs, files in gen:
#         for file in files:
#             if file.endswith(".md"):
#                 data[dir].append(file)

# print(json.dumps(data, indent=4))