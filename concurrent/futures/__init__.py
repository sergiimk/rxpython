# Copyright 2009 Brian Quinlan. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

"""Execute computations asynchronously using threads or processes."""

__author__ = 'Brian Quinlan (brian@sweetapp.com)'

from concurrent.futures.old.util import (FIRST_COMPLETED,
                                         FIRST_EXCEPTION,
                                         ALL_COMPLETED,
                                         wait,
                                         as_completed)

from concurrent.futures.old.executor import Executor

from concurrent.futures.cooperative import FutureBase
from concurrent.futures.old.future import Future
from .exceptions import CancelledError, TimeoutError, InvalidStateError
#from concurrent.executors.process import ProcessPoolExecutor
#from concurrent.executors.thread import ThreadPoolExecutor
