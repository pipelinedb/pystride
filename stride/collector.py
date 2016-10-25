from collections import defaultdict
from datetime import datetime
import logging
import Queue
from threading import Thread
import time

from stride.client import api_endpoint, Stride
from stride.errors import StrideError

timestamp_key = '$timestamp'
id_key = '$id'

log = logging.getLogger(__name__)


def set_timestamp(event, timestamp=None):
    if not timestamp:
        timestamp = datetime.utcnow()
    if not isinstance(timestamp, datetime):
        raise StrideError("timestamp value must be of type datetime")
    event[timestamp_key] = str(timestamp)


def set_id(event, _id=None):
    if _id is None:
        raise StrideError("id must not be null")
    event[id_key] = _id


class Collector(object):
    _collect_kwargs = {'block', 'timeout'}

    def __init__(self, api_key, timeout=5, flush_interval=0.25,
                 batch_size=1000, endpoint=api_endpoint):
        self._timeout = timeout
        self._flush_interval = flush_interval
        self._batch_size = batch_size
        self._endpoint = endpoint

        self._client = Stride(api_key, timeout=timeout, endpoint=endpoint)
        self._thread = None
        self._queue = Queue.Queue(max_size=batch_size)
        self._stopped = True

    def _run(self):
        num_events = 0
        events = defaultdict(list)

        def flush():
            try:
                r = self._stride.post('/collect', events)
                if r.status_code != 200:
                    log.error('collect request failed',
                              extra={'status_code': r.status_code,
                                     'data': r.data,
                                     'num_events': num_events})
            except Exception:
                log.exception('collect request failed',
                              extra={'num_events': num_events})

        start_time = time.time()
        while not self._stopped:
            cur_time = time.time()

            # Flush interval has elapsed and we have events to flush?
            if num_events and cur_time - start_time > self._timeout:
                flush()
                events.clear()
                num_events = 0

            # Determine time to wait for new events
            if not num_events:
                timeout = None
            else:
                timeout = max(self._timeout - (cur_time - start_time), 0)

            stream, events = self._queue.get(True, timeout)

            # If we're seeing the first event(s), reset start_time
            if not num_events:
                start_time = time.time()

            num_events += len(events)
            events[stream].extend(events)

    def start(self):
        if self._thread is not None:
            raise StrideError('collector is already running')

        self._stopped = False
        self._thread = Thread(target=self._run)
        self._thread.start()

    def stop(self):
        self._stopped = True
        self._thread.join()
        self._thread = None

    def collect(self, stream, *events, **kwargs):
        if self._stopped or self._thread is None:
            raise StrideError('collector is not running')

        kw_keys = set(kwargs)
        if not kw_keys.issubset(Collector._collect_kwargs):
            invalid_keys = kw_keys - Collector._collect_kwargs
            raise StrideError('invalid keyword argument %s',
                              invalid_keys.pop())

        try:
            self._queue.put(
                (stream, events),
                block=kwargs.get('block', True),
                timeout=kwargs.get('timeout', self._timeout)
            )
        except Queue.Full:
            raise StrideError('queue is full, collector might be backlogged')
