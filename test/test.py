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
from clang_build.logging_stream_handler import TqdmHandler as TqdmHandler

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
    def test_hello_world_mwe(self):
        clang_build_try_except(['-d', 'test/mwe'])

        try:
            output = subprocess.check_output(['./build/default/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertEqual(output, 'Hello!')

    def test_build_types(self):
        for build_type in ['release', 'relwithdebinfo', 'debug', 'coverage']:
            clang_build_try_except(['-d', 'test/mwe', '-b', build_type])

            try:
                output = subprocess.check_output([f'./build/{build_type}/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
            except subprocess.CalledProcessError as e:
                self.fail(f'Could not run compiled program with build type "{build_type}". Message:\n{e.output}')

            self.assertEqual(output, 'Hello!')

    def test_compile_error(self):
        with self.assertRaises(CompileError):
            clang_build.build(clang_build.parse_args(['-d', 'test/mwe_build_error', '-V']))

    def test_script_call(self):
        try:
            subprocess.check_output(['clang-build', '-d', 'test/mwe', '-V'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.fail('Compilation failed')
        try:
            output = subprocess.check_output(['./build/default/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertEqual(output, 'Hello!')

    def test_hello_world_rebuild(self):
        clang_build_try_except(['-d', 'test/mwe', '-V'])

        try:
            output = subprocess.check_output(['./build/default/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')
        self.assertEqual(output, 'Hello!')

        ### TODO: the following does not seem to work under coverage runs...
        # logger = logging.getLogger('clang_build')

        # stream_capture = io.StringIO()
        # ch = logging.StreamHandler(stream_capture)
        # ch.setLevel(logging.DEBUG)
        # logger.addHandler(ch)
        # clang_build_try_except(['-d', 'test/mwe', '-V'])
        # logger.removeHandler(ch)
        # self.assertRegex(stream_capture.getvalue(), r'.*\[main\]: target is already compiled*')

        # stream_capture = io.StringIO()
        # ch = logging.StreamHandler(stream_capture)
        # ch.setLevel(logging.DEBUG)
        # logger.addHandler(ch)
        # clang_build_try_except(['-d', 'test/mwe', '-V', '-f'])
        # logger.removeHandler(ch)
        # self.assertRegex(stream_capture.getvalue(), r'.*\[main\]: target needs to build sources*')


    def test_automatic_include_folders(self):
        clang_build_try_except(['-d', 'test/mwe_with_default_folders', '-V'])

        try:
            output = subprocess.check_output(['./build/default/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertEqual(output, 'Calculated Magic: 30')

    def test_toml_mwe(self):
        clang_build_try_except(['-d', 'test/toml_mwe'])

        try:
            output = subprocess.check_output(['./build/default/bin/runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertEqual(output, 'Hello!')

    def test_toml_custom_folder(self):
        clang_build_try_except(['-d', 'test/toml_with_custom_folder'])

        try:
            output = subprocess.check_output(['./build/default/bin/runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertEqual(output, 'Hello!')

    def test_external_scripts(self):
        clang_build_try_except(['-d', 'test/external_scripts', '-V'])

        try:
            output = subprocess.check_output(['./build/default/bin/runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertEqual(output, 'the version is 1.2.0')

    def test_subproject(self):
        clang_build_try_except(['-d', 'test/subproject', '-V'])

        try:
            output = subprocess.check_output(['./build/mainproject/default/bin/runLib'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertEqual(output, 'Hello! mylib::triple(3) returned 9')

    def test_boost_filesystem(self):
        clang_build_try_except(['-d', 'test/boost-filesystem', '-V'])

        try:
            output = subprocess.check_output(['./build/myproject/default/bin/myexe', 'build'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertEqual(output, '"build" is a directory')

    def test_c_library(self):
        clang_build_try_except(['-d', 'test/c-library', '-V'])

        try:
            output = subprocess.check_output(['./build/mainproject/default/bin/myexe'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertEqual(output, '3 2 0'+os.linesep+'3 1 0')

    def test_build_all(self):
        clang_build_try_except(['-d', 'test/c-library', '-V', '-a'])

        try:
            output = subprocess.check_output(['./build/qhull/qhull-executable/default/bin/qhull', '-V'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail('Could not run a target which should have been built')

        self.assertEqual(output, 'qhull_r 7.2.0 (2015.2.r 2016/01/18)')

    def test_platform_flags(self):
        clang_build_try_except(['-d', 'test/platform_flags', '-V', '--debug'])

        try:
            output = subprocess.check_output(['./build/default/bin/myexe'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        from sys import platform as _platform
        if _platform == 'linux' or _platform == 'linux2':
            self.assertEqual(output, 'Hello Linux!')
        elif _platform == 'darwin':
            self.assertEqual(output, 'Hello OSX!')
        elif _platform == 'win32':
            self.assertEqual(output, 'Hello Windows!')
        else:
            raise RuntimeError('Tried to run test_platform_flags on unsupported platform ' + _platform)

    def test_openmp(self):
        clang_build_try_except(['-d', 'test/openmp', '-V'])

        try:
            output = subprocess.check_output(['./build/default/bin/runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertRegex(output, r'Hello from thread 1, nthreads*')

    def test_mwe_two_targets(self):
        clang_build_try_except(['-d', 'test/multi_target_external', '-V', '--bundle'])

        try:
            output = subprocess.check_output(['./build/myexe/default/bin/runLib'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertEqual(output, 'Hello! mylib::calculate() returned 2')

    def test_automatic_tests_examples(self):
        clang_build_try_except(['-d', 'test/automatic_tests_examples', '-V', '--tests', '--examples'])

        try:
            output = subprocess.check_output(['./build/mylib/default/tests/bin/test'], stderr=subprocess.STDOUT).decode('utf-8').strip()
            print(output)
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        clang_build_try_except(['-d', 'test/automatic_tests_examples', '-V', '--runtests'])

        self.assertRegex(output, r'.*All tests passed.*')

        try:
            output = subprocess.check_output(['./build/mylib/default/examples/bin/example_magic_function'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            self.fail(f'Could not run compiled program. Message:\n{e.output}')

        self.assertRegex(output, r'.*Calling `mylib::magic_function\(1, 2\)` returns `5`')

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