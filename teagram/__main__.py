import sys

if sys.version_info < (3, 8, 0):
    print("You have to use python 3.8+")
    sys.exit()

import argparse

parser = argparse.ArgumentParser()

parser.add_argument("--no-qr", "-nq", action="store_true")
parser.add_argument("--no-web", "-nw", action="store_true")

parser.add_argument("--test-mode", "-test", action="store_true")
parser.add_argument("--debug", "-d", action="store_true")

parser.add_argument("--hot-reload", "-w", action="store_true")
parser.add_argument("--port", "-p", type=int, required=False)

if __name__ == "__main__":
    from .main import Main

    main = Main(parser.parse_args())
    main.start()
