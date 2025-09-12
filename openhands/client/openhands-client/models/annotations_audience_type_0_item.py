from typing import Literal, cast

AnnotationsAudienceType0Item = Literal["assistant", "user"]

ANNOTATIONS_AUDIENCE_TYPE_0_ITEM_VALUES: set[AnnotationsAudienceType0Item] = {
    "assistant",
    "user",
}


def check_annotations_audience_type_0_item(value: str) -> AnnotationsAudienceType0Item:
    if value in ANNOTATIONS_AUDIENCE_TYPE_0_ITEM_VALUES:
        return cast(AnnotationsAudienceType0Item, value)
    raise TypeError(f"Unexpected value {value!r}. Expected one of {ANNOTATIONS_AUDIENCE_TYPE_0_ITEM_VALUES!r}")
