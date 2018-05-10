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


def on_rm_error( func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and unlink it.
    os.chmod( path, stat.S_IWRITE )
    os.unlink( path )


class TestClangBuild(unittest.TestCase):
    def test_hello_world_mwe(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/mwe']), False)

        try:
            output = subprocess.check_output(['./build/default/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')

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
        clang_build.build(clang_build.parse_args(['-d', 'test/mwe']), False)
        logger = logging.getLogger('clang_build')
        logger.setLevel(logging.DEBUG)
        stream_capture = io.StringIO()
        ch = logging.StreamHandler(stream_capture)
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        clang_build.build(clang_build.parse_args(['-d', 'test/mwe', '-V']), False)
        try:
            output = subprocess.check_output(['./build/default/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        logger.removeHandler(ch)

        self.assertRegex(stream_capture.getvalue(), r'.*Target \[main\] is already compiled.*')
        self.assertEqual(output, 'Hello!')

    def test_automatic_include_folders(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/mwe_with_default_folders', '-V']), False)

        try:
            output = subprocess.check_output(['./build/default/bin/main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')
        
        self.assertEqual(output, 'Calculated Magic: 30')

    def test_toml_mwe(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/toml_mwe']), False)

        try:
            output = subprocess.check_output(['./build/default/bin/runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')

    def test_toml_custom_folder(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/toml_with_custom_folder']), False)

        try:
            output = subprocess.check_output(['./build/default/bin/runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')

    def test_external_scripts(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/external_scripts']), False)

        try:
            output = subprocess.check_output(['./build/default/bin/runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'the version is 1.2.0')

    # def test_mwe_two_targets(self):
    #     logging.getLogger().setLevel(logging.DEBUG)
    #     clang_build.build(clang_build.parse_args(['-d', 'test/multi_target_external']), False)

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