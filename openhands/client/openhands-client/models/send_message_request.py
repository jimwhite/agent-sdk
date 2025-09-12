from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.send_message_request_role import SendMessageRequestRole, check_send_message_request_role
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.image_content import ImageContent
    from ..models.text_content import TextContent


T = TypeVar("T", bound="SendMessageRequest")


@_attrs_define
class SendMessageRequest:
    """Payload to send a message to the agent.

    This is a simplified version of openhands.sdk.Message.

        Attributes:
            role (Union[Unset, SendMessageRequestRole]):  Default: 'user'.
            content (Union[Unset, list[Union['ImageContent', 'TextContent']]]):
            run (Union[Unset, bool]): If true, immediately run the agent after sending the message. Default: True.
    """

    role: Union[Unset, SendMessageRequestRole] = "user"
    content: Union[Unset, list[Union["ImageContent", "TextContent"]]] = UNSET
    run: Union[Unset, bool] = True
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.text_content import TextContent

        role: Union[Unset, str] = UNSET
        if not isinstance(self.role, Unset):
            role = self.role

        content: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.content, Unset):
            content = []
            for content_item_data in self.content:
                content_item: dict[str, Any]
                if isinstance(content_item_data, TextContent):
                    content_item = content_item_data.to_dict()
                else:
                    content_item = content_item_data.to_dict()

                content.append(content_item)

        run = self.run

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if role is not UNSET:
            field_dict["role"] = role
        if content is not UNSET:
            field_dict["content"] = content
        if run is not UNSET:
            field_dict["run"] = run

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.image_content import ImageContent
        from ..models.text_content import TextContent

        d = dict(src_dict)
        _role = d.pop("role", UNSET)
        role: Union[Unset, SendMessageRequestRole]
        if isinstance(_role, Unset):
            role = UNSET
        else:
            role = check_send_message_request_role(_role)

        content = []
        _content = d.pop("content", UNSET)
        for content_item_data in _content or []:

            def _parse_content_item(data: object) -> Union["ImageContent", "TextContent"]:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    content_item_type_0 = TextContent.from_dict(data)

                    return content_item_type_0
                except:  # noqa: E722
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                content_item_type_1 = ImageContent.from_dict(data)

                return content_item_type_1

            content_item = _parse_content_item(content_item_data)

            content.append(content_item)

        run = d.pop("run", UNSET)

        send_message_request = cls(
            role=role,
            content=content,
            run=run,
        )

        send_message_request.additional_properties = d
        return send_message_request

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
