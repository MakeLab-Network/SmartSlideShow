import os, sys, copy, random, time, datetime, abc, typing, enum, dataclasses
#from PIL import Image
#from kivy import App, Widget, ScreenManager, Builder
from dataclasses import dataclass
from typing import Self, List, Set, Optional
from abc import ABC, abstractmethod
from collections import OrderedDict

class FileSystemAccess(ABC):
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
    

class NormalFileSystemAccess(FileSystemAccess):
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


image_suffixes : Set[str] = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif"}

@dataclass
class OvershadowConfig:
  frequencies : List[int] = None
  oneAtATime : bool = None

defaultOvershadowConfig = OvershadowConfig([8], True)

@dataclass
class ChooseSlideConfig:
  weight : float = None
  
defaultChooseSlideConfig: ChooseSlideConfig = ChooseSlideConfig(1.0)

@dataclass
class ShowConfig:
  expireDate : datetime.datetime | None = None
  duration : datetime.timedelta | None = None
  maxSlides : int | None = None
  specializedConfig : OvershadowConfig | ChooseSlideConfig | None = None
  def override(self, other: Self):
    if other.expireDate:
      self.expireDate = other.expireDate
    if other.duration:
      self.duration = other.duration
    if other.maxSlides:
      self.maxSlides = other.maxSlides
    if other.specializedConfig:
      self.specializedConfig = other.specializedConfig
      
defaultShowConfig = ShowConfig(None, datetime.timedelta(seconds=5), None, defaultChooseSlideConfig)

def fillUnspecifiedShowConfigWithDefaults(showConfig: ShowConfig) -> None :
  if not showConfig.expireDate:
    showConfig.expireDate = defaultShowConfig.expireDate
  if not showConfig.duration:
    showConfig.duration = defaultShowConfig.duration
  if not showConfig.maxSlides:
    showConfig.maxSlides = defaultShowConfig.maxSlides
  if not showConfig.specializedConfig:
    showConfig.specializedConfig = defaultShowConfig.specializedConfig
  #for each specialized config type, fill with defaults
  if isinstance(showConfig.specializedConfig, OvershadowConfig):
    if not showConfig.specializedConfig.frequencies:
      showConfig.specializedConfig.frequencies = defaultOvershadowConfig.frequencies
    if not showConfig.specializedConfig.oneAtATime:
      showConfig.specializedConfig.oneAtATime = defaultOvershadowConfig.oneAtATime
  elif isinstance(showConfig.specializedConfig, ChooseSlideConfig):
    if not showConfig.specializedConfig.weight:
      showConfig.specializedConfig.weight = defaultChooseSlideConfig.weight
      
def expireDateFromFileDateAndString(fileDate: datetime.datetime, expireDateString: str) -> datetime.datetime:
      if len(expireDateString) == 8:
        return datetime.datetime.strptime(expireDateString, "%d%m%Y")
      elif len(expireDateString) == 6:
        return datetime.datetime.strptime(expireDateString, "%d%m%y")
      elif len(expireDateString) == 4:
        # try the year before, same, and year after
        for year in range(fileDate.year-1, fileDate.year+2):
          try:
            expireDateAttempString : str = f'{expireDateString}{year}'
            expireDate : datetime.datetime = datetime.datetime.strptime(expireDateAttempString, "%d%m%Y") 
            if expireDate > fileDate - datetime.timedelta(days=90) \
              and expireDate < fileDate + datetime.timedelta(days=365-91):
              return expireDate;
          except:
            pass
        raise ValueError("Could not find a valid date for " + expireDateString + " and file date " + fileDate)
      else:
        raise ValueError("Invalid expire date string " + expireDateString)


def cementSpecializedConfig(showConfig: ShowConfig, isOvershadowConfig : bool):
  # check if there is already a specialized config
  # mismatchError : str = "wg cannot be used together with freq/all/single"
  if isOvershadowConfig:
    if showConfig.specializedConfig:
      # check if it is already a choose slide config
      if not isinstance(showConfig.specializedConfig, ChooseSlideConfig):
        raise ValueError("Incomplete configuration")
    else:
      showConfig.specializedConfig = OvershadowConfig()
  else:
      # check if it is already an overshadow config
    if showConfig.specializedConfig:
      if not isinstance(showConfig.specializedConfig, OvershadowConfig):
        raise ValueError("Cannot override a specialized config with a different type")
    else:
      showConfig.specializedConfig = ChooseSlideConfig()

  
def parseFileNameForConfig(fileName: str, fileDate: datetime.datetime) -> ShowConfig:
  # split on @
  configStrings : List[str] = fileName.split("@")
  showConfig : ShowConfig = ShowConfig()

  # ignore first string
  for configString in configStrings[1:]:
    configString : str = configString.lower()
    #check for expiration date
    if configString[0:4] == "till":
      showConfig.expireDate : datetime.datetime = expireDateFromFileDateAndString(fileDate, configString[4:])
    if configString[0:3] == "dur":
      showConfig.duration : datetime.timedelta = datetime.timedelta(seconds=int(configString[3:]))
    if configString[0:8] == "maxfiles":
      showConfig.maxSlides : int = int(configString[8:])
  
    if configString[0:2] == "wg":
      cementSpecializedConfig(showConfig, False)
      # replace _ with . to get weight
      showConfig.specializedConfig.weight : float = float(configString[2:].replace("_", "."))
      
    #if configString[0:4] == "freq":
    #  cementSpecializedConfig(showConfig, True)
    
    if configString[0:3] == "all":
      cementSpecializedConfig(showConfig, True)
      showConfig.specializedConfig.oneAtATime : bool = False
      freqStr : str = configString[3:]
      # split on "_" to get frequencies
      freqStrs : List[str] = freqStr.split("_")
      showConfig.specializedConfig.frequencies = [int(freq) for freq in freqStrs]
      # check if there is at least one frequency
      if len(showConfig.specializedConfig.frequencies) == 0:
        raise ValueError("At least one frequency must be provided")
      
    if configString[0:6] == "single":
      freqStr : str = configString[6:]
      cementSpecializedConfig(showConfig, True)
      showConfig.specializedConfig.frequencies = [int(freqStr)]
      showConfig.specializedConfig.oneAtATime : bool = True
  return showConfig

@dataclass
class NormalSlide:
  file: str
  weight: float
  duration: datetime.timedelta

@dataclass
class OvershadowSlideCollection:
  files: List[str]
  frequency: int
  duration: datetime.timedelta
  
class severity(enum.Enum):
  INFO = 0
  WARNING = 1
  ERROR = 2
  
@dataclass
class SlideMessage:
  severity: severity
  file: str
  error: str
  
def remove_leading_slash(path: str) -> str:
  if path.startswith('/'):
    return path[1:]
  else:
    return path

@dataclass
class SlidesCollection:
  normalSlides: OrderedDict[float, List[NormalSlide]] = \
    dataclasses.field(default_factory=OrderedDict)
  overshadowSlidesCollections: List[OvershadowSlideCollection] = \
    dataclasses.field(default_factory=list)
  messages: List[SlideMessage] = dataclasses.field(default_factory=list)
  expired_slides: List[str] = dataclasses.field(default_factory=list)
  def addSlide(self, file: str, show_config: ShowConfig) -> None:
    new_config : ShowConfig = copy.deepcopy(show_config)
    fillUnspecifiedShowConfigWithDefaults(new_config)
    if isinstance(new_config.specializedConfig, ChooseSlideConfig):
      if new_config.specializedConfig.weight not in self.normalSlides:
        self.normalSlides[new_config.specializedConfig.weight] = []
      self.normalSlides[new_config.specializedConfig.weight]\
        .append(NormalSlide(remove_leading_slash(file), new_config.duration))
    else:
      overshadowSlideCollection : OvershadowSlideCollection = OvershadowSlideCollection([file], 0, new_config.duration)
#      overshadowSlideCollection.frequency = min(len(self.overshadowSlides), len(new_config.specializedConfig.frequencies) - 1)
#      overshadowSlideCollection.files.append(OvershadowSlideCollection(remove_leading_slash(file), 
#                    new_config.specializedConfig.frequencies[frequency], new_config.duration))
      self.overshadowSlidesCollectoins
  
  def addError(self, file: str, error: str) -> None:
    self.messages.append(SlideMessage(severity.ERROR, remove_leading_slash(file), error))
  
  def addWarning(self, file: str, warning: str) -> None:
    self.messages.append(SlideMessage(severity.ERROR, remove_leading_slash(file), warning))
  
  def addExpiredSlide(self, file: str) -> None:
    self.expired_slides.append(remove_leading_slash(file))

def merge_overshadow_slide_collections(slide_collection: SlidesCollection,
                                       sub_slide_collection: SlidesCollection,
                                       config: ShowConfig) -> None:
  overshadow_slide_collections : List[OvershadowSlideCollection] = sub_slide_collection.overshadowSlidesCollections
  assert len(overshadow_slide_collections) == 1
  files : List[str] = overshadow_slide_collections[0].files
  frequency_idx: int = min(len(files), len(config.specializedConfig.frequencies) - 1)
  new_config: ShowConfig = copy.deepcopy(config)
  frequency = new_config.specializedConfig.frequencies[frequency_idx]
  new_config.specializedConfig.frequencies = [frequency]

  # add all files as a single overshadow slide collection
  for file in sub_slide_collection.files:
      slide_collection.addSlide(file, new_config)


def collect_slides(slide_collection: SlidesCollection, root_dir: str, relative_path: str = '', 
                   show_config: ShowConfig = ShowConfig(), fs_access: FileSystemAccess = NormalFileSystemAccess()) -> int:
  slide_count = 0
  dir_path: str = fs_access.join(root_dir, relative_path)
  for name in fs_access.list_dir(dir_path):
      full_file_name: str = fs_access.join(dir_path, name)
      relative_file_name: str = fs_access.join(relative_path, name)

      new_config : ShowConfig = copy.deepcopy(show_config)            
      new_config.override(parseFileNameForConfig(fs_access.get_file_main_name(name),
                                          fs_access.get_file_modification_time(full_file_name)))
      if fs_access.is_dir(full_file_name):
          # If file is a directory, recurse into it, but if in all overshadow mode, put it in a
          # new slide collection
          if (new_config.specializedConfig and isinstance(new_config.specializedConfig, OvershadowConfig) and
               not new_config.specializedConfig.oneAtATime):

            sub_slide_collection : SlidesCollection = SlidesCollection()
            slide_count += collect_slides(sub_slide_collection, root_dir, relative_file_name, new_config, fs_access)
            merge_overshadow_slide_collections(slide_collection, sub_slide_collection, new_config)
          else:
            slide_count += collect_slides(slide_collection, root_dir, relative_file_name, new_config, fs_access)
      else:
          try:
            #extract file suffix
            suffix : str = fs_access.get_file_suffix(relative_file_name)
            if suffix not in image_suffixes:
              slide_collection.addWarning(relative_file_name, "File suffix " + suffix + " is not an image suffix")
            # Check if the expireDate of the show_config is greater than or equal to the current date
            if new_config.expireDate and new_config.expireDate.date() < fs_access.get_current_date():
              slide_collection.addExpiredSlide(relative_file_name)
            else:
              slide_collection.addSlide(relative_file_name, show_config)
              slide_count += 1
          except ValueError as e:
            slide_collection.addError(relative_file_name, str(e))
  
  #check that slide count is not greater than maxSlides
  if show_config.maxSlides and slide_count > show_config.maxSlides:
    slide_collection.addError(relative_path,
                              "Slide count " + str(slide_count) + " is greater than the maximum set")

  return slide_count
