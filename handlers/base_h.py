from abc import ABC, abstractmethod


class BaseHandler(ABC):
    @abstractmethod
    def parse(self, raw_data: dict) -> dict:
        """парсит сырые данные в нормализованный формат"""
        pass

    @abstractmethod
    def can_handle(self, raw_data: dict) -> bool:
        pass
