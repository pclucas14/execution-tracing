import unittest
from unittest.mock import patch, MagicMock
import sys
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

if __name__ == '__main__':
    unittest.main()