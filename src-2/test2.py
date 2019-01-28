import gevent
from gevent.event import AsyncResult

N = 5
inputs = [AsyncResult() for _ in range(N)]
outputs = [AsyncResult() for _ in range(N)]

def wait_for_inputs():
    # wait for the inputs to arruve
    while True:
        s = 0
        for i in inputs:
            if i.ready():
                s += 1 
        if s == N:
            break
        else:
            gevent.sleep()

    _inputs = [i.get() for i in inputs]

    for i in range(len(_inputs)):
        outputs[i].set(_inputs[i])


def give_inputs():
    for i in range(N):
        inputs[i].set('hi'+str(i))

    gevent.wait(outputs)

    for o in outputs:
        print(o.get())

g1 = gevent.spawn(wait_for_inputs)
g2 = gevent.spawn(give_inputs)

gevent.joinall([g1, g2])
