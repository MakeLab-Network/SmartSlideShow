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

def test_normal_slides1():
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
    assert len(slide_collection.normalSlides) == 2
    assert len(slide_collection.normalSlides[1.0]) == 2
    assert len(slide_collection.normalSlides[1.5]) == 2
    assert slide_collection.normalSlides[1.0][0].file == 'dir1@wg1/slide1@dur5.jpg'
    assert slide_collection.normalSlides[1.0][0].duration == datetime.timedelta(seconds=5)
    assert slide_collection.normalSlides[1.0][1].file == 'dir1@wg1/slide2@dur7.jpg'
    assert slide_collection.normalSlides[1.0][1].duration == datetime.timedelta(seconds=7)
    assert slide_collection.normalSlides[1.5][0].file == 'dir2@wg1.5/slide3@dur5.jpg'
    assert slide_collection.normalSlides[1.5][0].duration == datetime.timedelta(seconds=5)
    assert slide_collection.normalSlides[1.5][1].file == 'dir2@wg1.5/slide4@dur7.jpg'
    assert slide_collection.normalSlides[1.5][1].duration == datetime.timedelta(seconds=7)

def test_expired_slides():
    # Prepare a TestFileSystemAccess
    current_time = datetime.now()
    root = FileSim('/root/aaa', True, [
        FileSim('dir1@till' + (current_time - datetime.timedelta(days=1)).strftime('%d%m%Y'), True, [
            FileSim('slide1.jpg', False, mod_time=current_time),
            FileSim('slide2.jpg', False, mod_time=current_time)
        ]),
        FileSim('dir2@till' + (current_time + datetime.timedelta(days=1)).strftime('%d%m%y'), True, [
            FileSim('slide3.jpg', False, mod_time=current_time),
            FileSim('slide4.jpg', False, mod_time=current_time)
        ]),
        FileSim('dir3@till' + (current_time + datetime.timedelta(days=1)).strftime('%d%m'), True, [
            FileSim('slide5.jpg', False, mod_time=current_time),
            FileSim('slide6.jpg', False, mod_time=current_time)
        ])
    ])
    fs_access = TestFileSystemAccess(root, current_time)

    # Call the collect function
    slide_collection = SlidesCollection()
    collect_slides(slide_collection, '/root/aaa', fs_access=fs_access)

    # Verify the result
    assert len(slide_collection.normalSlides) == 2
    assert len(slide_collection.expired_slides) == 1
    assert slide_collection.expired_slides[0] == 'dir1@till' + (current_time - datetime.timedelta(days=1)).strftime('%d%m%Y')
    assert len(slide_collection.normalSlides[1.0]) == 2
    assert len(slide_collection.normalSlides[1.5]) == 2
    assert slide_collection.normalSlides[1.0][0].file == 'dir2@till' + (current_time + datetime.timedelta(days=1)).strftime('%d%m%y') + '/slide3.jpg'
    assert slide_collection.normalSlides[1.0][0].duration == datetime.timedelta(seconds=5)
    assert slide_collection.normalSlides[1.0][1].file == 'dir2@till' + (current_time + datetime.timedelta(days=1)).strftime('%d%m%y') + '/slide4.jpg'
    assert slide_collection.normalSlides[1.0][1].duration == datetime.timedelta(seconds=7)
    assert slide_collection.normalSlides[1.5][0].file == 'dir3@till' + (current_time + datetime.timedelta(days=1)).strftime('%d%m') + '/slide5.jpg'
    assert slide_collection.normalSlides[1.5][0].duration == datetime.timedelta(seconds=5)
    assert slide_collection.normalSlides[1.5][1].file == 'dir3@till' + (current_time + datetime.timedelta(days=1)).strftime('%d%m') + '/slide6.jpg'
    assert slide_collection.normalSlides[1.5][1].duration == datetime.timedelta(seconds=7)

if __name__ == '__main__':
    test_normal_slides1()
    test_expired_slides()