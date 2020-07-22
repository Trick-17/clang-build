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
