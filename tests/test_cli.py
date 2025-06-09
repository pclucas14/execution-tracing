import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
import tempfile
import subprocess

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cli.main import main
from tracer.core import start_tracing, stop_tracing

def run_tracer(script_path, output_file=None, track_external_calls=True):
    """Helper function to run the tracer on a script."""
    import subprocess
    import sys
    
    # Get the directory containing the script
    script_dir = os.path.dirname(script_path)
    
    # Start tracing
    start_tracing(scope_path=script_dir, track_external_calls=track_external_calls)
    
    try:
        # Execute the script
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        # Create a new namespace for execution
        script_globals = {'__file__': script_path, '__name__': '__main__'}
        exec(script_content, script_globals)
    finally:
        # Stop tracing and save output
        stop_tracing(output_file)

class TestCLI(unittest.TestCase):

    def test_basic_trace_execution(self):
        """Test that the tracer can be imported and basic functions work."""
        from tracer.core import Tracer
        tracer = Tracer()
        tracer.start()
        self.assertTrue(tracer.is_tracing)
        tracer.stop()
        self.assertFalse(tracer.is_tracing)

    def test_cli_module_integration(self):
        """Test that CLI modules can be imported successfully."""
        try:
            from cli.main import main
            self.assertTrue(callable(main))
        except ImportError as e:
            self.fail(f"Failed to import CLI modules: {e}")

    @patch('builtins.open', mock_open(read_data='print("Hello World")'))
    @patch('builtins.exec')
    @patch('cli.main.stop_tracing')
    @patch('cli.main.start_tracing')
    def test_main_with_default_args(self, mock_start_tracing, mock_stop_tracing, mock_exec):
        with patch.object(sys, 'argv', ['main.py', 'test_script.py']):
            main()
        
        # Verify that tracing was started and stopped
        mock_start_tracing.assert_called_once()
        mock_stop_tracing.assert_called_once()
        # Verify the script was "executed"
        mock_exec.assert_called_once()

    @patch('builtins.open', mock_open(read_data='print("Hello World")'))
    @patch('builtins.exec')
    @patch('cli.main.stop_tracing')
    @patch('cli.main.start_tracing')
    def test_main_with_output_file(self, mock_start_tracing, mock_stop_tracing, mock_exec):
        with patch.object(sys, 'argv', ['main.py', 'test_script.py', '-o', 'output.json']):
            main()
        
        # Verify that tracing was started and stopped with output file
        mock_start_tracing.assert_called_once()
        mock_stop_tracing.assert_called_once_with('output.json')
        mock_exec.assert_called_once()

    @patch('builtins.open', mock_open(read_data='print("Hello World")'))
    @patch('builtins.exec')
    @patch('cli.main.stop_tracing')
    @patch('cli.main.start_tracing')
    def test_main_with_no_external_calls(self, mock_start_tracing, mock_stop_tracing, mock_exec):
        with patch.object(sys, 'argv', ['main.py', 'test_script.py', '--no-external-calls']):
            main()
        
        # Verify that tracing was started with track_external_calls=False
        call_args = mock_start_tracing.call_args
        self.assertIn('track_external_calls', call_args.kwargs)
        self.assertFalse(call_args.kwargs['track_external_calls'])
        
        mock_stop_tracing.assert_called_once()
        mock_exec.assert_called_once()

    def setUp(self):
        self.test_script_content = '''
def test_function():
    return "hello world"

if __name__ == "__main__":
    result = test_function()
    print(result)
'''

    def test_output_file_creation(self):
        """Test that output file creation works correctly."""
        from tracer.core import Tracer
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as f:
            temp_file = f.name
        
        try:
            tracer = Tracer()
            tracer.start()
            tracer.log_function_call('test_function', {'arg': 'value'}, is_external=False)
            
            # Write output to file
            output = tracer.get_trace_output()
            with open(temp_file, 'w') as f:
                f.write(output)
            
            # Verify file was created and contains valid JSON
            self.assertTrue(os.path.exists(temp_file))
            with open(temp_file, 'r') as f:
                data = json.load(f)
            
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['name'], 'test_function')
            
        finally:
            # Clean up
            if os.path.exists(temp_file):
                os.unlink(temp_file)

if __name__ == '__main__':
    unittest.main()