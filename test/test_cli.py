import subprocess
from pathlib import Path
from shutil import rmtree

import pytest

from clang_build import clang_build as cli
from clang_build.build_type import BuildType


def cli_argument_check(
    argument, argument_short, default_value, custom_parameter, expected_outcome
):
    args_argument = argument.replace("-", "_")
    # default check
    args = cli.parse_args([])
    assert vars(args)[args_argument] == default_value

    # custom input
    args = cli.parse_args([f"--{argument}"] + custom_parameter)
    assert vars(args)[args_argument] == expected_outcome

    if argument_short:
        args = cli.parse_args([f"-{argument_short}"] + custom_parameter)
        assert vars(args)[args_argument] == expected_outcome


def test_cli_arguments():
    cli_argument_check("verbose", "V", False, [], True)
    cli_argument_check("progress", "p", False, [], True)
    cli_argument_check("directory", "d", Path(), ["my_folder"], Path("my_folder"))
    cli_argument_check("build-type", "b", BuildType.Default, ["dEbUg"], BuildType.Debug)
    cli_argument_check("all", "a", False, [], True)
    cli_argument_check(
        "targets", "t", None, ["target1", "target2"], ["target1", "target2"]
    )
    with pytest.raises(SystemExit):
        cli_argument_check("all", "a", False, ["--targets", "target1"], False)
    cli_argument_check("force-build", "f", False, [], True)
    cli_argument_check("jobs", "j", 1, ["12"], 12)
    with pytest.raises(SystemExit):
        cli_argument_check("jobs", "j", 1, ["0"], 0)
    cli_argument_check("debug", None, False, [], True)
    cli_argument_check("no-graph", None, False, [], True)
    cli_argument_check("bundle", None, False, [], True)
    cli_argument_check("redistributable", None, False, [], True)


def test_hello_world_mwe():
    try:
        cli.build(cli.parse_args(["-d", "test/mwe"]))
        output = (
            subprocess.check_output(["./build/default/bin/main"], stderr=subprocess.STDOUT)
            .decode("utf-8")
            .strip()
        )
        assert output == "Hello!"
    finally:
        rmtree("build", ignore_errors=True)