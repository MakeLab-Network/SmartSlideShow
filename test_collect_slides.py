from config import collect_slides, SlidesCollection, FileSystemAccess
from typing import List, Dict, Tuple, Optional, Union
from dataclasses import dataclass
import datetime

@dataclass
class FileSim:
    name: str
    datetime: datetime.datetime
    subtree: List['FileSim'] | None = None

  
  