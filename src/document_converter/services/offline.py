"""Python network guard for dedicated conversion processes, not an OS sandbox."""
import sys


class NetworkAccessBlocked(PermissionError):
    pass


def install_network_guard():
    """Permanently deny Python socket networking in this process only.

    Install before importing parsers. Audit hooks also cover references to socket
    functions retained by dependencies. Native-library networking is not covered.
    """
    attempts = []
    def deny(event, args):
        if event in {"socket.connect", "socket.bind", "socket.sendto",
                     "socket.getaddrinfo", "socket.gethostbyname",
                     "socket.gethostbyaddr", "socket.getnameinfo"}:
            attempts.append(event)  # Never retain destination addresses or document data.
            raise NetworkAccessBlocked("Network access is disabled during local conversion")
    sys.addaudithook(deny)
    return attempts
