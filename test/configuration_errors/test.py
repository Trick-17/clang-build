import os, sys
import unittest
import subprocess
import shutil
import logging
import io
import stat
from pathlib import Path as _Path
from multiprocessing import freeze_support

from clang_build import clang_build
from clang_build.errors import CompileError
from clang_build.errors import LinkError
from clang_build.logging_tools import TqdmHandler as TqdmHandler

def on_rm_error( func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    os.chmod( path, stat.S_IWRITE )
    os.unlink( path )

def clang_build_try_except( args ):
    try:
        clang_build.build(clang_build.parse_args(args))
    except CompileError as compile_error:
        logger = logging.getLogger('clang_build')
        logger.error('Compilation was unsuccessful:')
        for target, errors in compile_error.error_dict.items():
            printout = f'Target [{target}] did not compile. Errors:\n'
            printout += ' '.join(errors)
            logger.error(printout)
    except LinkError as link_error:
        logger = logging.getLogger('clang_build')
        logger.error('Linking was unsuccessful:')
        for target, errors in link_error.error_dict.items():
            printout = f'Target [{target}] did not link. Errors:\n{errors}'
            logger.error(printout)

class TestClangBuild(unittest.TestCase):
    def test_circular_dependency(self):
        with self.assertRaisesRegex(RuntimeError, "(\[circular_project\.mylib1\] -> \[circular_project\.mylib2\] -> \[circular_project\.mylib1\])|(\[circular_project\.mylib2\] -> \[circular_project\.mylib1\] -> \[circular_project\.mylib2\])"):
            clang_build.build(clang_build.parse_args(['-d', 'test/configuration_errors/circular_dependency']))

    def test_missing_name_with_subproject(self):
        with self.assertRaisesRegex(RuntimeError, "defining a top-level project with subprojects but without a name is illegal"):
            clang_build.build(clang_build.parse_args(['-d', 'test/configuration_errors/missing_name_with_subproject']))

    def test_missing_subproject_toml(self):
        with self.assertRaisesRegex(RuntimeError, "It is not allowed to add a subproject that does not have a project file"):
            clang_build.build(clang_build.parse_args(['-d', 'test/configuration_errors/missing_subproject_toml']))

    def test_missing_subproject_name(self):
        with self.assertRaisesRegex(RuntimeError, "It is not allowed to add a subproject that does not have a name"):
            clang_build.build(clang_build.parse_args(['-d', 'test/configuration_errors/missing_subproject_name']))

    def setUp(self):
        logger = logging.getLogger('clang_build')
        logger.setLevel(logging.INFO)
        ch = TqdmHandler()
        formatter = logging.Formatter('%(message)s')
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.handlers = []
        logger.addHandler(ch)

    def tearDown(self):
        if _Path('build').exists():
            shutil.rmtree('build', onerror = on_rm_error)


if __name__ == '__main__':
    freeze_support()
    unittest.main()