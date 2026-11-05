import sys

from it_toolkit.core.application import Application

def main():
    try:
        application = Application()
        application.run()
    except KeyboardInterrupt:
        print("\nToolkit interrupted.")
        return 130
    except Exception as error:
        print(f"\nToolkit error: {error}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())