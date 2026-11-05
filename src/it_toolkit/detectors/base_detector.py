from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar("T")

class BaseDetector(ABC):

    @abstractmethod
    def detect(self) -> T:
        """
        Detect and return information about a system component.
        """
        raise NotImplementedError