from collections import defaultdict
from datetime import datetime
import cStringIO
import gzip
import json
import os
import pytest
import responses
import time

from stride import Collector, set_id, set_timestamp, __version__


def check_request(request):
  assert request.headers['Content-Type'] == 'application/json'
  assert request.headers['Authorization'] == 'Basic a2V5Og=='
  assert request.headers['User-Agent'] == (
      'pystride (version: %s)' % __version__)


@pytest.fixture
def rsps():
  rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
  rsps.requests = []

  def collect(request):
    check_request(request)

    if 'Content-Encoding' in request.headers and request.headers['Content-Encoding'] == 'gzip':
      tmp = cStringIO.StringIO(request.body)
      with gzip.GzipFile(mode='rb', fileobj=tmp) as gz:
        request.body = gz.read()

    stream = request.url.split('/')[-1]
    rsps.requests.append((stream, json.loads(request.body)))
    headers = {'Content-Type': 'application/json'}
    return (200, headers, '')

  rsps.add_callback(
      responses.POST,
      'https://api.stride.io/v1/collect/stream0',
      callback=collect,
      content_type='application/json')

  rsps.add_callback(
      responses.POST,
      'https://api.stride.io/v1/collect/stream1',
      callback=collect,
      content_type='application/json')

  return rsps


def test_set_funcs():
  event = {}
  ts = datetime.utcnow()

  set_id(event, 'lolcat')
  set_timestamp(event, ts)

  assert event['$id'] == 'lolcat'
  assert event['$timestamp'] == str(ts)


def test_collector(rsps):
  c = Collector('key', batch_size=10, flush_interval=0.25)
  c.start()

  with rsps:
    assert len(rsps.requests) == 0

    # Test batch_size
    c.collect('stream0', [{'$id': i} for i in xrange(5)])
    c.collect('stream1', [{'$id': i} for i in xrange(10)])
    c.collect('stream0', [{'$id': i} for i in xrange(10)])

    # We sleep a bit for thread to flush, but less than flush interval
    time.sleep(0.1)

    assert len(rsps.requests) == 3

    events = defaultdict(list)
    for stream, data in rsps.requests:
      events[stream].extend(data)

    assert len(events.get('stream0', [])) == 15
    assert len(events.get('stream1', [])) == 10

    rsps.requests = []

    # Test flush interval
    c.collect('stream0', [{'$id': i} for i in xrange(5)])

    time.sleep(0.1)
    assert len(rsps.requests) == 0
    time.sleep(0.25)
    assert len(rsps.requests) == 1
    req0 = rsps.requests[0]
    assert len(req0) == 2

    events = defaultdict(list)
    for stream, data in rsps.requests:
      events[stream].extend(data)

    assert len(events.get('stream0', [])) == 5

    rsps.requests = []

    # Test drain
    c.collect('stream0', [{'$id': i} for i in xrange(5)])
    c.stop()
    assert len(rsps.requests) == 1
    stream, events = rsps.requests[0]
    assert stream == 'stream0'
    assert len(events) == 5
