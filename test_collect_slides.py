from config import collect_slides, SlidesCollection, FileSystemAccess
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
import datetime
from typing import List
from datetime import datetime
from config import FileSystemAccess

@dataclass
class FileSim:
    name: str
    datetime: datetime.datetime
    subtree: List['FileSim'] | None = None


class FileSim:
    def __init__(self, name: str, is_dir: bool, children=None, mod_time: datetime = datetime.now()):
        self.name = name
        self.is_dir = is_dir
        self.children = children if children else []
        self.mod_time = mod_time

class TestFileSystemAccess(FileSystemAccess):
    def __init__(self, root: FileSim, current_time: datetime):
        self.root = root
        self.current_time = current_time

    def list_dir(self, path: str) -> List[str]:
        node = self._find_node(path)
        if node and node.is_dir:
            return [child.name for child in node.children]
        else:
            return []

    def is_dir(self, path: str) -> bool:
        node = self._find_node(path)
        return node.is_dir if node else False

    def get_file_suffix(self, path: str) -> str:
        return '.' + path.split('.')[-1] if '.' in path else ''

    def get_file_modification_time(self, path: str) -> datetime:
        node = self._find_node(path)
        return node.mod_time if node else None

    def get_current_date(self) -> datetime.date:
        return self.current_time.date()

    def _find_node(self, path: str) -> FileSim:
        path_parts = path.split('/')
        root_parts = self.root.name.split('/')
        # Ignore the prefix of the root node
        for i in range(len(root_parts)):
            if path_parts[i] != root_parts[i]:
                return None
        node = self.root
        for part in path_parts[len(root_parts):]:
            for child in node.children:
                if child.name == part:
                    node = child
                    break
            else:
                return None
        return node
