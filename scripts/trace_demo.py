"""Send two real API requests, then verify their exported OpenTelemetry traces in Jaeger."""
import argparse
import json
import math
from pathlib import Path
import secrets
import time
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', default='http://127.0.0.1:8001')
    parser.add_argument('--jaeger', default='http://127.0.0.1:16686')
    parser.add_argument('--steps', type=int, default=1000)
    args = parser.parse_args()
    records = []
    outputs = []
    for engine in ['python','cpp']:
        trace_id = secrets.token_hex(16)
        body = json.dumps({'engine':engine,'data_source':'gbm','steps':args.steps,'seed':42}).encode()
        request = Request(args.api+'/backtest/run', data=body, headers={
            'Content-Type':'application/json',
            'traceparent':f'00-{trace_id}-{secrets.token_hex(8)}-01'})
        start = time.perf_counter()
        with urlopen(request, timeout=120) as response:
            raw = response.read()
        elapsed_ms = (time.perf_counter()-start)*1000
        output = json.loads(raw)
        outputs.append(output)
        trace = None
        for attempt in range(20):
            try:
                with urlopen(args.jaeger+'/api/traces/'+trace_id, timeout=5) as response:
                    data = json.load(response)
                if data.get('data'):
                    trace = data['data'][0]
                    break
            except Exception:
                pass
            time.sleep(1)
        if trace is None:
            raise RuntimeError(f'Trace {trace_id} was not found in Jaeger; ensure telemetry is enabled.')
        phases = [{'name':s['operationName'],'duration_ms':s['duration']/1000,
                   'span_id':s['spanID'],'references':s.get('references',[])}
                  for s in sorted(trace['spans'],key=lambda s:s['startTime'])]
        names = {s['name'] for s in phases}
        required = {'POST /backtest/run','backtest.data','backtest.engine','backtest.metrics',
                    'backtest.bootstrap','backtest.permutation','research.persist','research.transaction'}
        assert required <= names, (required-names)
        record = {'engine':engine,'steps':args.steps,'run_id':output['run_id'],
                  'trace_id':trace_id,'client_response_ms':elapsed_ms,'spans':phases}
        records.append(record)
        print(f'{engine}: client response {elapsed_ms:.1f} ms; trace {args.jaeger}/trace/{trace_id}')
        for phase in phases:
            print(f"  {phase['name']}: {phase['duration_ms']:.3f} ms")
    assert len(outputs[0]['equity']) == len(outputs[1]['equity'])
    assert all(math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-8) for a,b in zip(outputs[0]['equity'],outputs[1]['equity']))
    assert outputs[0]['trades'] == outputs[1]['trades']
    destination = Path(__file__).resolve().parents[1]/'artifacts/telemetry'
    destination.mkdir(exist_ok=True)
    (destination/'demo.json').write_text(json.dumps({'note':'Two traced diagnostic requests, not a statistically controlled speed benchmark. Parent spans include child time; do not add them together.','requests':records},indent=2))
    print('Both traces exported, required phases found, and Python/C++ outputs matched.')


if __name__ == '__main__':
    main()
