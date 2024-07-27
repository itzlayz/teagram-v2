import sys

if sys.version_info < (3, 8, 0):
    print("You have to use python 3.8+")
    sys.exit()

if __name__ == "__main__":
    from .main import Main

    main = Main(None)
    main.start()
