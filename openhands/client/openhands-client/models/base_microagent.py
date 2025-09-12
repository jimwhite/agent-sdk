from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.base_microagent_type import BaseMicroagentType, check_base_microagent_type
from ..types import UNSET, Unset

T = TypeVar("T", bound="BaseMicroagent")


@_attrs_define
class BaseMicroagent:
    """Base class for all microagents.

    Attributes:
        name (str):
        content (str):
        source (Union[None, Unset, str]): The source path or identifier of the microagent. When it is None, it is
            treated as a programmatically defined microagent.
        type_ (Union[Unset, BaseMicroagentType]):  Default: 'repo'.
    """

    name: str
    content: str
    source: Union[None, Unset, str] = UNSET
    type_: Union[Unset, BaseMicroagentType] = "repo"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        content = self.content

        source: Union[None, Unset, str]
        if isinstance(self.source, Unset):
            source = UNSET
        else:
            source = self.source

        type_: Union[Unset, str] = UNSET
        if not isinstance(self.type_, Unset):
            type_ = self.type_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "content": content,
            }
        )
        if source is not UNSET:
            field_dict["source"] = source
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        content = d.pop("content")

        def _parse_source(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        source = _parse_source(d.pop("source", UNSET))

        _type_ = d.pop("type", UNSET)
        type_: Union[Unset, BaseMicroagentType]
        if isinstance(_type_, Unset):
            type_ = UNSET
        else:
            type_ = check_base_microagent_type(_type_)

        base_microagent = cls(
            name=name,
            content=content,
            source=source,
            type_=type_,
        )

        base_microagent.additional_properties = d
        return base_microagent

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
