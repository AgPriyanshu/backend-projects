from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar, get_args, get_origin

from pydantic import BaseModel

PayloadT = TypeVar("PayloadT", bound=BaseModel)
OutputT = TypeVar("OutputT")


class Operation(ABC, Generic[PayloadT, OutputT]):
    payload_model: ClassVar[type[BaseModel]]
    name = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls is Operation:
            return

        origin_bases = getattr(cls, "__orig_bases__", ())

        for base in origin_bases:
            if get_origin(base) is Operation:
                payload_arg, output_arg = get_args(base)

                if isinstance(payload_arg, TypeVar) or isinstance(output_arg, TypeVar):
                    raise TypeError(
                        "Operation subclasses must specify concrete generic types."
                    )

                if not isinstance(payload_arg, type) or not issubclass(
                    payload_arg, BaseModel
                ):
                    raise TypeError(
                        "Operation subclasses must use a Pydantic BaseModel payload type."
                    )

                cls.payload_model = payload_arg

                return
        raise TypeError(
            "Operation subclasses must specify generic types like Operation[Payload, Output]."
        )

    def __init__(self, payload: PayloadT):
        self.payload = payload
        self.outputs = {}
        self.ctx = {}

    @abstractmethod
    def execute(self, *args, **kwargs) -> OutputT:
        pass
