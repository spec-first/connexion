import abc
import pathlib
import typing as t


class AppMiddleware(abc.ABC):
    """Middlewares that need the APIs to be registered on them should inherit from this base
    class"""

    @abc.abstractmethod
    def add_api(self, specification: t.Union[pathlib.Path, str, dict], **kwargs) -> None:
        pass
