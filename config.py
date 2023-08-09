import os, sys, copy, random, time, datetime, abc, typing, enum, dataclasses
#from PIL import Image
#from kivy import App, Widget, ScreenManager, Builder
from dataclasses import dataclass
from typing import Self, List, Set, Optional
from abc import ABC, abstractmethod

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
    def get_file_modification_time(self, path: str) -> datetime.datetime:
        pass

    @abstractmethod
    def get_current_date(self) -> datetime.date:
        pass

class NormalFileSystemAccess(FileSystemAccess):
    def list_dir(self, path: str) -> List[str]:
        return os.listdir(path)

    def is_dir(self, path: str) -> bool:
        return os.path.isdir(path)

    def get_file_suffix(self, path: str) -> str:
        return os.path.splitext(path)[1]

    def get_file_modification_time(self, path: str) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(os.path.getmtime(path))

    def get_current_date(self) -> datetime.date:
        return datetime.date.today()


image_suffixes : Set[str] = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif"}

@dataclass
class OvershadowConfig:
  frequency : int = None
  frequencyDecrement : int = None
  oneAtATime : bool = None

defaultOvershadowConfig = OvershadowConfig(8, 3, True)

@dataclass
class ChooseSlideConfig:
  weight : float = None
  
defaultChooseSlideConfig = ChooseSlideConfig(1.0)

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
    if not showConfig.specializedConfig.frequency:
      showConfig.specializedConfig.frequency = defaultOvershadowConfig.frequency
    if not showConfig.specializedConfig.frequencyDecrement:
      showConfig.specializedConfig.frequencyDecrement = defaultOvershadowConfig.frequencyDecrement
    if not showConfig.specializedConfig.oneAtATime:
      showConfig.specializedConfig.oneAtATime = defaultOvershadowConfig.oneAtATime
  elif isinstance(showConfig.specializedConfig, ChooseSlideConfig):
    if not showConfig.specializedConfig.weight:
      showConfig.specializedConfig.weight = defaultChooseSlideConfig.weight
      
def expireDateFromFileDateAndString(fileDate: datetime.datetime, expireDateString: str) -> datetime.datetime:
      if expireDateString.length == 8:
        return datetime.datetime.strptime("%d%m%Y")
      elif expireDateString.length == 6:
        return datetime.datetime.strptime("%d%m%y")
      elif expireDateString.length == 4:
        # try the year before, same, and year after
        expireDate : datetime.datetime.strptime("%d%m" + "2000") # Y2K has Februrary 29th
        for year in range(fileDate.year-1, fileDate.year+2):
          try:
            expireDate.year = year
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
  mismatchError : str = "wg cannot be used together with freq/all/single"
  if showConfig.specializedConfig:
    if isOvershadowConfig:
      # check if it is already a choose slide config
      if not isinstance(showConfig.specializedConfig, ChooseSlideConfig):
        raise ValueError("Incomplete configuration")
      else:
        showConfig.specializedConfig = OvershadowConfig()
    else:
      # check if it is already an overshadow config
      if not isinstance(showConfig.specializedConfig, OvershadowConfig):
        raise ValueError("Cannot override a specialized config with a different type")
      else:
        showConfig.specializedConfig = ChooseSlideConfig()

  
def parseFileNameForConfig(fileName: str, fileDate: datetime.datetime) -> ShowConfig:
  # remove extension
  fileName : str = fileName.split(".")[0]
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
      showConfig.specializedConfig.weight : float = float(configString[2:])
      
    if configString[0:4] == "freq":
      cementSpecializedConfig(showConfig, True)
      freqStr : str = configString[4:]
      # split on "_" to get frequency and decrement
      freqStrs : List[str] = freqStr.split("_")
      showConfig.specializedConfig.frequency : int = int(freqStrs[0])
      # check if there is a decrement
      if len(freqStrs) > 1:
        showConfig.specializedConfig.frequencyDecrement : int = int(freqStrs[1])
    
    if configString[0:3] == "all":
      cementSpecializedConfig(showConfig, True)
      showConfig.specializedConfig.oneAtATime : bool = False
      
    if configString[0:6] == "single":
      cementSpecializedConfig(showConfig, True)
      showConfig.specializedConfig.oneAtATime : bool = True

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
  
from collections import OrderedDict

@dataclass
class NormalSlide:
  file: str
  duration: datetime.timedelta

@dataclass
class SlidesCollection:
  normalSlides: OrderedDict[float, List[NormalSlide]] = \
    dataclasses.field(default_factory=OrderedDict)
  overshadowSlides: List[OvershadowSlideCollection] = \
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
        .append(NormalSlide(file, new_config.duration))
    else:
      self.overshadowSlides.append(OvershadowSlideCollection(file, 
                    new_config.specializedConfig.frequency, new_config.duration))
  
  def addError(self, file: str, error: str) -> None:
    self.messages.append(SlideMessage(severity.ERROR, file, error))
  
  def addWarning(self, file: str, warning: str) -> None:
    self.messages.append(SlideMessage(severity.ERROR, file, warning))
  
  def addExpiredSlide(self, file: str) -> None:
    self.expired_slides.append(file)

def collect_slides(slide_collection: SlidesCollection, root_dir: str, relative_path: str = '', 
                   show_config: ShowConfig = ShowConfig(), fs_access: FileSystemAccess = NormalFileSystemAccess()) -> int:
  slide_count = 0
  for name in fs_access.list_dir(root_dir):
      path: str = os.path.join(root_dir, name)
      relative_path_name: str = os.path.join(relative_path, name)

      if fs_access.is_dir(path):
          # If path is a directory, recurse into it
          new_config : ShowConfig = show_config.deep_copy()            
          try:
            #extract file suffix
            suffix : str = fs_access.get_file_suffix(path)
            if suffix not in image_suffixes:
              slide_collection.addWarning(path, "File suffix " + suffix + " is not an image suffix")
            new_config.override(parseFileNameForConfig(path,
                                                fs_access.get_file_modification_time(path)))
            # Check if the expireDate of the show_config is greater than or equal to the current date
            if new_config.expireDate and new_config.expireDate.date() >= fs_access.get_current_date():
              slide_count += collect_slides(slide_collection, path, relative_path_name, new_config, fs_access)
            else:
              slide_collection.addExpiredSlide(relative_path_name)
          except ValueError as e:
            slide_collection.addError(relative_path_name, str(e))
      else:
          slide_collection.addSlide(relative_path_name, show_config)
          slide_count += 1
  
  #check that slide count is not greater than maxSlides
  if show_config.maxSlides and slide_count > show_config.maxSlides:
    slide_collection.addError(relative_path,
                              "Slide count " + str(slide_count) + " is greater than the maximum set")

  return slide_count
        
      
    
    
  
    
  
  
  
