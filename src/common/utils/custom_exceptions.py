class IncorrectCredentials(Exception):
    pass


class UserAlreadyExists(Exception):
    pass


class UserBlocked(Exception):
    pass

class NotFoundException(Exception):
    def __init__(self, resource: str, identifier: str, status_code: str):
        self.resource = resource
        self.identifier = identifier
        self.status_code = status_code


class NoAvailableRooms(Exception):
    pass

class InvalidDates(Exception):
    pass