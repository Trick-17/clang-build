"""Module for the Circle class."""

class Circle(list):
    """List with a circular dependency representation.

    Utility class to print circular dependencies. Given
    a list ["A", "B", "A"], this list will print as:

        A -> B -> A

    indicating the circular dependency.
    """

    def __repr__(self) -> str:
        """Return a representation of this circle.

        Returns
        -------
        str
            An arrow connected string of the circular
            dependency

        """
        return " -> ".join(repr(item) for item in self)

    def __str__(self) -> str:
        """Return a string representation of this circle.

        Returns
        -------
        str
            An arrow connected string of the circular
            dependency

        """
        return " -> ".join(str(item) for item in self)
