import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import tempfile
import subprocess
from src.cli.main import main, run_tracer

class TestCLI(unittest.TestCase):

    @patch('src.cli.main.run_tracer')
    def test_main_with_default_args(self, mock_run_tracer):
        with patch.object(sys, 'argv', ['main.py', 'test_script.py']):
            main()
        mock_run_tracer.assert_called_once()
        args, kwargs = mock_run_tracer.call_args
        self.assertEqual(kwargs['script_path'], 'test_script.py')
        self.assertTrue(kwargs['track_external_calls'])

    @patch('src.cli.main.run_tracer')
    def test_main_with_output_file(self, mock_run_tracer):
        with patch.object(sys, 'argv', ['main.py', 'test_script.py', '-o', 'output.json']):
            main()
        mock_run_tracer.assert_called_once()
        args, kwargs = mock_run_tracer.call_args
        self.assertEqual(kwargs['output_file'], 'output.json')

    @patch('src.cli.main.run_tracer')
    def test_main_with_no_external_calls(self, mock_run_tracer):
        with patch.object(sys, 'argv', ['main.py', 'test_script.py', '--no-external-calls']):
            main()
        mock_run_tracer.assert_called_once()
        args, kwargs = mock_run_tracer.call_args
        self.assertFalse(kwargs['track_external_calls'])

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

    def test_cli_module_integration(self):
        """Test that the CLI module can be used directly."""
        # Create a temporary test script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(self.test_script_content)
            test_script_path = f.name

        try:
            # Test the run_tracer function directly
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
                output_file_path = f.name

            # This should not raise an exception
            run_tracer(
                script_path=test_script_path,
                output_file=output_file_path,
                track_external_calls=False
            )
            
            # Check that output file was created
            self.assertTrue(os.path.exists(output_file_path))
            
        finally:
            # Clean up
            os.unlink(test_script_path)
            if os.path.exists(output_file_path):
                os.unlink(output_file_path)

if __name__ == '__main__':
    unittest.main()