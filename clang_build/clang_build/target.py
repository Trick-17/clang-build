class Target:
    def __init__(self, my_properties, dependencies=None):
        self.my_properties = my_properties
        self.targets_I_depend_on = []
        self.targets_that_depend_on_me = dependencies if dependencies else []
