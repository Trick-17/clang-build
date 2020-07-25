from pathlib import Path

from clang_build.directories import Directories

# correct order of directories
#


class MockDependency:
    def __init__(self, directories):
        self.directories = directories


def test_correct_order():
    d = Directories(
        {"include_directories": [Path("a")], "include_directories_public": [Path("b")]},
        [
            MockDependency(
                Directories(
                    {
                        "include_directories": [Path("m/a")],
                        "include_directories_public": [Path("m/b")],
                    },
                    [],
                )
            )
        ],
    )

    assert d.include_public == [Path("b")]
    assert d.include_private == [Path("a")]
    assert d.include_public_total() == [Path("b"), Path("m/b")]
    assert d.include_command() == ["-I", "a", "-I", "b", "-I", str(Path("m/b"))]
    assert d.final_directories_list() == [Path("a"), Path("b"), Path("m/b")]

    d.make_private_directories_public()
    assert d.include_public == [Path("a"), Path("b")]
    assert d.include_private == []


def test_empty_dependency_list():
    d = Directories(
        {"include_directories": [Path("a")], "include_directories_public": [Path("b")]},
        [],
    )

    assert d.include_public == [Path("b")]
    assert d.include_private == [Path("a")]
    assert d.include_public_total() == [Path("b")]
    assert d.include_command() == ["-I", "a", "-I", "b"]
    assert d.final_directories_list() == [Path("a"), Path("b")]

    d.make_private_directories_public()
    assert d.include_public == [Path("a"), Path("b")]
    assert d.include_private == []
