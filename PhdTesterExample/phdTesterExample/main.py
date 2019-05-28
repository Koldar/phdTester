import logging
import sys

from phdTesterExample.factory import SortResearchField


def main():
    factory = SortResearchField()
    factory.run(cli_commands=sys.argv[1:])


if __name__ == "__main__":
    main()
