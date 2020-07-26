from clang_build.circle import Circle

def test_string_representation():
    c = Circle(["A", "B", "C"])

    assert str(c) == "A -> B -> C"
    assert repr(c) == f'{repr("A")} -> {repr("B")} -> {repr("C")}'
