from datetime import datetime
import cStringIO
import gzip
import inspect
import json
import pytest
import responses

from stride import Stride, __version__


def check_request(request):
  assert request.headers['Content-Type'] == 'application/json'
  assert request.headers['Authorization'] == 'Basic a2V5Og=='
  assert request.headers['User-Agent'] == (
      'pystride (version: %s)' % __version__)


@pytest.fixture
def rsps():
  def subscribe(request):
    check_request(request)

    events = [{
        '$id': i,
        '$timestamp': str(datetime.utcnow())
    } for i in xrange(100)]
    headers = {'Content-Type': 'application/json'}
    data = '\r\n'.join(json.dumps(e) for e in events)
    return (200, headers, data)

  def post(request):
    check_request(request)

    headers = {'Content-Type': 'application/json'}
    return (200, headers, request.body)

  rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
  rsps.add_callback(
      responses.GET,
      'https://api.stride.io/v1/collect/stream/subscribe',
      callback=subscribe,
      content_type='application/json')
  rsps.add_callback(
      responses.POST,
      'https://api.stride.io/v1/process/p1',
      callback=post,
      content_type='application/json')
  rsps.add_callback(
      responses.PUT,
      'https://api.stride.io/v1/process/p1',
      callback=post,
      content_type='application/json')
  return rsps


def test_subscribe(rsps):
  s = Stride('key')

  with rsps:
    r = s.subscribe('/collect/stream')
    assert r.status_code == 200
    events = r.data()
    assert inspect.isgenerator(events)

    i = 0
    for i, event in enumerate(events):
      assert event['$id'] == i

    assert i == 99


def test_subscribe_sample(rsps):
  s = Stride('key')

  def callback(request):
    check_request(request)

    events = [{'url': request.url}]
    headers = {'Content-Type': 'application/json'}
    data = '\r\n'.join(json.dumps(e) for e in events)
    return (200, headers, data)

  with rsps:
    rsps.add_callback(
        responses.GET,
        'https://api.stride.io/v1/collect/subscribe_stream/subscribe',
        callback=callback,
        content_type='application/json')

    r = s.subscribe('/collect/subscribe_stream', sample=42)
    assert r.status_code == 200
    events = r.data()
    assert inspect.isgenerator(events)

    event = list(events)[0]
    assert event['url'] == 'https://api.stride.io/v1/collect/subscribe_stream/subscribe?sample=42'


def test_request(rsps):
  s = Stride('key')

  with rsps:
    r = s.post('/process/p1', json={'query': 'SELECT 1'})
    assert r.status_code == 200
    assert r.data == {'query': 'SELECT 1'}

    r = s.put('/process/p1', json={'ttl': {'duration': '1 day', 'column': 'minute'}})
    assert r.status_code == 200
    assert r.data == {'ttl': {'duration': '1 day', 'column': 'minute'}}


def test_endpoint(rsps):
  s = Stride('key', endpoint='http://stride.io/another/endpoint')

  def post(request):
    if 'Content-Encoding' in request.headers and request.headers['Content-Encoding'] == 'gzip':
      tmp = cStringIO.StringIO(request.body)
      with gzip.GzipFile(mode='rb', fileobj=tmp) as gz:
        request.body = gz.read()
    return 200, {}, request.body

  with rsps:
    rsps.add_callback(
        responses.POST,
        'http://stride.io/another/endpoint/collect/stream',
        callback=post,
        content_type='application/json')
    r = s.post('/collect/stream', json={'x': 42})

    assert r.status_code == 200
    assert r.data == {'x': 42}


def test_malformed_json(rsps):
  s = Stride('key', endpoint='http://stride.io/v1')

  with rsps:
    rsps.add_callback(
        responses.POST,
        'http://stride.io/v1/collect/stream',
        callback=lambda r: (502, {}, '{not valid json'),
        content_type='application/json')
    r = s.post('/collect/stream', json={'x': 42})

    assert r.status_code == 502
    assert r.data == {'error': 'response contained malformed json'}
