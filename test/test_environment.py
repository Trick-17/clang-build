from pathlib import Path

from clang_build.environment import Environment
from clang_build.build_type import BuildType
from clang_build.compiler import Clang


def test_compiler():
    env = Environment({})
    assert isinstance(env.compiler, Clang)


def test_build_type():
    env = Environment({})
    assert env.build_type == BuildType.Default

    env = Environment({"build_type": BuildType.Release})
    assert env.build_type == BuildType.Release


def test_force_build():
    env = Environment({})
    assert env.force_build == False

    env = Environment({"force_build": True})
    assert env.force_build == True


def test_build_directory():
    env = Environment({})
    assert env.build_directory == Path("build")


def test_create_dependency_dotfile():
    env = Environment({})
    assert env.create_dependency_dotfile == True

    env = Environment({"no_graph": True})
    assert env.create_dependency_dotfile == False


def test_clone_recursive():
    env = Environment({})
    assert env.clone_recursive == True

    env = Environment({"no_recursive_clone": True})
    assert env.clone_recursive == False


def test_bundle():
    env = Environment({})
    assert env.bundle == False

    env = Environment({"bundle": True})
    assert env.bundle == True


def test_redistributable():
    env = Environment({})
    assert env.redistributable == False

    env = Environment({"redistributable": True})
    assert env.redistributable == True
