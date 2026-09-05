"""A ticket object with a close() that has nothing to do with descriptors."""


class Ticket:
    def __init__(self, ident):
        self.ident = ident
        self.closed = False

    def close(self):
        self.closed = True


def resolve(ident):
    ticket = Ticket(ident)
    ticket.close()
    return ticket
