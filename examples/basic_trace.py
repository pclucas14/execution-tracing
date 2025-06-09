import sys
import os

def main():
    # Add the project root directory to Python's path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
    sys.path.insert(0, project_root)
    
    # Import and run the CLI main function
    from cli.main import main as cli_main
    cli_main()

if __name__ == "__main__":
    main()