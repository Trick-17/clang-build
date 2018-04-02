import unittest
import subprocess
import shutil
import pathlib2

class TestStringMethods(unittest.TestCase):

    def test_hello_world_mwe(self):
        try:
            subprocess.check_call(['clang-build', '-d', 'test/hello', '-V'])
        except subprocess.CalledProcessError:
            self.fail('Compilation failed')
        try:
            output = subprocess.check_output(['./main'], stderr=subprocess.STDOUT).decode('utf-8').strip()
        except subprocess.CalledProcessError:
            self.fail('Could not run compiled program')

        self.assertEqual(output, 'Hello!')

    def tearDown(self):
        if pathlib2.Path('build').exists():
            shutil.rmtree('build')

        if pathlib2.Path('main').exists():
            pathlib2.Path('main').unlink()

if __name__ == '__main__':
    unittest.main()