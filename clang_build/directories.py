class Directories:
    def __init__(self, files, dependencies, public_dependencies):
        """The root and build directories are taken from `target_description`,
        include directories from `files` and `dependencies`.

        Include directories are made unique.
        """

        self.dependencies = dependencies

        # Include directories
        self.include_private = files["include_directories"]
        self.include_public = files["public_include_directories"]

        # Default include path
        # if self.root_directory.joinpath('include').exists():
        #    self._include_directories_public = [self.root_directory.joinpath('include')] + self._include_directories_public

        # Public include directories of private dependencies are applied
        for target in dependencies:
            self.include_private += target.directories.include_public

        # Public include directories of public dependencies are forwarded
        for target in public_dependencies:
            self.include_public += target.directories.include_public

        # Make unique and resolve
        self.include_private = list(
            dict.fromkeys(dir.resolve() for dir in self.include_private)
        )
        self.include_public = list(
            dict.fromkeys(dir.resolve() for dir in self.include_public)
        )

    def final_directories_list(self):
        return list(dict.fromkeys(
            self.include_private + self.include_public
        ))

    def make_private_directories_public(self):
        self.include_public = self.final_directories_list()
        self.include_private = []