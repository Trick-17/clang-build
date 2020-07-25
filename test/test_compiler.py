from pathlib import Path
import subprocess

from clang_build.compiler import Clang


def test_finds_clang():
    compiler = Clang()

    for exe in [compiler.clang, compiler.clangpp, compiler.clang_ar]:
        subprocess.check_call([str(exe), "--version"])


def create_file(content, path):
    with open(path, 'w') as f:
        f.write(content)

def remove_file(path):
    path.unlink(missing_ok=True)

def remove_dir(path):
    path.rmdir()


def test_compile_empty_source():
    compiler = Clang()
    source_file = Path("empty.cpp")
    object_file = Path("output.o")
    try:
        create_file("", source_file)
        success, _ = compiler.compile(source_file, object_file)
        assert object_file.exists()
        assert success
    finally:
        remove_file(object_file)
        remove_file(source_file)

def test_compile_faulty_source():
    compiler = Clang()
    source_file = Path("faulty.cpp")
    object_file = Path("should_not_be_here.o")
    try:
        create_file("{", source_file)
        success, report = compiler.compile(source_file, object_file)
        assert not success
        assert str(source_file)+":1:1" in report
    finally:
        remove_file(object_file)
        remove_file(source_file)

def test_compile_with_flags():
    compiler = Clang()
    source_file = Path("needs_flags.cpp")
    object_file = Path("should_not_be_here.o")
    try:
        create_file("int main(){\n#ifdef HIFLAG\n}\n#endif", source_file)
        success, _ = compiler.compile(source_file, object_file)
        assert not success
        success, _ = compiler.compile(source_file, object_file, ["-DHIFLAG"])
        assert success
        assert object_file.exists()
    finally:
        remove_file(object_file)
        remove_file(source_file)

def test_compile_output_in_folder():
    compiler = Clang()
    source_file = Path("empty.cpp")
    object_file = Path("nested/folder/output.o")
    try:
        create_file("", source_file)
        success, _ = compiler.compile(source_file, object_file)
        assert success
        assert object_file.exists()
    finally:
        remove_file(object_file)
        remove_dir(object_file.parent)
        remove_dir(object_file.parent.parent)
        remove_file(source_file)


def test_link():
    assert False


def test_dependency_file():
    assert False