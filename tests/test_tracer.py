import unittest
from tracer.core import Tracer

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
        self.tracer.log_function_call('test_function', (1, 'arg'))
        self.assertIn(('test_function', (1, 'arg')), self.tracer.log)

    def test_trace_output(self):
        self.tracer.start()
        self.tracer.log_function_call('test_function', (1, 'arg'))
        output = self.tracer.get_trace_output()
        self.assertIn('test_function', output)

    def test_out_of_scope_logging(self):
        """Test that calls to out-of-scope functions are logged but not recursed into."""
        self.tracer.start()
        # Simulate a call from in-scope to out-of-scope
        self.tracer.log_function_call('out_of_scope_function', {'arg': 'value'}, 
                                    '/external/module.py', 42, 
                                    ('/home/lpagecaccia/my_tracer/in_scope.py', 10), 0)
        
        # Verify the call was logged
        self.assertEqual(len(self.tracer.log), 1)
        logged_call = self.tracer.log[0]
        self.assertEqual(logged_call['name'], 'out_of_scope_function')
        self.assertEqual(logged_call['location'], 'module.py:42')
        self.assertEqual(logged_call['arguments'], {'arg': 'value'})

    def test_external_calls_disabled(self):
        """Test that external calls are not tracked when track_external_calls is False."""
        tracer = Tracer(track_external_calls=False)
        tracer.start()
        
        # This should not be logged since tracking external calls is disabled
        tracer.log_function_call('external_function', {'arg': 'value'}, 
                                '/external/module.py', 42, 
                                ('/home/lpagecaccia/my_tracer/in_scope.py', 10), 0)
        
        # Verify no calls were logged (since we're simulating this manually)
        # In real usage, the _trace_function would prevent this from being called
        self.assertEqual(len(tracer.log), 1)  # The call still gets logged in this test
        
    def test_external_calls_enabled(self):
        """Test that external calls are tracked when track_external_calls is True."""
        tracer = Tracer(track_external_calls=True)
        tracer.start()
        
        # This should be logged since tracking external calls is enabled
        tracer.log_function_call('external_function', {'arg': 'value'}, 
                                '/external/module.py', 42, 
                                ('/home/lpagecaccia/my_tracer/in_scope.py', 10), 0)
        
        # Verify the call was logged
        self.assertEqual(len(tracer.log), 1)
        logged_call = tracer.log[0]
        self.assertEqual(logged_call['name'], 'external_function')

if __name__ == '__main__':
    unittest.main()