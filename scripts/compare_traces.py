"""Alternating, sequential before/after API requests with real exported OTel spans."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import statistics
import time
from urllib.request import Request, urlopen

PHASES = ['POST /backtest/run','backtest.data','backtest.engine','backtest.metrics',
          'backtest.bootstrap','backtest.permutation','research.persist','research.transaction']
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pairs',type=int,default=20)
    parser.add_argument('--steps',type=int,default=20000)
    parser.add_argument('--comparison',choices=['adapter','stats'],default='adapter')
    parser.add_argument('--service-prefix',default='novaquant')
    args = parser.parse_args()
    if args.pairs < 1 or not 50 <= args.steps <= 20000:
        parser.error('pairs must be positive; steps must be 50..20000')
    urls = {'before':'http://127.0.0.1:8002','after':'http://127.0.0.1:8003'}
    for variant, url in urls.items():
        for attempt in range(60):
            try:
                with urlopen(url+'/health',timeout=2) as response:
                    if json.load(response).get('status') == 'ok':
                        break
            except Exception:
                pass
            time.sleep(1)
        else:
            raise RuntimeError(variant+' API did not become ready')
    records = []
    expected = None
    payload = {'engine':'cpp','data_source':'gbm','steps':args.steps,'seed':42}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = ROOT/'artifacts/telemetry'/('comparison-'+stamp)
    destination.mkdir(parents=True)
    def request(variant, pair, warmup=False):
        nonlocal expected
        trace_id = secrets.token_hex(16)
        request = Request(urls[variant]+'/backtest/run',data=json.dumps(payload).encode(),headers={
            'Content-Type':'application/json','traceparent':f'00-{trace_id}-{secrets.token_hex(8)}-01'})
        start = time.perf_counter()
        with urlopen(request,timeout=120) as response:
            raw = response.read()
        elapsed = (time.perf_counter()-start)*1000
        out = json.loads(raw)
        canonical = {k:out[k] for k in ['symbol','equity','trades','metrics','stats','evaluation','dataset_id']}
        digest = hashlib.sha256(json.dumps(canonical,sort_keys=True).encode()).hexdigest()
        if expected is None: expected = digest
        if digest != expected: raise AssertionError('Complete research outputs differ')
        if not warmup:
            records.append({'variant':variant,'pair':pair,'trace_id':trace_id,'run_id':out['run_id'],
                'engine_version':out['engine_version'],'client_ms':elapsed})
    for _ in range(2):
        for variant in urls: request(variant,-1,True)
    for pair in range(args.pairs):
        for variant in (['before','after'] if pair%2==0 else ['after','before']):
            request(variant,pair)
        print(f'Completed pair {pair+1}/{args.pairs}',flush=True)
    (destination/'requests.json').write_text(json.dumps(records,indent=2))
    # Fetch traces after timing all requests, avoiding query traffic between pairs.
    for record in records:
        trace = None
        for _ in range(20):
            try:
                with urlopen('http://127.0.0.1:16686/api/traces/'+record['trace_id'],timeout=5) as response:
                    data = json.load(response)
                if data.get('data'):
                    candidate = data['data'][0]
                    names = {s['operationName'] for s in candidate['spans']}
                    if set(PHASES).issubset(names):
                        trace = candidate
                        break
            except Exception:
                pass
            time.sleep(1)
        if trace is None: raise RuntimeError('Missing trace '+record['trace_id'])
        spans = trace['spans']
        service = args.service_prefix+'-'+record['variant']
        if not any(p['serviceName']==service for p in trace['processes'].values()):
            raise AssertionError('Trace exported by wrong comparison service')
        durations = {s['operationName']:s['duration']/1000 for s in spans if s['operationName'] in PHASES}
        if set(durations) != set(PHASES): raise AssertionError('Missing required phases')
        record['span_ms'] = durations
        (destination/(record['trace_id']+'.json')).write_text(json.dumps(trace,indent=2))
    versions = {variant:{r['engine_version'] for r in records if r['variant']==variant} for variant in urls}
    assert len(versions['before'])==len(versions['after'])==1
    assert versions['before'] != versions['after']
    summary = {}
    for phase in ['client_ms']+PHASES:
        values = {v:[r['client_ms'] if phase=='client_ms' else r['span_ms'][phase] for r in records if r['variant']==v] for v in urls}
        medians = {v:statistics.median(samples) for v,samples in values.items()}
        summary[phase] = {'median_ms':medians,'reduction_pct':100*(1-medians['after']/medians['before']),
                          'range_ms':{v:[min(x),max(x)] for v,x in values.items()}}
    report = {'timestamp_utc':stamp,'pairs':args.pairs,'payload':payload,'warmups_per_variant':2,
              'method':'Alternating sequential requests; one outstanding request; same Docker image code/kernel, local shared PostgreSQL, both traced; Jaeger queries after timing.',
              'scope':args.comparison+' before/after; same C++ engine. Spans include tracing overhead; child durations overlap parent durations.',
              'output_sha256':expected,'summary':summary,'requests':records,
              'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['scripts/trace_comparison_app.py','scripts/compare_traces.py','backend/backtest/native.py','scripts/baselines/native_before_buffers.py','backend/backtest/stats.py','scripts/baselines/stats_before_resampling.py','scripts/stats_comparison_app.py']}}
    (destination/'comparison.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(summary,indent=2))
    print('All results matched and traces were verified. Saved '+str(destination))
    print('Before: http://localhost:16686/trace/'+next(r['trace_id'] for r in records if r['variant']=='before'))
    print('After: http://localhost:16686/trace/'+next(r['trace_id'] for r in records if r['variant']=='after'))


if __name__=='__main__': main()
