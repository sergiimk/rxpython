TODO
====

* Lightweight successful/failed futures
* asyncio integration
* Observables
* Traceability
* Debugging output stream
* Graphviz task graphs

Interface differences
-----------

Executor interface reduced to:

<pre>
<code>
class Executor:
    def submit(fn, *args, **kwargs) -> Future
</code>
</pre>

Future interface:

 - **cancel()** method return value does not relate to state of execution of async operation.
Communicating cancellation to executors of async operations may be too restrictive for some
implementations and can cause unwanted blocking. Instead cancel method returns True when
future is not completed and cancelled state was successfully set (similar to *Promise.try_failure()*).
Using *Promise.is_cancelled()* executor of async operation can then periodically check whether future's
result is still required.

 - **cancelled()** method replaced with *is_cancelled* property
 - **running()** method removed as too restrictive for some implementations and not very useful
 - **done()** method replaced with *is_completed* property
 - **exception()** method does not raise *CancelledError* but returns it instead to unify the error handling
 - all methods for future completion like **set_running_or_notify_cancel()**,
**set_result()** and **set_exception()** are replaced by *Promise* class

Module functions:
 - **wait()** and **as_completed()** functions removed to encourage use of future composition.
*Future.result()* and *Future.exception()* are only ways to break out of Future monad.
