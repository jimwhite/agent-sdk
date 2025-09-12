from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="CmdExecResponse")


@_attrs_define
class CmdExecResponse:
    """
    Attributes:
        stdout (str):
        stderr (str):
        return_code (int):
        timed_out (bool):
        duration_ms (int):
    """

    stdout: str
    stderr: str
    return_code: int
    timed_out: bool
    duration_ms: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        stdout = self.stdout

        stderr = self.stderr

        return_code = self.return_code

        timed_out = self.timed_out

        duration_ms = self.duration_ms

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code,
                "timed_out": timed_out,
                "duration_ms": duration_ms,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        stdout = d.pop("stdout")

        stderr = d.pop("stderr")

        return_code = d.pop("return_code")

        timed_out = d.pop("timed_out")

        duration_ms = d.pop("duration_ms")

        cmd_exec_response = cls(
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            timed_out=timed_out,
            duration_ms=duration_ms,
        )

        cmd_exec_response.additional_properties = d
        return cmd_exec_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
