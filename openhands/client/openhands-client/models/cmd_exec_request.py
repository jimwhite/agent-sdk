from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.cmd_exec_request_env_type_0 import CmdExecRequestEnvType0


T = TypeVar("T", bound="CmdExecRequest")


@_attrs_define
class CmdExecRequest:
    """
    Attributes:
        command (list[str]): Executable and args; no shell.
        timeout (Union[Unset, int]):  Default: 30.
        cwd (Union[None, Unset, str]): Working directory under FS_ROOT.
        env (Union['CmdExecRequestEnvType0', None, Unset]):
        max_output_bytes (Union[Unset, int]):  Default: 1000000.
    """

    command: list[str]
    timeout: Union[Unset, int] = 30
    cwd: Union[None, Unset, str] = UNSET
    env: Union["CmdExecRequestEnvType0", None, Unset] = UNSET
    max_output_bytes: Union[Unset, int] = 1000000
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.cmd_exec_request_env_type_0 import CmdExecRequestEnvType0

        command = self.command

        timeout = self.timeout

        cwd: Union[None, Unset, str]
        if isinstance(self.cwd, Unset):
            cwd = UNSET
        else:
            cwd = self.cwd

        env: Union[None, Unset, dict[str, Any]]
        if isinstance(self.env, Unset):
            env = UNSET
        elif isinstance(self.env, CmdExecRequestEnvType0):
            env = self.env.to_dict()
        else:
            env = self.env

        max_output_bytes = self.max_output_bytes

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "command": command,
            }
        )
        if timeout is not UNSET:
            field_dict["timeout"] = timeout
        if cwd is not UNSET:
            field_dict["cwd"] = cwd
        if env is not UNSET:
            field_dict["env"] = env
        if max_output_bytes is not UNSET:
            field_dict["max_output_bytes"] = max_output_bytes

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.cmd_exec_request_env_type_0 import CmdExecRequestEnvType0

        d = dict(src_dict)
        command = cast(list[str], d.pop("command"))

        timeout = d.pop("timeout", UNSET)

        def _parse_cwd(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        cwd = _parse_cwd(d.pop("cwd", UNSET))

        def _parse_env(data: object) -> Union["CmdExecRequestEnvType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                env_type_0 = CmdExecRequestEnvType0.from_dict(data)

                return env_type_0
            except:  # noqa: E722
                pass
            return cast(Union["CmdExecRequestEnvType0", None, Unset], data)

        env = _parse_env(d.pop("env", UNSET))

        max_output_bytes = d.pop("max_output_bytes", UNSET)

        cmd_exec_request = cls(
            command=command,
            timeout=timeout,
            cwd=cwd,
            env=env,
            max_output_bytes=max_output_bytes,
        )

        cmd_exec_request.additional_properties = d
        return cmd_exec_request

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
