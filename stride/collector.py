from collections import defaultdict
from datetime import datetime
import logging
import Queue
from threading import Thread
import time

from stride.client import Stride, DEFAULT_API_ENDPOINT
from stride.errors import Error

timestamp_key = '$timestamp'
id_key = '$id'

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(threadName)s]: %(message)s")
log = logging.getLogger(__name__)


def set_timestamp(event, timestamp=None):
  if not timestamp:
    timestamp = datetime.utcnow()
  if not isinstance(timestamp, datetime):
    raise Error('timestamp value must be of type datetime')
  event[timestamp_key] = str(timestamp)


def set_id(event, _id=None):
  if _id is None:
    raise Error('id must not be null')
  event[id_key] = _id


class Collector(object):
  '''
    Collector is an asynchronous batching collector for the Stride API
    '''
  _collect_kwargs = {'block', 'timeout'}

  def __init__(self, api_key, endpoint=DEFAULT_API_ENDPOINT, timeout=5,
               concurrency=2, flush_interval=0.25, batch_size=1000):

    self._concurrency = concurrency
    self._timeout = timeout
    self._flush_interval = flush_interval
    self._batch_size = batch_size
    self._api_key = api_key
    self._thread = None
    self._queue = Queue.Queue(maxsize=batch_size)
    self._stopped = True
    self._threads = []
    self._endpoint = endpoint

  def _run(self, client):
    num_events = 0
    buffered_events = defaultdict(list)

    def flush():
      try:
        count = 0
        for stream, events in buffered_events.iteritems():
          r = client.post('/collect/%s' % stream, events)
          if r.status_code != 200:
            log.error(
                'collect request failed',
                extra={
                    'status_code': r.status_code,
                    'data': r.data,
                    'num_events': num_events
                })
          count += len(events)
          log.info('flushed %d events', count)
      except Exception, e:
        log.exception(
            'collect request failed', extra={'num_events': num_events})

    start_time = time.time()
    while not self._stopped:
      cur_time = time.time()

      # Flush interval has elapsed and we have events to flush?
      if num_events:
        if (num_events >= self._batch_size or
            cur_time - start_time > self._flush_interval):
          flush()
          buffered_events.clear()
          num_events = 0

      # Determine time to wait for new events
      timeout = max(self._flush_interval - (cur_time - start_time), 0)
      try:
        stream, events = self._queue.get(True, timeout)
      except Queue.Empty:
        continue

      # If we're seeing the first event(s), reset start_time
      if not num_events:
        start_time = time.time()

      num_events += len(events)
      buffered_events[stream].extend(events)

    # Drain
    while True:
      try:
        stream, events = self._queue.get_nowait()
        buffered_events[stream].extend(events)
      except Queue.Empty:
        flush()
        break

  def start(self):
    if len(self._threads):
      raise Error('collector is already running')

    self._stopped = False
    self._threads = []

    for n in range(self._concurrency):
      client = Stride(self._api_key, timeout=self._timeout, endpoint=self._endpoint)
      t = Thread(target=self._run, args=(client,))
      t.daemon = True
      t.start()
      self._threads.append(t)

  def stop(self):
    self._stopped = True
    map(lambda t: t.join(), self._threads)
    self._threads = []

  def collect(self, stream, events, **kwargs):
    if self._stopped or not self._threads:
      raise Error('collector is not running')

    kw_keys = set(kwargs)
    if not kw_keys.issubset(Collector._collect_kwargs):
      invalid_keys = kw_keys - Collector._collect_kwargs
      raise Error('invalid keyword argument %s', invalid_keys.pop())

    if not isinstance(events, list):
      events = [events]
    try:
      self._queue.put(
          (stream, events),
          block=kwargs.get('block', True),
          timeout=kwargs.get('timeout', self._timeout))
    except Queue.Full:
      raise Error('queue is full, collector might be backlogged')
