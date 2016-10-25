import json
import re
import requests
from requests.auth import HTTPBasicAuth

from stride.errors import StrideError
from stride.version import VERSION

api_endpoint = 'https://api.stride.io/v1'
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
    'put': [
        re.compile(r'^/analyze/[A-Za-z][A-Za-z0-9_]*$')
    ],
    'delete': [
        re.compile(r'^/(collect|process|analyze)/[A-Za-z][A-Za-z0-9_]*$')
    ],
    'subscribe': [
        re.compile(r'^/(collect|process)/[A-Za-z][A-Za-z0-9_]*$')
    ]
}


def check_path(method, path):
    for regex in valid_paths[method]:
        if regex.match(path):
            return
    raise StrideError('path "%s" is not valid for method "%s"' %
                      (path, method))


class StrideResponse(object):

    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.data = data

        def ok(self):
            return self.status_code == 200 or self.status_code == 201


class Stride(object):
    '''
    Stride is the wrapper for the Stride API client
    '''

    def __init__(self, api_key, timeout=5, endpoint=api_endpoint):
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

    def _make_request(self, method, path, data=None):
        check_path(method, path)

        kwargs = self._get_request_kwargs()
        if data:
            kwargs['json'] = data

        fn = getattr(requests, method)
        r = fn('%s%s' % (self._endpoint, path), **kwargs)
        data = r.json() if r.text else None
        return StrideResponse(r.status_code, data=data)

    def get(self, path):
        return self._make_request('get', path)

    def post(self, path, data):
        return self._make_request('post', path, data=data)

    def put(self, path, data):
        return self._make_request('put', path, data=data)

    def delete(self, path):
        return self._make_request('delete', path)

    def subscribe(self, path):
        # TODO(usmanm): Add retry and chunk_size support
        check_path('subscribe', path)

        kwargs = self._get_request_kwargs()
        kwargs['stream'] = True

        r = requests.get('%s%s' % (self._endpoint, path), **kwargs)

        if r.status_code != requests.codes.ok:
            data = r.json() if r.text else None
        else:
            # Create a generator to stream the events
            def events():
                for line in r.iter_lines():
                    line = line.strip()
                    if line:
                        yield json.loads(line)
            data = events

        return StrideResponse(r.status_code, data=data)
