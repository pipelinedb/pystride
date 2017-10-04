from collections import namedtuple
import cStringIO
import gzip
import json as jsonm
import re
import requests
from requests.auth import HTTPBasicAuth

from stride.errors import Error
from stride.version import VERSION

DEFAULT_API_ENDPOINT = 'https://api.stride.io/v1'
valid_paths = {
    'get': [
        re.compile(r'^/(collect|process)(/[A-Za-z][A-Za-z0-9_]*)?$'),
        re.compile(r'^/analyze(/[A-Za-z][A-Za-z0-9_]*(/results)?)?$')
    ],
    'post': [
        re.compile(r'^/(collect|process|analyze)/[A-Za-z][A-Za-z0-9_]*$'),
        re.compile(r'^/(collect|analyze)$'),
        re.compile(r'^/analyze/[A-Za-z][A-Za-z0-9_]*/results$')
    ],
    'put': [re.compile(r'^/(analyze|process)/[A-Za-z][A-Za-z0-9_]*$')],
    'delete':
    [re.compile(r'^/(collect|process|analyze)/[A-Za-z][A-Za-z0-9_]*$')],
    'subscribe': [re.compile(r'^/(collect|process)/[A-Za-z][A-Za-z0-9_]*$')]
}


def check_path(method, path):
  for regex in valid_paths[method]:
    if regex.match(path):
      return
  raise Error('path "%s" is not valid for method "%s"' % (path, method))


Response = namedtuple('Response', ['status_code', 'data'])


class Stride(object):
  '''
    Stride is the wrapper for the Stride API
    '''

  def __init__(self, api_key, endpoint=DEFAULT_API_ENDPOINT, timeout=30):
    self.api_key = api_key
    self._timeout = timeout
    self._endpoint = endpoint

  def _get_request_kwargs(self):
    return {
        'auth': HTTPBasicAuth(self.api_key, ''),
        'headers': {
            'User-Agent': 'pystride (version: %s)' % VERSION,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        'timeout': self._timeout
    }

  def _make_request(self, method, path, json=None):
    check_path(method, path)

    kwargs = self._get_request_kwargs()

    if re.match('^/collect', path):
      # Compress raw events written to /collect endpoint
      tmp = cStringIO.StringIO()
      with gzip.GzipFile(mode='wb', fileobj=tmp) as gz:
        gz.write(jsonm.dumps(json))
      kwargs['data'] = tmp.getvalue()
      kwargs['headers']['Content-Encoding'] = 'gzip'
    elif json:
      kwargs['data'] = jsonm.dumps(json)

    fn = getattr(requests, method)
    r = fn('%s%s' % (self._endpoint, path), **kwargs)
    data = None

    try:
      data = r.json() if r.text else None
    except:
      data = {'error': 'response contained malformed json'}

    return Response(r.status_code, data)

  def get(self, path):
    return self._make_request('get', path)

  def post(self, path, json):
    return self._make_request('post', path, json=json)

  def put(self, path, json):
    return self._make_request('put', path, json=json)

  def delete(self, path):
    return self._make_request('delete', path)

  def subscribe(self, path, sample=None):
    # TODO(usmanm): Add retry and chunk_size support
    check_path('subscribe', path)

    kwargs = self._get_request_kwargs()
    kwargs['stream'] = True
    if sample:
      kwargs['params'] = {'sample': sample}

    r = requests.get('%s%s/subscribe' % (self._endpoint, path), **kwargs)

    if r.status_code != requests.codes.ok:
      data = r.json() if r.text else None
    else:
      # Create a generator to stream the events
      def events():
        for line in r.iter_lines():
          line = line.strip()
          if line:
            yield jsonm.loads(line)

      data = events

    return Response(r.status_code, data)
