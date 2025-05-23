import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
import subprocess
from src.cli.main import main

class TestCLI(unittest.TestCase):

    @patch('src.cli.main.run_tracer')
    def test_main_with_default_args(self, mock_run_tracer):
        sys.argv = ['main.py']
        main()
        mock_run_tracer.assert_called_once_with('default', 42)

    @patch('src.cli.main.run_tracer')
    def test_main_with_custom_args(self, mock_run_tracer):
        sys.argv = ['main.py', 'custom_arg']
        main()
        mock_run_tracer.assert_called_once_with('custom_arg', 42)

    @patch('src.cli.main.run_tracer')
    def test_main_with_multiple_args(self, mock_run_tracer):
        sys.argv = ['main.py', 'arg1', 'arg2']
        main()
        mock_run_tracer.assert_called_once_with('arg1', 42)

    def setUp(self):
        self.test_script_content = '''
def test_function():
    return "hello world"

if __name__ == "__main__":
    result = test_function()
    print(result)
'''

    def test_basic_trace_execution(self):
        """Test that the basic trace script can execute without errors."""
        # Create a temporary test script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(self.test_script_content)
            test_script_path = f.name

        try:
            # Get the path to basic_trace.py
            examples_dir = os.path.join(os.path.dirname(__file__), '..', 'examples')
            basic_trace_path = os.path.join(examples_dir, 'basic_trace.py')
            
            # Run the basic trace script
            result = subprocess.run([
                sys.executable, basic_trace_path, test_script_path
            ], capture_output=True, text=True, timeout=30)
            
            # Should not crash (exit code 0 or reasonable error)
            self.assertIn(result.returncode, [0], 
                         f"Script failed with return code {result.returncode}. "
                         f"Stdout: {result.stdout}, Stderr: {result.stderr}")
            
        finally:
            # Clean up
            os.unlink(test_script_path)

    def test_output_file_creation(self):
        """Test that output file is created when specified."""
        # Create a temporary test script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(self.test_script_content)
            test_script_path = f.name

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            output_file_path = f.name

        try:
            # Get the path to basic_trace.py
            examples_dir = os.path.join(os.path.dirname(__file__), '..', 'examples')
            basic_trace_path = os.path.join(examples_dir, 'basic_trace.py')
            
            # Run the basic trace script with output file
            result = subprocess.run([
                sys.executable, basic_trace_path, test_script_path, 
                '-o', output_file_path
            ], capture_output=True, text=True, timeout=30)
            
            # Should create output file
            self.assertTrue(os.path.exists(output_file_path), 
                           f"Output file was not created. Return code: {result.returncode}, "
                           f"Stdout: {result.stdout}, Stderr: {result.stderr}")
            
            # Output file should contain JSON
            with open(output_file_path, 'r') as f:
                content = f.read()
                self.assertTrue(len(content) > 0, "Output file is empty")
                
        finally:
            # Clean up
            os.unlink(test_script_path)
            if os.path.exists(output_file_path):
                os.unlink(output_file_path)

if __name__ == '__main__':
    unittest.main()