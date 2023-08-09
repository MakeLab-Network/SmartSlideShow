from config import collect_slides, SlidesCollection, NormalSlide, FileSystemAccess, OvershadowSlideCollection
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class FileSim:
    name: str
    date_time: datetime
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
            if path_parts[i] != root_parts[i] and root_parts[i] != '':
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


def search_normal_slides(slides: List[NormalSlide], file: str, duration: timedelta) -> List[NormalSlide]:
    # use list comprehension to find all slides with the same filename and duration
    return [slide for slide in slides if slide.file == file and slide.duration == duration]


def search_single_normal_slide(slides: List[NormalSlide], file: str,
                               duration: timedelta) -> Optional[NormalSlide]:
    slides = search_normal_slides(slides, file, duration)
    assert len(slides) <= 1
    if len(slides) == 1:
        return slides[0]
    else:
        return None


def search_overshadow_slides(slides: List[OvershadowSlideCollection], file: str, frequency: int) -> List[OvershadowSlideCollection]:
    # use list comprehension to find all overshadow slides with the same filename and frequency
    return [slide for slide in slides if slide.file == file and slide.frequency == frequency]


def search_single_overshadow_slide(slides: List[OvershadowSlideCollection], file: str,
                                   frequency: int) -> Optional[OvershadowSlideCollection]:
    slides = search_overshadow_slides(slides, file, frequency)
    assert len(slides) <= 1
    if len(slides) == 1:
        return slides[0]
    else:
        return None


def search_expired_slides(slides: List[str], file: str) -> List[str]:
    # use list comprehension to find all expired slides with the same filename
    return [slide for slide in slides if slide == file]


def search_single_expired_slide(slides: List[str], file: str) -> Optional[str]:
    slides = search_expired_slides(slides, file)
    assert len(slides) <= 1
    if len(slides) == 1:
        return slides[0]
    else:
        return None


def test_normal_slides1():
    # Prepare a TestFileSystemAccess
    root = FileSim('/root/aaa/', True, [
        FileSim('dir1@wg1@dur5', True, [
            FileSim('slide1.jpg', False, mod_time=datetime(2022, 1, 3, 13, 0)),
            FileSim('slide2.jpg', False, mod_time=datetime(2022, 1, 3, 13, 0))
        ]),
        FileSim('dir2@wg1.5@dur7', True, [
            FileSim('slide3.jpg', False, mod_time=datetime(2022, 1, 3, 13, 0)),
            FileSim('slide4.jpg', False, mod_time=datetime(2022, 1, 3, 13, 0))
        ])
    ])
    fs_access = TestFileSystemAccess(root, datetime(2022, 1, 3, 13, 0))

    # Call the collect function
    slide_collection = SlidesCollection()
    collect_slides(slide_collection, '/root/aaa/', fs_access=fs_access)

    print(f"{slide_collection}\n")
    # Verify the result
    assert len(slide_collection.normalSlides) == 2
    assert len(slide_collection.normalSlides[1.0]) == 2
    assert len(slide_collection.normalSlides[1.5]) == 2
    slide1 = search_single_normal_slide(
        slide_collection.normalSlides[1.0], 'dir1@wg1/slide1@dur5.jpg', timedelta(seconds=5))
    assert slide1 is not None
    slide2 = search_single_normal_slide(
        slide_collection.normalSlides[1.0], 'dir1@wg1/slide2@dur7.jpg', timedelta(seconds=7))
    assert slide2 is not None
    slide3 = search_single_normal_slide(
        slide_collection.normalSlides[1.5], 'dir2@wg1.5/slide3@dur5.jpg', timedelta(seconds=5))
    assert slide3 is not None
    slide4 = search_single_normal_slide(
        slide_collection.normalSlides[1.5], 'dir2@wg1.5/slide4@dur7.jpg', timedelta(seconds=7))
    assert slide4 is not None


def test_expired_slides():
    # Prepare a TestFileSystemAccess
    current_time = datetime(2022, 1, 3, 13, 0)
    root = FileSim('/root/aaa/', True, [
        FileSim('dir1@till' + (current_time - timedelta(days=1)).strftime('%d%m%Y'), True, [
            FileSim('slide1.jpg', False, mod_time=current_time),
            FileSim('slide2.jpg', False, mod_time=current_time)
        ]),
        FileSim('dir2@till' + (current_time + timedelta(days=1)).strftime('%d%m%y'), True, [
            FileSim('slide3.jpg', False, mod_time=current_time),
            FileSim('slide4.jpg', False, mod_time=current_time)
        ]),
        FileSim('dir3@till' + (current_time + timedelta(days=1)).strftime('%d%m'), True, [
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
    expired_slide = search_single_expired_slide(slide_collection.expired_slides, 'dir1@till' + (
        current_time - timedelta(days=1)).strftime('%d%m%Y'))
    assert expired_slide is not None
    assert len(slide_collection.normalSlides[1.0]) == 2
    assert len(slide_collection.normalSlides[1.5]) == 2
    slide3 = search_single_normal_slide(slide_collection.normalSlides[1.0], 'dir2@till' + (
        current_time + timedelta(days=1)).strftime('%d%m%y') + '/slide3.jpg', timedelta(seconds=5))
    assert slide3 is not None
    slide4 = search_single_normal_slide(slide_collection.normalSlides[1.0], 'dir2@till' + (
        current_time + timedelta(days=1)).strftime('%d%m%y') + '/slide4.jpg', timedelta(seconds=7))
    assert slide4 is not None
    slide5 = search_single_normal_slide(slide_collection.normalSlides[1.5], 'dir3@till' + (
        current_time + timedelta(days=1)).strftime('%d%m') + '/slide5.jpg', timedelta(seconds=5))
    assert slide5 is not None
    slide6 = search_single_normal_slide(slide_collection.normalSlides[1.5], 'dir3@till' + (
        current_time + timedelta(days=1)).strftime('%d%m') + '/slide6.jpg', timedelta(seconds=7))
    assert slide6 is not None


if __name__ == '__main__':
    test_normal_slides1()
    test_expired_slides()
