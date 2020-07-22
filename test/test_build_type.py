from clang_build.build_type import BuildType

def test_case_insensitivity():
    assert BuildType("default") == BuildType("Default")
