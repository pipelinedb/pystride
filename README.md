# pystride

[![CircleCI](https://circleci.com/gh/pipelinedb/pystride.svg?style=shield)](https://circleci.com/gh/pipelinedb/pystride)
[![PyPI version](https://badge.fury.io/py/stride.svg)](https://badge.fury.io/py/stride)

Welcome to the Python client for Stride.

```sh
pip install stride
```

Then in your project:

```python
from stride import Stride

stride = new Stride('apikey')
stride.post('/collect/mystream', {'bojack': 'horseman'})
# StrideResponse(status_code=200, data=None)
```

There are a few main methods: `get`, `post`, `put`, `delete`, `subscribe`. All methods return a `StrideResponse` object which has two attributes: 
- `status_code` - the HTTP status code returned by the server 
- `data` - the JSON object returned by the server, or `None` is response was empty

## get()

* `url` - endpoint to `GET` from

*Note: the endpoints passed to the Stride client must not include the API version, i.e. just `/collect`*

```python
stride.get('/collect')
# StrideResponse(status_code=200, data=['clicks', 'app_events', 'web_logs'])
```

## post()

* `url` - endpoint to `POST` to
* `data` - data to post to server

```python
process = {
  'query': 'SELECT count(*) FROM app_events',
  'action': {'type': 'MATERIALIZE'}
}
stride.post('/process/myproc', process)
# StrideResponse(status_code=200, data=None)
```

## put()

* `url` - endpoint to `PUT` to
* `data` - data to post to server

```python
analyze = {
  'query': 'SELECT * FROM myproc',
}
stride.put('/analyze/myanalyze', analyze)
# StrideResponse(status_code=200, data=None)
```

## delete()

* `url` - endpoint to `DELETE`

```python
stride.delete('/process/myproc')
# StrideResponse(status_code=200, data=None)
```

## subscribe()

Due to the streaming nature of `subscribe()`, its usage is a little different compared to other methods. The `data` attribute of the response object is not a `dict` but instead is a `generator` function which will `yield` new events as they arrive.

* `url` - endpoint to subscribe to, this should not include the `/subscribe` suffix e.g. `/collect/mystream`

```python
res = stride.subscribe('/collect/app_events')
# StrideResponse(status_code=200, data=<function events at 0x7f73045d1c08>)

for event in res.data():
  do_something(event)
```
