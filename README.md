# pystride

[![CircleCI](https://circleci.com/gh/pipelinedb/pystride.svg?style=shield)](https://circleci.com/gh/pipelinedb/pystride)
[![PyPI version](https://badge.fury.io/py/stride.svg)](https://badge.fury.io/py/stride)

Python client for [Stride](https://www.stride.io/docs)

## Install

```sh
pip install stride
```

The library provides two modules:

* `Stride` - a simple wrapper around the [Stride HTTP API](https://www.stride.io/docs)
* `Collector` - an asynchronous collector that batches events and sends them to the server periodically

## Stride

To use `pystride` from your project, you just need to instantiate an instance of the `Stride` class using one of your [API keys](https://www.stride.io/docs#security):

```python
from stride import Stride

stride = new Stride('secret_key')
stride.post('/collect/mystream', {'bojack': 'horseman'})
# Response(status_code=200, data=None)
```

There are only a few main methods: `get`, `post`, `put`, `delete`, `subscribe`. All methods return a `Response` object which has two attributes:

* `status_code` - the HTTP status code returned by the server
* `data` - the JSON object returned by the server, or `None` if response was empty

### get()

* `url` - endpoint to `GET` from

*Note: the endpoints passed to the Stride client must not include the API version, i.e. just `/collect`*

```python
stride.get('/collect')
# Response(status_code=200, data=['clicks', 'app_events', 'web_logs'])
```

### post()

* `url` - endpoint to `POST` to
* `json` - JSON-serializable data to post to server

```python

process = {
  'query': 'SELECT count(*) FROM app_events',
  'action': {'type': 'MATERIALIZE'}
}

stride.post('/process/myproc', process)
# Response(status_code=201, data=None)

stride.post('/collect/app_events', json={'x': 42})
# Response(status_code=200, data=None)
```

### put()

* `url` - endpoint to `PUT` to
* `json` - JSON-serializable data to post to server

```python
analyze = {
  'query': 'SELECT * FROM myproc',
}
stride.put('/analyze/myanalyze', analyze)
# Response(status_code=200, data=None)
```

### delete()

* `url` - endpoint to `DELETE`

```python
stride.delete('/process/myproc')
# Response(status_code=200, data=None)
```

### subscribe()

Due to the streaming nature of `subscribe()`, its usage is a little different compared to other methods. The `data` attribute of the `Response` object is not a `dict` but instead is a `generator` function which will `yield` new events as they arrive.

* `url` - endpoint to subscribe to, this should not include the `/subscribe` suffix e.g. `/collect/mystream`

```python
res = stride.subscribe('/collect/app_events')
# Response(status_code=200, data=<function events at 0x7f73045d1c08>)

for event in res.data():
  do_something(event)
```

`subscribe` also supports server-side sampling if you'd like to bound the number of events per second your client should receive. The following `subscribe` call will receive no more than 100 events per second:

```python
res = stride.subscribe('/collect/app_events', sample=100)
```

## Collector

While you can certainly [collect](https://www.stride.io/docs#collect) events by using the `post` method, you may not always want a blocking call such as `post` in your application. For asynchronous, non-blocking event collection, `pystride` also provides you with the `Collector` class to save you the hassle of writing async boilerplate around `pystride's` `post` method.

Its usage is fairly straightforward:

```python
from stride import Collector

# flush_interval: the max time (in seconds) to wait before sending buffered events to the server, default = 0.25
# batch_size: the max number of events to buffer in memory before flushing, default = 1000
c = Collector('apikey', flush_interval=0.25, batch_size=1000)
c.start()

for i in range(100000):
  c.collect('mystream', {'id': i, 'bojack': 'horseman'})

c.stop()
```
