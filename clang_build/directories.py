from copy import copy

class Directories:

    def include_public_total(self):
        includes = copy(self.include_public)
        for target in self.dependencies:
            includes += target.directories.include_public_total()

        return includes

    def __init__(self, files, dependencies):
        self.dependencies = dependencies

        # Include directories
        self.include_private = files["include_directories"]
        self.include_public = files["include_directories_public"]


        # Make unique and resolve
        self.include_private = list(
            dict.fromkeys(dir.resolve() for dir in self.include_private)
        )
        self.include_public = list(
            dict.fromkeys(dir.resolve() for dir in self.include_public)
        )

    def final_directories_list(self):
        return list(dict.fromkeys(self.include_private + self.include_public_total()))

    def include_command(self):
        include_directories_command = []
        for directory in self.final_directories_list():
            include_directories_command += ["-I", str(directory)]

        return include_directories_command

    def make_private_directories_public(self):
        self.include_public = self.final_directories_list()
        self.include_private = []
