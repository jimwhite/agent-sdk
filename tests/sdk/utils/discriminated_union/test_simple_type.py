from openhands.sdk.utils.discriminated_union.simple_type import SimpleType


def test_roundtrip_serialization_of_int() -> None:
    """Test that the int type can be serialized and deserialized correctly."""
    simple_type = SimpleType.from_type(int)
    assert simple_type.to_type() is int


def test_roundtrip_serialization_of_str() -> None:
    """Test that the str type can be serialized and deserialized correctly."""
    simple_type = SimpleType.from_type(str)
    assert simple_type.to_type() is str


def test_roundtrip_serialization_of_float() -> None:
    """Test that the float type can be serialized and deserialized correctly."""
    simple_type = SimpleType.from_type(float)
    assert simple_type.to_type() is float


def test_roundtrip_serialization_of_bool() -> None:
    """Test that the bool type can be serialized and deserialized correctly."""
    simple_type = SimpleType.from_type(bool)
    assert simple_type.to_type() is bool


def test_roundtrip_serialization_of_none() -> None:
    """Test that the None type can be serialized and deserialized correctly."""
    simple_type = SimpleType.from_type(type(None))
    assert simple_type.to_type() is type(None)


def test_roundtrip_serialization_of_list() -> None:
    """Test that the list type can be serialized and deserialized correctly."""
    simple_type = SimpleType.from_type(list[int])
    assert simple_type.to_type() == list[int]


def test_roundtrip_serialization_of_dict() -> None:
    """Test that the dict type can be serialized and deserialized correctly."""
    simple_type = SimpleType.from_type(dict[str, float])
    assert simple_type.to_type() == dict[str, float]


def test_roundtrip_serialization_of_nested_types() -> None:
    """Test that nested types can be serialized and deserialized correctly."""
    simple_type = SimpleType.from_type(dict[str, list[int]])
    assert simple_type.to_type() == dict[str, list[int]]
