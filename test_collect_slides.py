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

    def test_normal_slides1(self):
        # Prepare a TestFileSystemAccess
        root = FileSim('/root/aaa', True, [
            FileSim('dir1@wg1@dur5', True, [
                FileSim('slide1.jpg', False, mod_time=datetime.now()),
                FileSim('slide2.jpg', False, mod_time=datetime.now())
            ]),
            FileSim('dir2@wg1.5@dur7', True, [
                FileSim('slide3.jpg', False, mod_time=datetime.now()),
                FileSim('slide4.jpg', False, mod_time=datetime.now())
            ])
        ])
        fs_access = TestFileSystemAccess(root, datetime.now())

        # Call the collect function
        slide_collection = SlidesCollection()
        collect_slides(slide_collection, '/root/aaa', fs_access=fs_access)

        # Verify the result
        self.assertEqual(len(slide_collection.normalSlides), 2)
        self.assertEqual(len(slide_collection.normalSlides[1.0]), 2)
        self.assertEqual(len(slide_collection.normalSlides[1.5]), 2)
        self.assertEqual(slide_collection.normalSlides[1.0][0].file, 'dir1@wg1/slide1@dur5.jpg')
        self.assertEqual(slide_collection.normalSlides[1.0][0].duration, datetime.timedelta(seconds=5))
        self.assertEqual(slide_collection.normalSlides[1.0][1].file, 'dir1@wg1/slide2@dur7.jpg')
        self.assertEqual(slide_collection.normalSlides[1.0][1].duration, datetime.timedelta(seconds=7))
        self.assertEqual(slide_collection.normalSlides[1.5][0].file, 'dir2@wg1.5/slide3@dur5.jpg')
        self.assertEqual(slide_collection.normalSlides[1.5][0].duration, datetime.timedelta(seconds=5))
        self.assertEqual(slide_collection.normalSlides[1.5][1].file, 'dir2@wg1.5/slide4@dur7.jpg')
        self.assertEqual(slide_collection.normalSlides[1.5][1].duration, datetime.timedelta(seconds=7))
