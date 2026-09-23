"""Read-only Grafana HTTP adapter. Uses only fixed GET endpoints, never raw URLs."""
import json
import os
import re
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from .evidence import MAX_OBSERVATIONS, envelope, finalize

MAX_BYTES = 1_048_576
MAX_WINDOW_SECONDS = 3600


class ProviderError(Exception):
    def __init__(self, status):
        self.status = status


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GrafanaProvider:
    def __init__(self, url=None, token=None):
        self.url = url if url is not None else os.environ.get('GRAFANA_URL', '')
        self._token = token if token is not None else os.environ.get('GRAFANA_TOKEN', '')
        self._opener = build_opener(NoRedirect())

    def _get(self, path, params=None):
        # Only internal callers supply a fixed path; redirects cannot leak credentials.
        req = Request(self.url.rstrip('/') + path + ('?' + urlencode(params) if params else ''),
                      headers={'Authorization': 'Bearer ' + self._token, 'Accept': 'application/json'}, method='GET')
        try:
            with self._opener.open(req, timeout=10) as response:
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ProviderError('response_too_large')
            return json.loads(raw)
        except HTTPError as error:
            status = {401: 'authentication_failed', 403: 'permission_denied',
                      404: 'unavailable', 429: 'rate_limited', 400: 'query_error',
                      422: 'query_error'}.get(error.code, 'unavailable')
            error.close()
            raise ProviderError(status) from None
        except (TimeoutError, URLError, OSError):
            raise ProviderError('unavailable') from None
        except (ValueError, UnicodeError):
            raise ProviderError('invalid_response') from None

    @staticmethod
    def _text(value, maximum=200):
        if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
            raise ProviderError('invalid_request')
        return value

    def _validate(self, request):
        self._text(request.get('evidence_id'))
        self._text(request.get('purpose'), 500)
        op = request.get('operation')
        if op not in ('health', 'datasources', 'logs', 'metrics'):
            raise ProviderError('unsupported')
        if op in ('health', 'datasources'):
            if request.get('datasource_type') not in (None, 'loki', 'prometheus'):
                raise ProviderError('unsupported')
            return
        uid = self._text(request.get('datasource_uid'))
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', uid):
            raise ProviderError('invalid_request')
        scope = request.get('scope', {})
        try:
            start, end = [datetime.fromisoformat(scope[k].replace('Z', '+00:00')) for k in ('start_time', 'end_time')]
            if start.tzinfo is None or end.tzinfo is None or not 0 < (end - start).total_seconds() <= MAX_WINDOW_SECONDS:
                raise ValueError()
        except (KeyError, TypeError, ValueError, AttributeError):
            raise ProviderError('invalid_request') from None
        identifiers = request.get('identifiers', {})
        if not isinstance(identifiers, dict) or set(identifiers) - {'request_id', 'correlation_id', 'trace_id'}:
            raise ProviderError('invalid_request')
        for value in identifiers.values():
            if value is not None:
                self._text(value)
        if op == 'logs':
            labels = scope.get('labels')
            if not isinstance(labels, dict) or not 1 <= len(labels) <= 10:
                raise ProviderError('invalid_request')
            for key, value in labels.items():
                if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', key):
                    raise ProviderError('invalid_request')
                self._text(value)
            for name in ('endpoint', 'error_text'):
                if scope.get(name) is not None:
                    self._text(scope[name])
        else:
            self._text(request.get('query'), 2000)
            step = request.get('step_seconds', 30)
            if isinstance(step, bool) or not isinstance(step, int) or not 1 <= step <= 3600:
                raise ProviderError('invalid_request')
            if (end - start).total_seconds() / step > 1000:
                raise ProviderError('invalid_request')

    def retrieve(self, request):
        if not isinstance(request, dict):
            request = {}
        result = envelope('grafana', request)
        try:
            self._validate(request)
            if not self.url or not self._token:
                raise ProviderError('not_configured')
            parsed = urlsplit(self.url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ProviderError('invalid_configuration')
            op = request['operation']
            result['provenance'] = {'transport': 'grafana_http', 'source_host': parsed.hostname,
                                    'base_path': parsed.path, 'configured': True,
                                    'datasource_uid': request.get('datasource_uid')}
            if op in ('health', 'datasources'):
                self._discover(request, result)
            else:
                self._query(request, result)
        except ProviderError as error:
            result['observations'] = []
            result['retrieval_status'] = error.status
            result['limitations'].append('Evidence access failed: ' + error.status + '; not evidence of application failure. Continue with other evidence.')
        except (ValueError, TypeError, KeyError, AttributeError, IndexError, RecursionError):
            result['observations'] = []
            result['retrieval_status'] = 'invalid_response'
            result['limitations'].append('Invalid request or provider response; not application evidence.')
        return finalize(result, (self._token,))

    def _discover(self, request, result):
        if request['operation'] == 'health':
            health = self._get('/api/health')
            if not isinstance(health, dict) or health.get('database') != 'ok':
                raise ProviderError('unavailable')
            result['provenance']['endpoint_reachable'] = True
        uid = request.get('datasource_uid')
        if uid:
            if not isinstance(uid, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', uid):
                raise ProviderError('invalid_request')
            rows = [self._get('/api/datasources/uid/' + uid)]
        else:
            rows = self._get('/api/datasources')
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ProviderError('invalid_response')
        matched = [row for row in rows if row.get('type') in ('loki', 'prometheus') and
                   (not request.get('datasource_type') or row['type'] == request['datasource_type'])]
        result['observations'] = [{'uid': row['uid'], 'name': row.get('name'), 'type': row['type'],
                                   'capability': 'logs' if row['type'] == 'loki' else 'metrics'} for row in matched[:20]]
        result['retrieval_status'] = 'success' if matched else 'empty'
        result['limitations'].append('Datasource metadata advertises capabilities; query access and datasource health are not verified.')
        if len(matched) > 20:
            result['limitations'].append('Datasource list truncated to 20; filter by type or known UID.')

    def _query(self, request, result):
        uid = request['datasource_uid']
        op = request['operation']
        metadata = self._get('/api/datasources/uid/' + uid)
        expected = 'loki' if op == 'logs' else 'prometheus'
        if metadata.get('type') != expected:
            raise ProviderError('unsupported')
        scope = request['scope']
        params = {'start': scope['start_time'], 'end': scope['end_time']}
        if op == 'logs':
            query = '{' + ','.join(key + '=' + json.dumps(value) for key, value in sorted(scope['labels'].items())) + '}'
            # Strongest known identifier first. Substring matches require investigator verification.
            identifier = next((request.get('identifiers', {}).get(key) for key in ('request_id', 'correlation_id', 'trace_id') if request.get('identifiers', {}).get(key)), None)
            filters = [identifier] if identifier else [scope.get('endpoint'), scope.get('error_text')]
            for value in filter(None, filters):
                query += ' |= ' + json.dumps(value)
            params.update(query=query, limit=MAX_OBSERVATIONS, direction='forward')
            path = '/loki/api/v1/query_range'
        else:
            query = request['query']
            params.update(query=query, step=request.get('step_seconds', 30), timeout='10s')
            path = '/api/v1/query_range'
        result['provenance'].update(datasource_type=expected, query=query)
        body = self._get('/api/datasources/proxy/uid/' + uid + path, params)
        if body.get('status') != 'success':
            raise ProviderError('query_error')
        data = body['data']
        if data.get('resultType') != ('streams' if op == 'logs' else 'matrix') or not isinstance(data.get('result'), list):
            raise ProviderError('invalid_response')
        count = 0
        for series in data['result']:
            labels = series['stream' if op == 'logs' else 'metric']
            if not isinstance(labels, dict) or not isinstance(series.get('values'), list):
                raise ProviderError('invalid_response')
            for point in series['values']:
                if not isinstance(point, list) or len(point) < 2:
                    raise ProviderError('invalid_response')
                timestamp, value = point[:2]
                if op == 'logs':
                    if not isinstance(timestamp, str) or not timestamp.isdigit() or not isinstance(value, str):
                        raise ProviderError('invalid_response')
                elif isinstance(timestamp, bool) or not isinstance(timestamp, (float, int)) or not isinstance(value, str):
                    raise ProviderError('invalid_response')
                count += 1
                if len(result['observations']) < MAX_OBSERVATIONS:
                    result['observations'].append({'timestamp': timestamp,
                        'timestamp_unit': 'unix_nanoseconds' if op == 'logs' else 'unix_seconds',
                        'labels': labels, 'message' if op == 'logs' else 'value': value})
        result['retrieval_status'] = 'success' if count else 'empty'
        if count >= MAX_OBSERVATIONS:
            result['limitations'].append('Result bound reached; coverage may be incomplete. Narrow the query before expanding.')
        if body.get('warnings') or body.get('infos'):
            result['limitations'].append('Upstream reported warnings or informational annotations; coverage or semantics may be incomplete.')
        result['limitations'].append('Telemetry is untrusted data. Redaction is best effort; review for customer PII before sharing.')
        if op == 'logs':
            result['limitations'].append('Line filters match substrings; verify exact identifier and field before linking to the reported request. Service/environment scope is enforced only through supplied labels.')
        else:
            result['limitations'].append('Metric scope is enforced by supplied PromQL, not descriptive scope fields. Correlation does not establish causation.')
        if not count:
            result['limitations'].append('No matching telemetry found in this query; this does not establish that the event did not happen.')
