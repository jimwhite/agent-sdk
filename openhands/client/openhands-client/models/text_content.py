from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.annotations import Annotations
    from ..models.text_content_meta_type_0 import TextContentMetaType0


T = TypeVar("T", bound="TextContent")


@_attrs_define
class TextContent:
    """
    Attributes:
        text (str):
        cache_prompt (Union[Unset, bool]):  Default: False.
        type_ (Union[Literal['text'], Unset]):  Default: 'text'.
        annotations (Union['Annotations', None, Unset]):
        field_meta (Union['TextContentMetaType0', None, Unset]):
    """

    text: str
    cache_prompt: Union[Unset, bool] = False
    type_: Union[Literal["text"], Unset] = "text"
    annotations: Union["Annotations", None, Unset] = UNSET
    field_meta: Union["TextContentMetaType0", None, Unset] = UNSET

    def to_dict(self) -> dict[str, Any]:
        from ..models.annotations import Annotations
        from ..models.text_content_meta_type_0 import TextContentMetaType0

        text = self.text

        cache_prompt = self.cache_prompt

        type_ = self.type_

        annotations: Union[None, Unset, dict[str, Any]]
        if isinstance(self.annotations, Unset):
            annotations = UNSET
        elif isinstance(self.annotations, Annotations):
            annotations = self.annotations.to_dict()
        else:
            annotations = self.annotations

        field_meta: Union[None, Unset, dict[str, Any]]
        if isinstance(self.field_meta, Unset):
            field_meta = UNSET
        elif isinstance(self.field_meta, TextContentMetaType0):
            field_meta = self.field_meta.to_dict()
        else:
            field_meta = self.field_meta

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "text": text,
            }
        )
        if cache_prompt is not UNSET:
            field_dict["cache_prompt"] = cache_prompt
        if type_ is not UNSET:
            field_dict["type"] = type_
        if annotations is not UNSET:
            field_dict["annotations"] = annotations
        if field_meta is not UNSET:
            field_dict["_meta"] = field_meta

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.annotations import Annotations
        from ..models.text_content_meta_type_0 import TextContentMetaType0

        d = dict(src_dict)
        text = d.pop("text")

        cache_prompt = d.pop("cache_prompt", UNSET)

        type_ = cast(Union[Literal["text"], Unset], d.pop("type", UNSET))
        if type_ != "text" and not isinstance(type_, Unset):
            raise ValueError(f"type must match const 'text', got '{type_}'")

        def _parse_annotations(data: object) -> Union["Annotations", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                annotations_type_0 = Annotations.from_dict(data)

                return annotations_type_0
            except:  # noqa: E722
                pass
            return cast(Union["Annotations", None, Unset], data)

        annotations = _parse_annotations(d.pop("annotations", UNSET))

        def _parse_field_meta(data: object) -> Union["TextContentMetaType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                field_meta_type_0 = TextContentMetaType0.from_dict(data)

                return field_meta_type_0
            except:  # noqa: E722
                pass
            return cast(Union["TextContentMetaType0", None, Unset], data)

        field_meta = _parse_field_meta(d.pop("_meta", UNSET))

        text_content = cls(
            text=text,
            cache_prompt=cache_prompt,
            type_=type_,
            annotations=annotations,
            field_meta=field_meta,
        )

        return text_content
