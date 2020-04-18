class Directories:
    def __init__(self, files, dependencies):
        # Include directories
        self.include_private = files["include_directories"]
        self.include_public = files["include_directories_public"]

        # Default include path
        # if self.root_directory.joinpath('include').exists():
        #    self._include_directories_public = [self.root_directory.joinpath('include')] + self._include_directories_public

        # Public include directories of dependencies are forwarded
        for target in self.dependencies:
            self._include_public += target.directories.include_public

        # Make unique and resolve
        self._include_private = list(
            dict.fromkeys(dir.resolve() for dir in self._include_private)
        )
        self._include_public = list(
            dict.fromkeys(dir.resolve() for dir in self._include_public)
        )