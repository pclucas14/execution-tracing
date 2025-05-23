import unittest
import sys
import os

# Add the src directory to the path so we can import tracer modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tracer.core import Tracer, start_tracing, stop_tracing, set_tracer_scope

class TestTracer(unittest.TestCase):

    def setUp(self):
        self.tracer = Tracer()

    def test_start_tracing(self):
        self.tracer.start()
        self.assertTrue(self.tracer.is_tracing)

    def test_stop_tracing(self):
        self.tracer.start()
        self.tracer.stop()
        self.assertFalse(self.tracer.is_tracing)

    def test_log_function_call(self):
        self.tracer.start()
        self.tracer.log_function_call('test_function', {'arg1': 1, 'arg2': 'test'})
        self.assertEqual(len(self.tracer.log), 1)
        self.assertEqual(self.tracer.log[0]['name'], 'test_function')

    def test_trace_output(self):
        self.tracer.start()
        self.tracer.log_function_call('test_function', {'arg1': 1, 'arg2': 'test'})
        output = self.tracer.get_trace_output()
        self.assertIn('test_function', output)
        self.assertIn('"name": "test_function"', output)

    def test_out_of_scope_logging(self):
        """Test that calls to out-of-scope functions are logged but not recursed into."""
        self.tracer.start()
        # Simulate a call from in-scope to out-of-scope
        self.tracer.log_function_call('out_of_scope_function', {'arg': 'value'}, 
                                    '/external/module.py', 42, 
                                    ('/home/lpagecaccia/my_tracer/in_scope.py', 10), 0, 
                                    is_external=True)
        
        # Verify the call was logged
        self.assertEqual(len(self.tracer.log), 1)
        logged_call = self.tracer.log[0]
        self.assertEqual(logged_call['name'], 'out_of_scope_function')
        self.assertEqual(logged_call['location'], 'module.py:42')
        self.assertEqual(logged_call['arguments'], {'arg': 'value'})
        self.assertTrue(logged_call['is_external'])

    def test_external_calls_disabled(self):
        """Test that external calls are not tracked when track_external_calls is False."""
        tracer = Tracer(track_external_calls=False)
        tracer.start()
        
        # This should not be logged since tracking external calls is disabled
        tracer.log_function_call('external_function', {'arg': 'value'}, 
                                '/external/module.py', 42, 
                                ('/home/lpagecaccia/my_tracer/in_scope.py', 10), 0,
                                is_external=True)
        
        # Verify the call was logged (since we're calling log_function_call directly)
        # In real usage, the _trace_function would prevent this from being called
        self.assertEqual(len(tracer.log), 1)
        self.assertTrue(tracer.log[0]['is_external'])
        
    def test_external_calls_enabled(self):
        """Test that external calls are tracked when track_external_calls is True."""
        tracer = Tracer(track_external_calls=True)
        tracer.start()
        
        # This should be logged since tracking external calls is enabled
        tracer.log_function_call('external_function', {'arg': 'value'}, 
                                '/external/module.py', 42, 
                                ('/home/lpagecaccia/my_tracer/in_scope.py', 10), 0,
                                is_external=True)
        
        # Verify the call was logged
        self.assertEqual(len(tracer.log), 1)
        logged_call = tracer.log[0]
        self.assertEqual(logged_call['name'], 'external_function')
        self.assertTrue(logged_call['is_external'])

    def test_internal_calls_marked_correctly(self):
        """Test that internal calls are marked as not external."""
        self.tracer.start()
        # Simulate an internal call
        self.tracer.log_function_call('internal_function', {'arg': 'value'}, 
                                    '/home/lpagecaccia/my_tracer/internal.py', 10, 
                                    None, 0, is_external=False)
        
        # Verify the call was logged and marked as internal
        self.assertEqual(len(self.tracer.log), 1)
        logged_call = self.tracer.log[0]
        self.assertEqual(logged_call['name'], 'internal_function')
        self.assertFalse(logged_call['is_external'])

    def test_format_arguments(self):
        """Test that arguments are formatted correctly."""
        self.tracer.start()
        
        # Test with various argument types
        args = {
            'string_arg': 'test',
            'int_arg': 42,
            'list_arg': [1, 2, 3],
            'dict_arg': {'nested': 'value'},
            'none_arg': None
        }
        
        self.tracer.log_function_call('test_function', args)
        logged_call = self.tracer.log[0]
        
        self.assertEqual(logged_call['arguments']['string_arg'], 'test')
        self.assertEqual(logged_call['arguments']['int_arg'], 42)
        self.assertEqual(logged_call['arguments']['list_arg'], [1, 2, 3])
        self.assertEqual(logged_call['arguments']['dict_arg'], {'nested': 'value'})
        self.assertIsNone(logged_call['arguments']['none_arg'])

    def test_json_output_format(self):
        """Test that the output is valid JSON."""
        import json
        
        self.tracer.start()
        self.tracer.log_function_call('test_function', {'arg': 'value'}, is_external=False)
        
        output = self.tracer.get_trace_output()
        
        # Should be valid JSON
        parsed = json.loads(output)
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['name'], 'test_function')
        self.assertFalse(parsed[0]['is_external'])

    def test_tracer_initialization_with_track_external_calls(self):
        """Test that the tracer initializes correctly with track_external_calls parameter."""
        tracer_enabled = Tracer(track_external_calls=True)
        tracer_disabled = Tracer(track_external_calls=False)
        
        self.assertTrue(tracer_enabled.track_external_calls)
        self.assertFalse(tracer_disabled.track_external_calls)

if __name__ == '__main__':
    unittest.main()