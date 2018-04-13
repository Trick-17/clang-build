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
        clang_build.build(clang_build.parse_args(['-d', 'test/mwe']))

        try:
            output = subprocess.check_output(['./main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')

    def test_script_call(self):
        try:
            subprocess.check_output(['clang-build', '-d', 'test/mwe', '-V'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            self.fail('Compilation failed')
        try:
            output = subprocess.check_output(['./main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')


    def test_hello_world_rebuild(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/mwe']))
        logger = logging.getLogger('clang_build')
        logger.setLevel(logging.DEBUG)
        stream_capture = io.StringIO()
        ch = logging.StreamHandler(stream_capture)
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        clang_build.build(clang_build.parse_args(['-d', 'test/mwe', '-V']))
        try:
            output = subprocess.check_output(['./main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        logger.removeHandler(ch)

        self.assertRegex(stream_capture.getvalue(), r'.*Target \[main\] is already compiled.*')
        self.assertEqual(output, 'Hello!')

    def test_automatic_include_folders(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/mwe_with_default_folders', '-V']))

        try:
            output = subprocess.check_output(['./main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')
        calculated_integer, calculated_vector = output.splitlines()
        self.assertEqual(calculated_integer, 'Calculated Integer: 1253643')
        self.assertEqual(calculated_vector, 'Calculated Vector:  0 0 1')

    def test_toml_mwe(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/toml_mwe']))

        try:
            output = subprocess.check_output(['./runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')

    def test_toml_custom_folder(self):
        clang_build.build(clang_build.parse_args(['-d', 'test/toml_with_custom_folder']))

        try:
            output = subprocess.check_output(['./runHello'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')


    def tearDown(self):
        if pathlib2.Path('build').exists():
            shutil.rmtree('build')

        if pathlib2.Path('main').exists():
            pathlib2.Path('main').unlink()

        if pathlib2.Path('runHello').exists():
            pathlib2.Path('runHello').unlink()


if __name__ == '__main__':
    unittest.main()