from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ToolAnnotations")


@_attrs_define
class ToolAnnotations:
    """Annotations to provide hints about the tool's behavior.

    Based on Model Context Protocol (MCP) spec:
    https://github.com/modelcontextprotocol/modelcontextprotocol/blob/caf3424488b10b4a7b1f8cb634244a450a1f4400/schema/20
    25-06-18/schema.ts#L838

        Attributes:
            title (Union[None, Unset, str]): A human-readable title for the tool.
            read_only_hint (Union[Unset, bool]): If true, the tool does not modify its environment. Default: false Default:
                False.
            destructive_hint (Union[Unset, bool]): If true, the tool may perform destructive updates to its environment. If
                false, the tool performs only additive updates. (This property is meaningful only when `readOnlyHint == false`)
                Default: true Default: True.
            idempotent_hint (Union[Unset, bool]): If true, calling the tool repeatedly with the same arguments will have no
                additional effect on the its environment. (This property is meaningful only when `readOnlyHint == false`)
                Default: false Default: False.
            open_world_hint (Union[Unset, bool]): If true, this tool may interact with an 'open world' of external entities.
                If false, the tool's domain of interaction is closed. For example, the world of a web search tool is open,
                whereas that of a memory tool is not. Default: true Default: True.
    """

    title: Union[None, Unset, str] = UNSET
    read_only_hint: Union[Unset, bool] = False
    destructive_hint: Union[Unset, bool] = True
    idempotent_hint: Union[Unset, bool] = False
    open_world_hint: Union[Unset, bool] = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        title: Union[None, Unset, str]
        if isinstance(self.title, Unset):
            title = UNSET
        else:
            title = self.title

        read_only_hint = self.read_only_hint

        destructive_hint = self.destructive_hint

        idempotent_hint = self.idempotent_hint

        open_world_hint = self.open_world_hint

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if title is not UNSET:
            field_dict["title"] = title
        if read_only_hint is not UNSET:
            field_dict["readOnlyHint"] = read_only_hint
        if destructive_hint is not UNSET:
            field_dict["destructiveHint"] = destructive_hint
        if idempotent_hint is not UNSET:
            field_dict["idempotentHint"] = idempotent_hint
        if open_world_hint is not UNSET:
            field_dict["openWorldHint"] = open_world_hint

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_title(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        title = _parse_title(d.pop("title", UNSET))

        read_only_hint = d.pop("readOnlyHint", UNSET)

        destructive_hint = d.pop("destructiveHint", UNSET)

        idempotent_hint = d.pop("idempotentHint", UNSET)

        open_world_hint = d.pop("openWorldHint", UNSET)

        tool_annotations = cls(
            title=title,
            read_only_hint=read_only_hint,
            destructive_hint=destructive_hint,
            idempotent_hint=idempotent_hint,
            open_world_hint=open_world_hint,
        )

        tool_annotations.additional_properties = d
        return tool_annotations

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
