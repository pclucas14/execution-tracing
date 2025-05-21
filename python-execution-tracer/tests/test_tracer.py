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

if __name__ == '__main__':
    unittest.main()