class TreeEntry:
    def __repr__(self) -> str:
        return self.identifier

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return self.string_to_hash() == other

        return self.string_to_hash() == other.string_to_hash()

    def __hash__(self) -> int:
        return hash(self.string_to_hash())

    def string_to_hash(self) -> str:
        return self.identifier
