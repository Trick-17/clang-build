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
            printout = f'Target {target} did not compile. Errors:'
            for file, output in errors:
                for out in output:
                    row = out['row']
                    column = out['column']
                    messagetype = out['type']
                    message = out['message']
                    printout += f'\n{file}:{row}:{column}: {messagetype}: {message}'
            logger.error(printout)
    except LinkError as link_error:
        logger = logging.getLogger('clang_build')
        logger.error('Linking was unsuccessful:')
        for target, errors in link_error.error_dict.items():
            printout = f'Target {target} did not link. Errors:\n{errors}'
            logger.error(printout)

class TestClangBuild(unittest.TestCase):
    def test_hello_world_mwe(self):
        clang_build_try_except(['-d', 'test/mwe', '-p'])

        try:
            output = subprocess.check_output(['./build/default/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')

    def test_compile_error(self):
        with self.assertRaises(CompileError):
            clang_build.build(clang_build.parse_args(['-d', 'test/mwe_build_error', '-V', '-p']))

    def test_script_call(self):
        try:
            subprocess.check_output(['clang-build', '-d', 'test/mwe', '-V', '-p'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            self.fail('Compilation failed')
        try:
            output = subprocess.check_output(['./build/default/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')

    def test_hello_world_rebuild(self):
        clang_build_try_except(['-d', 'test/mwe', '-p'])
        logger = logging.getLogger('clang_build')
        logger.setLevel(logging.DEBUG)
        stream_capture = io.StringIO()
        ch = logging.StreamHandler(stream_capture)
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        clang_build_try_except(['-d', 'test/mwe', '-V', '-p'])
        try:
            output = subprocess.check_output(['./build/default/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        logger.removeHandler(ch)

        self.assertRegex(stream_capture.getvalue(), r'.*Target \[main\] is already compiled.*')
        self.assertEqual(output, 'Hello!')

    def test_automatic_include_folders(self):
        clang_build_try_except(['-d', 'test/mwe_with_default_folders', '-V', '-p'])

        try:
            output = subprocess.check_output(['./build/default/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Calculated Magic: 30')

    def test_toml_mwe(self):
        clang_build_try_except(['-d', 'test/toml_mwe', '-p'])

        try:
            output = subprocess.check_output(['./build/default/bin/runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')

    def test_toml_custom_folder(self):
        clang_build_try_except(['-d', 'test/toml_with_custom_folder', '-p'])

        try:
            output = subprocess.check_output(['./build/default/bin/runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')

    def test_external_scripts(self):
        clang_build_try_except(['-d', 'test/external_scripts', '-V', '-p'])

        try:
            output = subprocess.check_output(['./build/default/bin/runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'the version is 1.2.0')

    def test_subproject(self):
        clang_build_try_except(['-d', 'test/subproject', '-V', '-p'])

        try:
            output = subprocess.check_output(['./build/mainproject/default/bin/runLib'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello! mylib::triple(3) returned 9')

    def test_boost_filesystem(self):
        clang_build_try_except(['-d', 'test/boost-filesystem', '-V', '-p'])

        try:
            output = subprocess.check_output(['./build/myexe/default/bin/myexe', 'build'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, '"build" is a directory')

    # def test_openmp(self):
    #     clang_build_try_except(['-d', 'test/openmp', '-V', '-p'])

    #     try:
    #         output = subprocess.check_output(['./build/default/bin/runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
    #     except subprocess.CalledProcessError:
    #         self.fail('Could not run compiled program')

        # self.assertEqual(output, 'Hello from thread 1, nthreads 8')

    # def test_mwe_two_targets(self):
    #     clang_build_try_except(['-d', 'test/multi_target_external', '-V', '-p'])

    #     try:
    #         output = subprocess.check_output(['./build/myexe/default/bin/runLib'], stderr=subprocess.STDOUT).decode('utf-8').strip()
    #     except subprocess.CalledProcessError:
    #         self.fail('Could not run compiled program')

    #     self.assertEqual(output, 'Hello!')

    def tearDown(self):
        if _Path('build').exists():
            shutil.rmtree('build', onerror = on_rm_error)


if __name__ == '__main__':
    freeze_support()
    unittest.main()