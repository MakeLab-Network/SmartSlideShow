from typing import List
from dataclasses import dataclass
from datetime import datetime, timedelta
from config import collect_slides, SlidesCollection, NormalSlide, FileSystemAccess, OvershadowSlideCollection


@dataclass
class FileSim:
    name: str
    is_dir: bool
    date_time: datetime
    subtree: List['FileSim'] | None = None


class TestFileSystemAccess(FileSystemAccess):
    root: FileSim
    current_date: datetime

    def __init__(self, root: FileSim, current_date: datetime):
        self.root = root
        self.current_date = current_date

    def list_dir(self, path: str) -> List[str]:
        node: FileSim = self._find_node(path)
        if node and node.is_dir:
            return [child.name for child in node.subtree]
        else:
            return []

    def is_dir(self, path: str) -> bool:
        node = self._find_node(path)
        return node.is_dir if node else False

    def get_file_suffix(self, path: str) -> str:
        return '.' + path.split('.')[-1] if '.' in path else ''

    def get_file_main_name(self, path: str) -> str:
        return path[0:path.rfind(".")] if '.' in path else path

    def get_file_modification_time(self, path: str) -> datetime:
        node = self._find_node(path)
        return node.date_time if node else None

    def join(self, path1: str, path2: str) -> str:
        # remove trailing slash from path1
        if path1 != '' and path1[-1] == '/':
            path1 = path1[:-1]
        # remove leading slash from path2
        if path2 != '' and path2[0] == '/':
            path2 = path2[1:]
        return path1 + '/' + path2

    def get_current_date(self) -> datetime.date:
        return self.current_date.date()

    def _find_node(self, path: str) -> FileSim:
        path_parts = path.split('/')
        # remove empty parts
        path_parts = [part for part in path_parts if part != '']
        root_parts = self.root.name.split('/')
        # remove empty parts
        root_parts = [part for part in root_parts if part != '']
        # Ignore the prefix of the root node
        for i in range(len(root_parts)):
            if path_parts[i] != root_parts[i]:
                return None
        node = self.root
        for part in path_parts[len(root_parts):]:
            for child in node.subtree:
                if child.name == part:
                    node = child
                    break
            else:
                return None
        return node


def search_normal_slides(slides: List[NormalSlide], file: str, duration: timedelta) -> List[NormalSlide]:
    # use list comprehension to find all slides with the same filename and duration
    return [slide for slide in slides if slide.file == file and slide.duration == duration]


def assert_single_normal_slide(slides: List[NormalSlide], file: str,
                               duration: timedelta) -> None:
    slides = search_normal_slides(slides, file, duration)
    assert len(slides) == 1


def search_overshadow_slides(slides: List[OvershadowSlideCollection], file: str, frequency: int) -> \
        List[OvershadowSlideCollection]:
    # use list comprehension to find all overshadow slides with the same filename and frequency
    return [slide for slide in slides if file in slide.files and slide.frequency == frequency]
    '''
    # for debugging intead of list comprehension
    # create an empty list to store the matching slides
    matching_slides = []
    # iterate over each slide in the input list
    for slide in slides:
        # check if the file name is present in the slide's files attribute and if the frequency matches the input frequency
        if file in slide.files and slide.frequency == frequency:
            # if both conditions are true, add the slide to the matching_slides list
            matching_slides.append(slide)
    # return the list of matching slides
    return matching_slides
    '''
def assert_single_overshadow_slide(slides: List[OvershadowSlideCollection], file: str,
                                   frequency: int, bundle_size: int) -> None:
    slides = search_overshadow_slides(slides, file, frequency)
    assert len(slides) == 1
    assert len(slides[0].files) == bundle_size


def search_expired_slides(slides: List[str], file: str) -> List[str]:
    # use list comprehension to find all expired slides with the same filename
    return [slide for slide in slides if slide == file]


def assert_single_expired_slide(slides: List[str], file: str) -> None:
    slides = search_expired_slides(slides, file)
    assert len(slides) == 1


def test_normal_slides1():
    # Prepare a TestFileSystemAccess
    date: datetime = datetime(2022, 1, 2, 13, 0)
    root = FileSim('/root/aaa/', True, date, [
        FileSim('dir1@wg1@dur5', True, date, [
            FileSim('slide1.jpg', False, date),
            FileSim('slide2.jpg', False, date)
        ]),
        FileSim('dir2@wg1_5@dur7', True, date, [
            FileSim('slide3.jpg', False, date),
            FileSim('slide4.jpg', False, date)
        ])
    ])
    fs_access = TestFileSystemAccess(root, datetime(2022, 1, 3))

    # Call the collect function
    slide_collection = SlidesCollection()
    collect_slides(slide_collection, '/root/aaa/', fs_access=fs_access)

    # Verify the result
    assert len(slide_collection.normal_slides) == 2
    assert len(slide_collection.normal_slides[1.0]) == 2
    assert len(slide_collection.normal_slides[1.5]) == 2
    assert_single_normal_slide(
        slide_collection.normal_slides[1.0], 'dir1@wg1@dur5/slide1.jpg', timedelta(seconds=5))
    assert_single_normal_slide(
        slide_collection.normal_slides[1.0], 'dir1@wg1@dur5/slide2.jpg', timedelta(seconds=5))
    assert_single_normal_slide(
        slide_collection.normal_slides[1.5], 'dir2@wg1_5@dur7/slide3.jpg', timedelta(seconds=7))
    assert_single_normal_slide(
        slide_collection.normal_slides[1.5], 'dir2@wg1_5@dur7/slide4.jpg', timedelta(seconds=7))


def test_expired_slides():
    # Prepare a TestFileSystemAccess
    current_date = datetime(2022, 1, 2)
    past: str = '@till1111'
    present: str = '@till' + current_date.strftime('%d%m%y')
    future: str = '@till' + \
        (current_date + timedelta(days=1)).strftime('%d%m%Y')

    root = FileSim('/root/aaa/', True, current_date, [
        FileSim('dir1@dur5' + past, True, current_date, [
            FileSim('slide1.jpg', False, current_date),
            FileSim('slide2.jpg', False, current_date),
            FileSim('slide3.jpg', False, current_date),
            FileSim('slide4.jpg', False, current_date)
        ]),
        FileSim('dir2@dur7' + present, True, current_date, [
            FileSim('slide1.jpg', False, current_date),
            FileSim('slide2.jpg', False, current_date)
        ]),
        FileSim('dir3@dur10' + future, True, current_date, [
            FileSim('slide1.jpg', False, current_date),
            FileSim('slide2.jpg', False, current_date)
        ])
    ])
    fs_access = TestFileSystemAccess(root, current_date)

    # Call the collect function
    slide_collection = SlidesCollection()
    collect_slides(slide_collection, '/root/aaa', fs_access=fs_access)

    # print(slide_collection.normal_slides)

    # Verify the result
    assert len(slide_collection.normal_slides) == 1
    assert len(slide_collection.normal_slides[1.0]) == 4
    assert len(slide_collection.expired_slides) == 4
    for i in range(1, 5):
        assert_single_expired_slide(
            slide_collection.expired_slides, 'dir1@dur5' + past + f'/slide{i}.jpg')
    for i in range(1, 3):
        assert_single_normal_slide(
            slide_collection.normal_slides[1.0], 'dir2@dur7' +
            present + f'/slide{i}.jpg',
            timedelta(seconds=7))
        assert_single_normal_slide(
            slide_collection.normal_slides[1.0], 'dir3@dur10' +
            future + f'/slide{i}.jpg',
            timedelta(seconds=10))


def test_overshadow_slides():
    date = datetime(2022, 1, 2)
    # Prepare a TestFileSystemAccess
    root = FileSim('/root/aaa/', True, date, [
        FileSim('dir1@all8_10_12', True, date, [
            FileSim('slide1.jpg', False, date),
            FileSim('slide2.jpg', False, date)
        ]),
        FileSim('dir2@all5_7', True, date, [
            FileSim('slide3.jpg', False, date),
            FileSim('slide4.jpg', False, date),
            FileSim('slide5.jpg', False, date)
        ]),
        FileSim('dir3@single6', True, date, [
            FileSim('slide6.jpg', False, date),
            FileSim('slide7.jpg', False, date)
        ])
    ])
    fs_access = TestFileSystemAccess(root, date)

    # Call the collect function
    slide_collection = SlidesCollection()
    collect_slides(slide_collection, '/root/aaa/', fs_access=fs_access)

    # Verify the result
    assert len(slide_collection.overshadow_slide_collections) == 7
    assert_single_overshadow_slide(
        slide_collection.overshadow_slide_collections, 'dir1@all8_10_12/slide1.jpg', 10, 1)
    assert_single_overshadow_slide(
        slide_collection.overshadow_slide_collections, 'dir1@all8_10_12/slide2.jpg', 10, 1)
    assert_single_overshadow_slide(
        slide_collection.overshadow_slide_collections, 'dir2@all5_7/slide3.jpg', 7, 1)
    assert_single_overshadow_slide(
        slide_collection.overshadow_slide_collections, 'dir2@all5_7/slide4.jpg', 7, 1)
    assert_single_overshadow_slide(
        slide_collection.overshadow_slide_collections, 'dir2@all5_7/slide5.jpg', 7, 1)
    assert_single_overshadow_slide(
        slide_collection.overshadow_slide_collections, 'dir3@single6/slide6.jpg', 6, 2)
    assert_single_overshadow_slide(
        slide_collection.overshadow_slide_collections, 'dir3@single6/slide7.jpg', 6, 2)


if __name__ == '__main__':
    test_normal_slides1()
    test_expired_slides()
    test_overshadow_slides()
