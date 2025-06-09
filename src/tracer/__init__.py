"""Tracer package for function call tracing."""

from .core import Tracer, start_tracing, stop_tracing, set_tracer_scope

__all__ = ['Tracer', 'start_tracing', 'stop_tracing', 'set_tracer_scope']
