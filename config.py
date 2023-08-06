import os, sys, copy, random, time, datetime, abc, typing, enum, dataclasses
#from PIL import Image
from kivy import App, Widget, ScreenManager, Builder
from dataclasses import dataclass
from typing import Self, List, Set


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

def fillUnspecifiedShowConfigWithDefaults(showConfig: ShowConfig):
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
class NormalSlideCollection:
  file: str
  weight: float
  duration: datetime.timedelta

@dataclass
class OvershadowSlideCollection:
  files: List[str]
  frequency: int
  duration: datetime.timedelta
  
@dataclass
class SlideError:
  file: str
  error: str
from collections import OrderedDict

@dataclass
class NormalSlideCollection:
  file: str
  duration: datetime.timedelta

@dataclass
class SlidesCollection:
  normalSlides: OrderedDict[float, List[NormalSlideCollection]]
  overshadowSlides: List[OvershadowSlideCollection] = []
  errors: List[SlideError] = []
  expired_slides: List[str] = []
  def addSlide(self, file: str, show_config: ShowConfig) -> None:
    new_config : ShowConfig = show_config.deep_copy()
    new_config.fillUnspecifiedShowConfigWithDefaults()
    if isinstance(new_config.specializedConfig, ChooseSlideConfig):
      if new_config.specializedConfig.weight not in self.normalSlides:
        self.normalSlides[new_config.specializedConfig.weight] = []
      self.normalSlides[new_config.specializedConfig.weight].\
        .append(NormalSlideCollection(file, new_config.duration))
    else:
      self.overshadowSlides.append(OvershadowSlideCollection(file, 
                    new_config.specializedConfig.frequency, new_config.duration))
  
  def addError(self, file: str, error: str) -> None:
    self.errors.append(SlideError(file, error))
  
  def addExpiredSlide(self, file: str) -> None:
    self.expired_slides.append(file)

def collect_slides(slide_collection: SlidesCollection, root_dir: str, relative_path: str = '', 
                   show_config: ShowConfig = ShowConfig()) -> int:
  slide_count = 0
  for name in os.listdir(root_dir):
      path: str = os.path.join(root_dir, name)
      relative_path_name: str = os.path.join(relative_path, name)

      if os.path.isdir(path):
          # If path is a directory, recurse into it
          slide_count += collect_slides(slide_collection, path, relative_path_name, show_config.deep_copy())
      else:
          new_config : ShowConfig = show_config.deep_copy()            
          try:
            #extract file suffix
            suffix : str = os.path.splitext(path)[1]
            if suffix not in image_suffixes:
              raise ValueError("File suffix " + suffix + " is not an image suffix")
            new_config.override(parseFileNameForConfig(path,
                                                datetime.datetime.fromtimestamp(os.path.getmtime(path))))
            # Check if the expireDate of the show_config is greater than or equal to the current date
            if new_config.expireDate and new_config.expireDate.date() >= datetime.date.today():
              slide_collection.addSlide(relative_path_name, new_config)
              slide_count += 1
            else:
              slide_collection.addExpiredSlide(relative_path_name)
          except ValueError as e:
            slide_collection.addError(relative_path_name, str(e))
  return slide_count

      
      
    
    
  
    
  
  
  
