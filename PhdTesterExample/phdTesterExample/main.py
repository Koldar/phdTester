import logging

from phdTesterExample.factory import SortResearchField


def main():
    logging.basicConfig(level=logging.INFO)

    factory = SortResearchField()
    # TODO alter run parameters (by adding *arg, **kwargs
    factory.run(None)

    logging.critical("DONE!")


if __name__ == "__main__":
    main()
