from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.annotations_audience_type_0_item import (
    AnnotationsAudienceType0Item,
    check_annotations_audience_type_0_item,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="Annotations")


@_attrs_define
class Annotations:
    """
    Attributes:
        audience (Union[None, Unset, list[AnnotationsAudienceType0Item]]):
        priority (Union[None, Unset, float]):
    """

    audience: Union[None, Unset, list[AnnotationsAudienceType0Item]] = UNSET
    priority: Union[None, Unset, float] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        audience: Union[None, Unset, list[str]]
        if isinstance(self.audience, Unset):
            audience = UNSET
        elif isinstance(self.audience, list):
            audience = []
            for audience_type_0_item_data in self.audience:
                audience_type_0_item: str = audience_type_0_item_data
                audience.append(audience_type_0_item)

        else:
            audience = self.audience

        priority: Union[None, Unset, float]
        if isinstance(self.priority, Unset):
            priority = UNSET
        else:
            priority = self.priority

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if audience is not UNSET:
            field_dict["audience"] = audience
        if priority is not UNSET:
            field_dict["priority"] = priority

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_audience(data: object) -> Union[None, Unset, list[AnnotationsAudienceType0Item]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                audience_type_0 = []
                _audience_type_0 = data
                for audience_type_0_item_data in _audience_type_0:
                    audience_type_0_item = check_annotations_audience_type_0_item(audience_type_0_item_data)

                    audience_type_0.append(audience_type_0_item)

                return audience_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list[AnnotationsAudienceType0Item]], data)

        audience = _parse_audience(d.pop("audience", UNSET))

        def _parse_priority(data: object) -> Union[None, Unset, float]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, float], data)

        priority = _parse_priority(d.pop("priority", UNSET))

        annotations = cls(
            audience=audience,
            priority=priority,
        )

        annotations.additional_properties = d
        return annotations

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
