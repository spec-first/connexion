import typing as t

ReturnType = t.TypeVar("ReturnType")
MaybeAwaitable = t.Union[t.Awaitable[ReturnType], ReturnType]
