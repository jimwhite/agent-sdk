from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.tool_annotations import ToolAnnotations
    from ..models.tool_input_schema import ToolInputSchema
    from ..models.tool_meta_type_0 import ToolMetaType0
    from ..models.tool_output_schema_type_0 import ToolOutputSchemaType0


T = TypeVar("T", bound="Tool")


@_attrs_define
class Tool:
    """Tool that wraps an executor function with input/output validation and schema.

    - Normalize input/output schemas (class or dict) into both model+schema.
    - Validate inputs before execute.
    - Coerce outputs only if an output model is defined; else return vanilla JSON.
    - Export MCP tool description.

        Attributes:
            name (str):
            description (str):
            action_type (str):
            kind (str): Property to create kind field from class name when serializing.
            input_schema (ToolInputSchema):
            output_schema (Union['ToolOutputSchemaType0', None]):
            title (str):
            observation_type (Union[None, Unset, str]):
            annotations (Union['ToolAnnotations', None, Unset]):
            meta (Union['ToolMetaType0', None, Unset]):
    """

    name: str
    description: str
    action_type: str
    kind: str
    input_schema: "ToolInputSchema"
    output_schema: Union["ToolOutputSchemaType0", None]
    title: str
    observation_type: Union[None, Unset, str] = UNSET
    annotations: Union["ToolAnnotations", None, Unset] = UNSET
    meta: Union["ToolMetaType0", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.tool_annotations import ToolAnnotations
        from ..models.tool_meta_type_0 import ToolMetaType0
        from ..models.tool_output_schema_type_0 import ToolOutputSchemaType0

        name = self.name

        description = self.description

        action_type = self.action_type

        kind = self.kind

        input_schema = self.input_schema.to_dict()

        output_schema: Union[None, dict[str, Any]]
        if isinstance(self.output_schema, ToolOutputSchemaType0):
            output_schema = self.output_schema.to_dict()
        else:
            output_schema = self.output_schema

        title = self.title

        observation_type: Union[None, Unset, str]
        if isinstance(self.observation_type, Unset):
            observation_type = UNSET
        else:
            observation_type = self.observation_type

        annotations: Union[None, Unset, dict[str, Any]]
        if isinstance(self.annotations, Unset):
            annotations = UNSET
        elif isinstance(self.annotations, ToolAnnotations):
            annotations = self.annotations.to_dict()
        else:
            annotations = self.annotations

        meta: Union[None, Unset, dict[str, Any]]
        if isinstance(self.meta, Unset):
            meta = UNSET
        elif isinstance(self.meta, ToolMetaType0):
            meta = self.meta.to_dict()
        else:
            meta = self.meta

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "description": description,
                "action_type": action_type,
                "kind": kind,
                "input_schema": input_schema,
                "output_schema": output_schema,
                "title": title,
            }
        )
        if observation_type is not UNSET:
            field_dict["observation_type"] = observation_type
        if annotations is not UNSET:
            field_dict["annotations"] = annotations
        if meta is not UNSET:
            field_dict["meta"] = meta

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.tool_annotations import ToolAnnotations
        from ..models.tool_input_schema import ToolInputSchema
        from ..models.tool_meta_type_0 import ToolMetaType0
        from ..models.tool_output_schema_type_0 import ToolOutputSchemaType0

        d = dict(src_dict)
        name = d.pop("name")

        description = d.pop("description")

        action_type = d.pop("action_type")

        kind = d.pop("kind")

        input_schema = ToolInputSchema.from_dict(d.pop("input_schema"))

        def _parse_output_schema(data: object) -> Union["ToolOutputSchemaType0", None]:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                output_schema_type_0 = ToolOutputSchemaType0.from_dict(data)

                return output_schema_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ToolOutputSchemaType0", None], data)

        output_schema = _parse_output_schema(d.pop("output_schema"))

        title = d.pop("title")

        def _parse_observation_type(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        observation_type = _parse_observation_type(d.pop("observation_type", UNSET))

        def _parse_annotations(data: object) -> Union["ToolAnnotations", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                annotations_type_0 = ToolAnnotations.from_dict(data)

                return annotations_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ToolAnnotations", None, Unset], data)

        annotations = _parse_annotations(d.pop("annotations", UNSET))

        def _parse_meta(data: object) -> Union["ToolMetaType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                meta_type_0 = ToolMetaType0.from_dict(data)

                return meta_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ToolMetaType0", None, Unset], data)

        meta = _parse_meta(d.pop("meta", UNSET))

        tool = cls(
            name=name,
            description=description,
            action_type=action_type,
            kind=kind,
            input_schema=input_schema,
            output_schema=output_schema,
            title=title,
            observation_type=observation_type,
            annotations=annotations,
            meta=meta,
        )

        tool.additional_properties = d
        return tool

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
