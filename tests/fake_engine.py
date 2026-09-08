import json
import sys
import threading
import time
lock=threading.Lock()
threads=[]


def reply(order):
    time.sleep(order.get('delay',0))
    with lock:
        for kind in ('ack','fill'):
            print(json.dumps({**order,'type':kind}),flush=True)


for line in sys.stdin:
    thread=threading.Thread(target=reply,args=(json.loads(line),))
    thread.start();threads.append(thread)
for thread in threads:thread.join()
