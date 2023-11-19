import types
import typing as t

# Maybe Awaitable
_ReturnType = t.TypeVar("_ReturnType")
MaybeAwaitable = t.Union[t.Awaitable[_ReturnType], _ReturnType]

# WSGIApp
Environ = t.Mapping[str, object]

_WriteCallable = t.Callable[[bytes], t.Any]
_ExcInfo = t.Tuple[type, BaseException, types.TracebackType]

_StartResponseCallable = t.Callable[
    [
        str,  # status
        t.Sequence[t.Tuple[str, str]],  # response headers
    ],
    _WriteCallable,  # write() callable
]
_StartResponseCallableWithExcInfo = t.Callable[
    [
        str,  # status
        t.Sequence[t.Tuple[str, str]],  # response headers
        t.Optional[_ExcInfo],  # exc_info
    ],
    _WriteCallable,  # write() callable
]
StartResponse = t.Union[_StartResponseCallable, _StartResponseCallableWithExcInfo]
ResponseStream = t.Iterable[bytes]

WSGIApp = t.Callable[[Environ, StartResponse], ResponseStream]
