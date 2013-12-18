rxpython
========

Composable alternative for _concurrent.features_ module for reactive programming in Python.

Promises and Futures basics
---------------------------

<pre>
<code>
def make_request(request, promise):
    sock.send(request)
    return sock.receive_all() # blocks

def request_async(request):
    p = Promise()
    thread_pool.submit(lambda: p.complete(make_request, request))
    return p.future

>> f = request_async("echo")
>> f.on_success(lambda resp: print("response: " + resp))
>> f.on_failure(lambda ex: print("request failed"))
</code>
</pre>

Futures composability
---------------------

Future.map - transforming the result of future

<pre>
<code>
>> f = compute_async(lambda: factorial(100))
>> fsqrt = f.map(math.sqrt)
>> fsqrt.on_success(lambda res: print("sqrt(factorial(100)) = " + resp))
</code>
</pre>

Future.then - chaining futures one after another

<pre>
<code>
def authenticate_and_make_request(request):
    fauth = authenticate_async()
    frequest = fauth.then(lambda: request_async('echo'))
    return frequest

>> frequest = authenticate_and_make_request('echo')
>> frequest.on_success(lambda resp: print("auth and request successful: " + resp))
>> frequest.on_failure(lambda ex: print("auth or request failed"))
</code>
</pre>

Future.all - combining results of multiple futures (transforms list of futures to future of result list)

<pre>
<code>
def squares(values):
    futures = map(sqr_async, values]
    return Future.all(futures)

>> squares(range(5)).on_success(lambda results: print(results))
[0, 1, 4, 9, 16]
</code>
</pre>

Future.first - contains result of first completed future

<pre>
<code>
def hedged_request(urls):
    futures = map(request_async, urls]
    return Future.first(futures)

>> fresponse = hedged_request([ip1, ip2, ip3])
</code>
</pre>