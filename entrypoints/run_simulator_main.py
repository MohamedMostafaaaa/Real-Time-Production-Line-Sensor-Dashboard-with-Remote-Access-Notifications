import runpy
import traceback

def main():
    try:
        runpy.run_module("simulator.run_simulator", run_name="__main__")
    except Exception:
        traceback.print_exc()
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
