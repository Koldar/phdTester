import logging
import sys

from phdTesterExample.factory import SortResearchField


def main():
    logging.basicConfig(level=logging.INFO)

    factory = SortResearchField()
    factory.run(cli_commands=sys.argv[1:])

    logging.critical("DONE!")


if __name__ == "__main__":
    main()
