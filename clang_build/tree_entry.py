"""Module for the TreeEntry class."""


class TreeEntry:
    """Abstract class to make an object insertable into a tree.

    Implements means to identify and compare an object
    based on a member variable called ``identifier``
    which every subclass has to define.
    """

    identifier = None

    def __eq__(self, other) -> bool:
        """Declare two objects identical if ``identifier`` is the same."""
        if isinstance(other, str):
            return self.identifier == other

        return self.identifier == other.identifier

    def __hash__(self) -> int:
        """Return a hash value.

        Hashes the ``identifier`` value of this
        object making every object with the same
        ``identifier`` equal to this one (in terms
        of hash value).
        """
        return hash(self.identifier)