import abc
import typing as t

from typing_extensions import Protocol


class Framework(Protocol):
    @staticmethod
    @abc.abstractmethod
    def is_framework_response(response: t.Any) -> bool:
        """Return True if provided response is a framework type"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def connexion_to_framework_response(cls, response):
        """Cast ConnexionResponse to framework response class"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def build_response(
        cls,
        data: t.Any,
        *,
        content_type: t.Optional[str] = None,
        headers: t.Optional[dict] = None,
        status_code: int = None
    ):
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def get_request(*args, **kwargs):
        """Return a framework request from the context."""
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def get_body(request):
        """Get body from a framework request"""
        raise NotImplementedError
