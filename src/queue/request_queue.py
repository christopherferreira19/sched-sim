import simpy
import logging
import collections


class RequestQueue(object):

    def __init__(self, env, size):
        self.env = env
        # If size = -1, assume infinite
        self.size = size


class FIFORequestQueue(RequestQueue):

    def __init__(self, env, size, dequeue_time):
        super(FIFORequestQueue, self).__init__(env, size)
        # TODO: If size is finite
        self.q = collections.deque()
        self.dequeue_time = dequeue_time

        # Assuming queue can only be accessed once at a time
        self.resource = simpy.Resource(env, capacity=1)

    def enqueue(self, request):
        self.q.append(request)

    def enqueue_front(self, request):
        self.q.appendleft(request)

    def empty(self):
        return len(self.q) == 0

    def dequeue(self):
        if len(self.q) == 0:
            return None
        return self.q.popleft()


class PerFlowRequestQueue(RequestQueue):

    def __init__(self, env, size):
        super(PerFlowRequestQueue, self).__init__(env, size)
        # TODO: If size is finite
        self.q = collections.deque()
        self.expected_length = 0

    def enqueue(self, request):
        self.q.append(request)
        self.expected_length += request.expected_length

    def enqueue_front(self, request):
        self.q.appendleft(request)
        self.expected_length += request.expected_length

    def empty(self):
        return len(self.q) == 0

    def dequeue(self):
        if len(self.q) == 0:
            return None

        request = self.q.popleft()
        self.expected_length -= request.expected_length
        return request


class FlowQueues(RequestQueue):

    def __init__(self, env, size, dequeue_time, flow_config):
        super(FlowQueues, self).__init__(env, size)
        # TODO: If size is finite
        self.q = []
        for flow in range(len(flow_config)):
            self.q.append(PerFlowRequestQueue(env, size))
        self.flow_config = flow_config
        self.dequeue_time = dequeue_time

        # Assume queues can only be accessed once at a time
        # FIXME Maybe change this to per queue lock
        self.resource = simpy.Resource(env, capacity=1)

    def enqueue(self, request):
        self.q[request.flow_id].enqueue(request)

    def enqueue_front(self, request):
        self.q[request.flow_id].enqueue_front(request)

    def empty(self):
        # Check whether all the queues are empty
        for flow in self.q:
            if not flow.empty():
                return False

        return True

    def dequeue(self):
        if self.empty():
            return None

        flow = self.get_max_queue()
        return self.q[flow].dequeue()

    def get_max_queue(self):
        # Get the key of the flow with the longest queue
        max_value = 0
        max_index = 0
        for flow in range(len(self.q)):
            if self.q[flow].expected_length >= max_value:
                max_index = flow
                max_value = self.q[flow].expected_length
        logging.debug("Dequeuing request from flow {} with length {}".
                      format(max_index, max_value))
        return max_index


class SLOFlowQueues(RequestQueue):

    def get_max_queue(self):
        # Get the key of the flow which is closest to violating the SLO
        min_value = self.flow_config[0] - self.q[0].expected_length
        min_index = 0

        for flow in range(len(self.q)):
            cur_value = (self.flow_config[flow]['slo'] -
                         self.q[flow].expected_length)
            if cur_value <= min_value:
                min_index = flow
                min_value = cur_value
        logging.debug("Dequeuing request from flow {} with slack {}".
                      format(min_index, min_value))
        return min_index
