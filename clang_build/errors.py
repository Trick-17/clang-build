'''
Module containing custom errors that are
raised by clang-build if something goes wrong.
'''

class CompileError(RuntimeError):
    '''
    Error that is raised if compilation was
    not successful.
    '''
    def __init__(self, message, error_dict=None):
        '''
        :param message: Message of the error
        :param error_dict: A dict containing all errors
                           that occurred during compilation
        '''
        super().__init__(message)
        self.error_dict = error_dict

class LinkError(RuntimeError):
    '''
    Error that is raised if linking was
    not successful.
    '''
    def __init__(self, message, error_dict=None):
        '''
        :param message: Message of the error
        :param error_dict: A dict containing all errors
                           that occurred during compilation
        '''
        super().__init__(message)
        self.error_dict = error_dict