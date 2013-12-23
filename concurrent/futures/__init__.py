# Copyright 2009 Brian Quinlan. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

"""Execute computations asynchronously using threads or processes."""

__author__ = 'Brian Quinlan (brian@sweetapp.com)'

from concurrent.futures._base import (FIRST_COMPLETED,
                                      FIRST_EXCEPTION,
                                      ALL_COMPLETED,
                                      Future,
                                      Executor,
                                      wait,
                                      as_completed)

from .exceptions import CancelledError, TimeoutError
#from concurrent.executors.process import ProcessPoolExecutor
#from concurrent.executors.thread import ThreadPoolExecutor
