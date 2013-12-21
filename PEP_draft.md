Composable futures for reactive programming
===========================================

Abstract
========

Motivation
==========
* concurrent.futures not composable
* escaping monad
* multiple versions (asyncio)
* benefit

Proposed solution
-----------------
* focused
* no thread pools etc

Specification
=============

Proposed package defines following abstractions:

- `Executor` - a contract for a service that executes async operations.

- `Future` - represents result of async operation which is expected
 to be completed by some `Executor`

- `Promise` - represents a `Future` on the `Executor` side, it is not
 exposed to client and is the only correct way of setting result to
 `Future`.

Future core interface
---------------------

``@property is_completed``

    Returns True if future is completed or cancelled.

``@property is_cancelled``

    Returns True if the future cancellation was requested.

``cancel()``

    Requests cancellation of future. Returns True if future was not
    yet completed or cancelled.

``on_success(fun_res, executor=None)``

	Specified function will be called upon successful future completion.
	fun_res - function that accepts one result argument.
	executor - context to run callback in (default - Synchronous).

``on_failure(fun_ex, executor=None)``

	Specified function will be called upon future failure.
	fun_ex: function that accepts one exception argument.
	executor: context to run callback in (default - Synchronous).

``wait(timeout=None)``

	Blocking wait for future to complete. timeout - time in seconds
	to wait for completion (default - infinite). Returns True if
	future completes within timeout.

``result(timeout=None)``

	Blocking wait for future result. timeout - time in seconds to wait
	for completion (default - infinite). Returns Future result value.

	Raises:
		``TimeoutError``: if future does not complete within timeout.
		``CancelledError``: if future cancellation was requested,
		``Exception``: if future was failed.

	This is one of few ways to drop Future monad, don't use unless it is
	absolutely necessary, prefer future composition.

``exception(timeout=None)``

	Blocking wait for future exception. timeout: time in seconds to wait
	for completion (default - infinite). Returns Exception future failed
	with, including CancelledError, or None if succeeded.
	Raises ``TimeoutError`` if future does not complete within timeout.

	This is one of few ways to drop Future monad, don't use unless it is
	absolutely necessary, prefer future composition.

Promise interface
-----------------

Promise is an only intended way of creating ``Futures``. It is intended
to be inaccessible to clients of services which provide async operations
and is the only right way to set result to the future given to client.

``Promise(clb_executor=None)``

	Creates new ``Promise`` with associated ``Future``.
	clb_executor - specifies default ``Executor`` for running
	``Future.on_success()`` and ``Future.on_failure()`` callbacks
	(default - Synchronous).

``@property is_completed``

	Returns True if associated future is completed or cancelled.

``@property is_cancelled``

	Returns True if the future cancellation was requested by client.

``@property future``

	Returns associated future instance.

``success(result)``

	Completes associated future with provided value.
	Raises ``IllegalStateError`` if future value was already set.

``try_success(result)``

	Completes associated future with provided value.
	Returns True if future value was set and False if it was
	already set before.

``failure(exception)``

	Completes associated future with provided exception.
	Raises ``IllegalStateError`` if future value was already set.

``try_failure(exception)``

	Completes associated future with provided exception.
	Returns True if future value was set and False if it was
	already set before.

``complete(fun, *vargs, **kwargs)``

	Executes provided function and sets future value from result
	or exception if function raises.
	Raises ``IllegalStateError`` if future value was already set.

``try_complete(fun, *vargs, **kwargs)``

	Executes provided function and sets future value from result
	or exception if function raises.
	Returns True if future value was set and False if it was
	already set before.

Future composition
------------------

``@staticmethod successful(result=None, clb_executor=None)``

	Returns successfully completed future. result - value to
	complete future with, clb_executor - default Executor to
	use for running callbacks (default - Synchronous).

``@staticmethod failed(exception, clb_executor=None)``

	Returns failed future. exception - Exception to set to future,
	clb_executor - default Executor to use for running
	callbacks (default - Synchronous).

``@staticmethod completed(fun, *args, clb_executor=None)``

	Returns successful or failed future set from provided function.

``recover(fun_ex, executor=None)``

	Returns future that will contain result of original if it
	completes successfully, or set from result of provided function
	in case of failure. fun_ex - function that accepts Exception
	parameter, executor - Executor to use when performing call to
	function (default - Synchronous).

``map(fun_res, executor=None)``

	Returns future which will be set from result of applying
	provided function to original future value. fun_res - function
	that accepts original result and returns new value,
	executor - Executor to use when performing call to
	function (default - Synchronous).

``then(future_fun, executor=None)``

	Returns future which represents two futures chained one
	after another. Failures are propagated from first future,
	from second future and from callback function.
	future_fun - function that returns future to be chained
	after successful completion of first one
	(or Future instance directly), executor - Executor to use
	when performing call to function (default - Synchronous).

``fallback(future_fun, executor=None)``

	Returns future that will contain result of original if
	it completes successfully, or will be set from future
	returned from provided function in case of failure.
	future_fun - function that returns future to be used for
	fallback (or Future instance directly), executor - Executor
	to use when performing call to function (default - Synchronous).

``@staticmethod all(futures, clb_executor=None)``

	Transforms list of futures into one future that will contain
	list of results. In case of any failure future will be failed
	with first exception to occur. futures - list of futures
	to combine, clb_executor - default executor to use when running
	new future's callbacks (default - Synchronous).

``@staticmethod first(futures, clb_executor=None)``

	Returns future which will be set from result of first future
	to complete, both successfully or with failure.
	futures - list of futures to combine, clb_executor - default
	executor to use when running new future's callbacks
	(default - Synchronous).

``@staticmethod first_successful(futures, clb_executor=None)``

	Returns future which will be set from result of first
	future to complete successfully, last detected error
	will be set in case when all of the provided future fail.
	futures - list of futures to combine, clb_executor - default
	executor to use when running new future's callbacks
	(default - Synchronous).

``@staticmethod reduce(futures, fun, *vargs, executor=None, clb_executor=None)``

	Returns future which will be set with reduced result of
	all provided futures. In case of any failure future will
	be failed with first exception to occur. futures - list
	of futures to combine, fun - reduce-compatible function,
	executor - Executor to use when performing call to function
	(default - Synchronous), clb_executor - default executor
	to use when running new future's callbacks
	(default - Synchronous).

Executors
---------

* out of scope

``submit(fn, *args, **kwargs)``

	Schedules function for execution and return `Future`
	representing pending result.

Performance and overhead
------------------------
* memory
* lightweight completed futures
* synchronous executor

Backward compatibility
======================

Interface differences
---------------------

Executor interface reduced to:

	class Executor:
		def submit(fn, *args, **kwargs) -> Future

Future interface:

``cancel()``

	Method return value does not relate to state of execution
	of async operation. Communicating cancellation to executors
	of async operations may be too restrictive for some
	implementations and can cause unwanted blocking. Instead
	cancel method returns True when future is not yet completed
	and cancelled state was successfully set (similarly to
	`Promise.try_failure()`). Using `Promise.is_cancelled()`
	executor of async operation can then periodically check
	whether future's result is still expected.

``cancelled()``

	Method replaced with `is_cancelled` property

``running()``

	Method removed as too restrictive for some implementations,
	not useful, and encouraging bad design.

``done()``

	Method replaced with `is_completed` property

``exception()``

	Method does not raise `CancelledError` but returns it instead
	to unify the error handling logic.

``set_running_or_notify_cancel()``
``set_result()``
``set_exception()``

	Methods for future completion removed in favour of using `Promise`.

Module functions:

``wait()``
``as_completed()``

	Functions removed to encourage use of future composition.
	`Future.result()` and `Future.exception()` are only ways
	to drop out of `Future` monad.

References
==========