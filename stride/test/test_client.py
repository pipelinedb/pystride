from datetime import datetime
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


def test_request(rsps):
  s = Stride('key')

  with rsps:
    r = s.post('/process/p1', json={'query': 'SELECT 1'})
    assert r.status_code == 200
    assert r.data == {'query': 'SELECT 1'}

def test_endpoint(rsps):
  s = Stride('key', endpoint='http://stride.io/another/endpoint')

  with rsps:
    rsps.add_callback(
        responses.POST,
        'http://stride.io/another/endpoint/collect/stream',
        callback=lambda r: (200, {}, r.body),
        content_type='application/json')
    r = s.post('/collect/stream', json={'x': 42})

    assert r.status_code == 200
    assert r.data == {'x': 42}