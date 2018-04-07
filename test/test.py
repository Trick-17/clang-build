import os, sys
import unittest
import subprocess
import shutil
import pathlib2
import logging
import io

from clang_build import clang_build

class TestClangBuild(unittest.TestCase):
    def test_hello_world_mwe(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/hello', '-V']))

        try:
            output = subprocess.check_output(['./main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')

    def test_script_call(self):
        try:
            subprocess.check_call(['clang-build', '-d', 'test/hello', '-V'])
        except subprocess.CalledProcessError:
            self.fail('Compilation failed')
        try:
            output = subprocess.check_output(['./main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')


    def test_hello_world_rebuild(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/hello', '-V']))
        logger = logging.getLogger('clang_build')
        logger.setLevel(logging.DEBUG)
        stream_capture = io.StringIO()
        ch = logging.StreamHandler(stream_capture)
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        clang_build.build(clang_build.parse_args(['-d', 'test/hello', '-V']))
        try:
            output = subprocess.check_output(['./main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        logger.removeHandler(ch)

        self.assertRegex(stream_capture.getvalue(), r'.*Target \[main\] is already compiled.*')
        self.assertEqual(output, 'Hello!')

    def test_automatic_include_folders(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/default_folder_test', '-V']))

        try:
            output = subprocess.check_output(['./main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Calculated Integer: 1253643\nCalculated Vector:  0 0 1')


    def tearDown(self):
        if pathlib2.Path('build').exists():
            shutil.rmtree('build')

        if pathlib2.Path('main').exists():
            pathlib2.Path('main').unlink()


if __name__ == '__main__':
    unittest.main()