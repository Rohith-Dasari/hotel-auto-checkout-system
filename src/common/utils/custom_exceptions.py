class IncorrectCredentials(Exception):
    pass


class UserAlreadyExists(Exception):
    pass


class UserBlocked(Exception):
    pass

class NotFoundException(Exception):
    def __init__(self, resource: str, identifier: str, status_code: int):
        self.resource = resource
        self.identifier = identifier
        self.status_code = status_code  
    def __str__(self):
        return f"{self.resource} '{self.identifier}' not found"


class NoAvailableRooms(Exception):
    pass

class InvalidDates(Exception):
    pass

class RoomAlreadyExists(Exception):
    pass