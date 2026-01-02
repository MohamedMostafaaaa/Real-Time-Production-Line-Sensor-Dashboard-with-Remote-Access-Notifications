import runpy
import traceback

def main():
    try:
        # Equivalent to: python -m app.dev.run_app
        runpy.run_module("app.dev.run_app", run_name="__main__")
    except Exception:
        traceback.print_exc()
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
