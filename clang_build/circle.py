class Circle(list):
    def __repr__(self) -> str:
        return " -> ".join(str(item) for item in self)

    def __str__(self) -> str:
        return self.__repr__()