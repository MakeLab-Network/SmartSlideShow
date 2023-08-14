# Importing necessary libraries
import os
import copy
import datetime
import enum
import dataclasses
# Importing dataclass for creating data classes
from dataclasses import dataclass
# Importing typing for type hinting
from typing import Self, List, Set
# Importing ABC and abstractmethod for creating abstract base classes and abstract methods
from abc import ABC, abstractmethod
# Importing OrderedDict for creating ordered dictionary
from collections import OrderedDict

# Abstract base class for file system access


class FileSystemAccess(ABC):
    # Abstract method to list directories
    @abstractmethod
    def list_dir(self, path: str) -> List[str]:
        pass

    @abstractmethod
    def is_dir(self, path: str) -> bool:
        pass

    @abstractmethod
    def get_file_suffix(self, path: str) -> str:
        pass

    @abstractmethod
    def get_file_main_name(self, path: str) -> str:
        pass

    @abstractmethod
    def get_file_modification_time(self, path: str) -> datetime.datetime:
        pass

    @abstractmethod
    def get_current_date(self) -> datetime.date:
        pass

    @abstractmethod
    def join(self, path1: str, path2: str) -> str:
        pass


# Class for normal file system access, inherits from FileSystemAccess
class NormalFileSystemAccess(FileSystemAccess):
    # Method to list directories
    def list_dir(self, path: str) -> List[str]:
        return os.listdir(path)

    def is_dir(self, path: str) -> bool:
        return os.path.isdir(path)

    def get_file_suffix(self, path: str) -> str:
        return os.path.splitext(path)[1]

    def get_file_main_name(self, path: str) -> str:
        return os.path.splitext(path)[0]

    def get_file_modification_time(self, path: str) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(os.path.getmtime(path))

    def get_current_date(self) -> datetime.date:
        return datetime.date.today()

    def join(self, path1: str, path2: str) -> str:
        return os.path.join(path1, path2)


image_suffixes: Set[str] = {".jpg", ".jpeg",
                            ".png", ".gif", ".bmp", ".tiff", ".tif"}


@dataclass
class OvershadowConfig:
    frequencies: List[int] = None
    one_at_a_time: bool = None


default_overshadow_config = OvershadowConfig([8], True)


@dataclass
class ChooseSlideConfig:
    weight: float = None


default_choose_slide_config: ChooseSlideConfig = ChooseSlideConfig(1.0)


@dataclass
class ShowConfig:
    expire_after_date: datetime.datetime | None = None
    duration: datetime.timedelta | None = None
    max_slides: int | None = None
    specialized_config: OvershadowConfig | ChooseSlideConfig | None = None

    def override(self, other: Self):
        if other.expire_after_date:
            self.expire_after_date = other.expire_after_date
        if other.duration:
            self.duration = other.duration
        if other.max_slides:
            self.max_slides = other.max_slides
        if other.specialized_config:
            self.specialized_config = other.specialized_config


default_show_config = ShowConfig(None, datetime.timedelta(
    seconds=5), None, default_choose_slide_config)


def fill_unspecified_show_config_with_defaults(show_config: ShowConfig) -> None:
    if not show_config.expire_after_date:
        show_config.expire_after_date = default_show_config.expire_after_date
    if not show_config.duration:
        show_config.duration = default_show_config.duration
    if not show_config.max_slides:
        show_config.max_slides = default_show_config.max_slides
    if not show_config.specialized_config:
        show_config.specialized_config = default_show_config.specialized_config
    # for each specialized config type, fill with defaults
    if isinstance(show_config.specialized_config, OvershadowConfig):
        if not show_config.specialized_config.frequencies:
            show_config.specialized_config.frequencies = default_overshadow_config.frequencies
        if not show_config.specialized_config.one_at_a_time:
            show_config.specialized_config.one_at_a_time = default_overshadow_config.one_at_a_time
    elif isinstance(show_config.specialized_config, ChooseSlideConfig):
        if not show_config.specialized_config.weight:
            show_config.specialized_config.weight = default_choose_slide_config.weight


def expire_date_from_file_date_and_string(file_date: datetime.datetime, expire_date_string: str) -> \
                                            datetime.datetime:
    if len(expire_date_string) == 8:
        return datetime.datetime.strptime(expire_date_string, "%d%m%Y")
    elif len(expire_date_string) == 6:
        return datetime.datetime.strptime(expire_date_string, "%d%m%y")
    elif len(expire_date_string) == 4:
        # try the year before, same, and year after
        for year in range(file_date.year-1, file_date.year+2):
            try:
                expire_after_date_attemp_string: str = f'{expire_date_string}{year}'
                expire_after_date: datetime.datetime = datetime.datetime.strptime(
                    expire_after_date_attemp_string, "%d%m%Y")
                if expire_after_date > file_date - datetime.timedelta(days=90) \
                        and expire_after_date < file_date + datetime.timedelta(days=365-91):
                    return expire_after_date
            except:
                pass
        raise ValueError("Could not find a valid date for " +
                         expire_date_string + " and file date " + file_date)
    else:
        raise ValueError("Invalid expire date string " + expire_date_string)


def cement_specialized_config(show_config: ShowConfig, is_overshadow_config: bool):
    # check if there is already a specialized config
    # mismatchError : str = "wg cannot be used together with freq/all/single"
    if is_overshadow_config:
        if show_config.specialized_config:
            # check if it is already a choose slide config
            if not isinstance(show_config.specialized_config, ChooseSlideConfig):
                raise ValueError("Incomplete configuration")
        else:
            show_config.specialized_config = OvershadowConfig()
    else:
        # check if it is already an overshadow config
        if show_config.specialized_config:
            if not isinstance(show_config.specialized_config, OvershadowConfig):
                raise ValueError(
                    "Cannot override a specialized config with a different type")
        else:
            show_config.specialized_config = ChooseSlideConfig()


def parse_file_name_for_config(filename: str, file_date: datetime.datetime) -> ShowConfig:
    # split on @
    config_strings: List[str] = filename.split("@")
    show_config: ShowConfig = ShowConfig()

    # ignore first string
    for configString in config_strings[1:]:
        configString: str = configString.lower()
        # check for expiration date
        if configString[0:4] == "till":
            show_config.expire_after_date: datetime.datetime = \
                expire_date_from_file_date_and_string(
                    file_date, configString[4:])
        if configString[0:3] == "dur":
            show_config.duration: datetime.timedelta = datetime.timedelta(
                seconds=int(configString[3:]))
        if configString[0:8] == "maxfiles":
            show_config.max_slides: int = int(configString[8:])

        if configString[0:2] == "wg":
            cement_specialized_config(show_config, False)
            # replace _ with . to get weight
            show_config.specialized_config.weight: float = float(
                configString[2:].replace("_", "."))

        # if configString[0:4] == "freq":
        #  cement_specialized_config(show_config, True)

        if configString[0:3] == "all":
            cement_specialized_config(show_config, True)
            show_config.specialized_config.one_at_a_time: bool = False
            freq_str: str = configString[3:]
            # split on "_" to get frequencies
            freqStrs: List[str] = freq_str.split("_")
            show_config.specialized_config.frequencies = [
                int(freq) for freq in freqStrs]
            # check if there is at least one frequency
            if len(show_config.specialized_config.frequencies) == 0:
                raise ValueError("At least one frequency must be provided")

        if configString[0:6] == "single":
            freq_str: str = configString[6:]
            cement_specialized_config(show_config, True)
            show_config.specialized_config.frequencies = [int(freq_str)]
            show_config.specialized_config.one_at_a_time: bool = True
    return show_config


@dataclass
class NormalSlide:
    file: str
    duration: datetime.timedelta


@dataclass
class OvershadowSlideCollection:
    files: List[str]
    frequency: int
    duration: datetime.timedelta


class Severity(enum.Enum):
    INFO = 0
    WARNING = 1
    ERROR = 2


@dataclass
class SlideMessage:
    severity: Severity
    file: str
    error: str


def remove_leading_slash(path: str) -> str:
    if path.startswith('/'):
        return path[1:]
    else:
        return path


@dataclass
class SlidesCollection:
    normal_slides: OrderedDict[float, List[NormalSlide]] = \
        dataclasses.field(default_factory=OrderedDict)
    overshadow_slide_collections: List[OvershadowSlideCollection] = \
        dataclasses.field(default_factory=list)
    messages: List[SlideMessage] = dataclasses.field(default_factory=list)
    expired_slides: List[str] = dataclasses.field(default_factory=list)

    def add_slide(self, file: str, show_config: ShowConfig) -> None:
        new_config: ShowConfig = copy.deepcopy(show_config)
        fill_unspecified_show_config_with_defaults(new_config)
        if isinstance(new_config.specialized_config, ChooseSlideConfig):
            if new_config.specialized_config.weight not in self.normal_slides:
                self.normal_slides[new_config.specialized_config.weight] = []
            self.normal_slides[new_config.specialized_config.weight]\
                .append(NormalSlide(remove_leading_slash(file), new_config.duration))
        else:
            overshadow_slide_collection: OvershadowSlideCollection = OvershadowSlideCollection(
                [file], 0, new_config.duration)
#      overshadow_slide_collection.frequency = min(len(self.overshadowSlides), len(new_config.specialized_config.frequencies) - 1)
#      overshadow_slide_collection.files.append(OvershadowSlideCollection(remove_leading_slash(file),
#                    new_config.specialized_config.frequencies[frequency], new_config.duration))
            self.overshadow_slide_collections.append(
                overshadow_slide_collection)

    def add_error(self, file: str, error: str) -> None:
        self.messages.append(SlideMessage(
            Severity.ERROR, remove_leading_slash(file), error))

    def add_warning(self, file: str, warning: str) -> None:
        self.messages.append(SlideMessage(
            Severity.ERROR, remove_leading_slash(file), warning))

    def add_expired_slide(self, file: str) -> None:
        self.expired_slides.append(remove_leading_slash(file))


def merge_overshadow_slide_collections(slide_collection: SlidesCollection,
                                       sub_slide_collection: SlidesCollection,
                                       config: ShowConfig) -> None:
    overshadow_slide_collections: List[OvershadowSlideCollection] = \
        sub_slide_collection.overshadow_slide_collections

    files: List[str] = []
    for overshadow_slide_collection in overshadow_slide_collections:
        files.extend(overshadow_slide_collection.files)
    frequency_idx: int = min(len(files), len(
        config.specialized_config.frequencies) - 1)
    new_config: ShowConfig = copy.deepcopy(config)
    frequency = new_config.specialized_config.frequencies[frequency_idx]
    new_config.specialized_config.frequencies = [frequency]

    # add all files as a single overshadow slide collection
    for file in files:
        slide_collection.add_slide(file, new_config)


def collect_slides(slide_collection: SlidesCollection, root_dir: str, relative_path: str = '',
                   show_config: ShowConfig = ShowConfig(), 
                   fs_access: FileSystemAccess = NormalFileSystemAccess()) -> int:
    slide_count = 0
    dir_path: str = fs_access.join(root_dir, relative_path)
    for name in fs_access.list_dir(dir_path):
        full_file_name: str = fs_access.join(dir_path, name)
        relative_file_name: str = fs_access.join(relative_path, name)

        new_config: ShowConfig = copy.deepcopy(show_config)
        new_config.override(parse_file_name_for_config(fs_access.get_file_main_name(name),
                                                   fs_access.get_file_modification_time(full_file_name)))
        if fs_access.is_dir(full_file_name):
            # If file is a directory, recurse into it, but if in all overshadow mode, put it in a
            # new slide collection
            if (new_config.specialized_config and isinstance(new_config.specialized_config, OvershadowConfig) and
                    not new_config.specialized_config.one_at_a_time):

                sub_slide_collection: SlidesCollection = SlidesCollection()
                slide_count += collect_slides(sub_slide_collection,
                                              root_dir, relative_file_name, new_config, fs_access)
                merge_overshadow_slide_collections(
                    slide_collection, sub_slide_collection, new_config)
            else:
                slide_count += collect_slides(slide_collection,
                                              root_dir, relative_file_name, new_config, fs_access)
        else:
            try:
                # extract file suffix
                suffix: str = fs_access.get_file_suffix(relative_file_name)
                if suffix not in image_suffixes:
                    slide_collection.add_warning(
                        relative_file_name, "File suffix " + suffix + " is not an image suffix")
                # Check if the expire_after_date of the show_config 
                # is greater than or equal to the current date
                if new_config.expire_after_date and new_config.expire_after_date.date() < \
                        fs_access.get_current_date():
                    slide_collection.add_expired_slide(relative_file_name)
                else:
                    slide_collection.add_slide(relative_file_name, show_config)
                    slide_count += 1
            except ValueError as e:
                slide_collection.add_error(relative_file_name, str(e))

    # check that slide count is not greater than max_slides
    if show_config.max_slides and slide_count > show_config.max_slides:
        slide_collection.add_error(relative_path,
                                   f"Slide count {slide_count} is greater than the maximum set")

    return slide_count
