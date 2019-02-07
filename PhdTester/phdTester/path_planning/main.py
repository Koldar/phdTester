import logging
import sys

import coloredlogs

from phdTester.path_planning.factory import PathFindingResearchField


def main():
    # setup logging
    coloredlogs.install(
        level=logging.INFO,
        fmt="%(asctime)s.%(msecs)03d %(processName)s %(filename)s[%(lineno)d]%(levelname)s %(message)s",
        datefmt='%H:%M:%S',
    )

    # get factory
    factory = PathFindingResearchField()

    # run the framework
    factory.run(sys.argv[1:])


if __name__ == "__main__":
    main()
