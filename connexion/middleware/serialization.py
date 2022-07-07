import pathlib
import typing as t

from connexion.middleware import AppMiddleware


class SerializationMiddleware(AppMiddleware):
    def add_api(
        self, specification: t.Union[pathlib.Path, str, dict], **kwargs
    ) -> None:
        pass
