import abc
import pathlib
import typing as t


class AppMiddleware(abc.ABC):

    @abc.abstractmethod
    def add_api(self, specification: t.Union[pathlib.Path, str, dict], **kwargs) -> None:
        pass
