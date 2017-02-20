#!/usr/bin/env python

import os
import sys
import json
import tempfile
import subprocess

OUTPUT_DIR = "../out/"


def main():
    # Set the simulation parameters
    iterations = 10
    core_count = [1, 10]
    time_slices = [0.0]
    host_types = ["global"]
    deq_costs = [0.0]

    config_jsons = [{"1": {
                        "work_gen": "lognormal_request",
                        "inter_gen": "poisson_arrival",
                        "load": 0.5,
                        "mean": 20,
                        "std_dev_request": 1,
                        },
                     "2": {
                        "work_gen": "lognormal_request",
                        "inter_gen": "poisson_arrival",
                        "load": 0.5,
                        "mean": 20,
                        "std_dev_request": 1,
                    }}]

    for deq_cost in deq_costs:
        for host in host_types:
            for time_slice in time_slices:
                for cores in core_count:
                    for config_json in config_jsons:
                        run_sim(deq_cost, host, time_slice, cores,
                                config_json, iterations)


def run_sim(deq_cost, host, time_slice, cores, config_json, iterations):
    # Create config file
    conf, config_file = tempfile.mkstemp()
    os.write(conf, json.dumps(config_json))
    os.close(conf)

    # Run the simulation
    sim_args = ["../src/sim.py",
                "--cores", str(cores),
                "--workload-conf", str(config_file),
                "--time-slice", str(time_slice),
                "--host-type", str(host),
                "--deq-cost", str(deq_cost)]

    total_lat = []
    throughput = []
    per_flow_lat = []
    for i in range(len(config_json)):
        per_flow_lat.append([])

    for i in range(iterations):
        raw = subprocess.check_output(sim_args)
        output = raw.split("\n")[:-1]
        throughput.append(float(output[-1]))
        total_lat.append(float(output[0]))
        for i in range(1, len(config_json)+1):
            per_flow_lat[i-1].append(float(output[i]))

    # Gather the results
    output_name = (OUTPUT_DIR + "sim_" + str(cores) + "_" + str(time_slice) +
                   "_" + str(host) + "_" + str(deq_cost))
    full_name = output_name
    i = 0
    for key in config_json:
        val = config_json[key]
        flow_name = ("_" + "flow" + str(key) + "_" + str(val["work_gen"]) +
                     "_" + str(val["inter_gen"]) + "_" + str(val["load"]))

        if val.get("mean"):
            flow_name += "_" + str(val["mean"])
        if val.get("std_dev_request"):
            flow_name += "_" + str(val["std_dev_request"])
        if val.get("exec_time"):
            flow_name += "_" + str(val["exec_time"])
        if val.get("heavy_per"):
            flow_name += "_" + str(val["heavy_per"])
        if val.get("heavy_time"):
            flow_name += "_" + str(val["heavy_time"])
        if val.get("std_dev_arrival"):
            flow_name += "_" + str(val["std_dev_arrival"])

        full_name += flow_name
        flow_name = output_name + flow_name
        with open(flow_name, 'w') as f:
            for value in per_flow_lat[i]:
                f.write(str(value) + "\n")

        flow_name = flow_name + ".total"
        with open(flow_name, 'w') as f:
            value = sum(per_flow_lat[i]) * 1.0 / len(per_flow_lat[i])
            f.write(str(value) + "\n")

        i += i + 1

    with open(full_name + ".throughput", 'w') as f:
        for value in throughput:
            f.write(str(value) + "\n")

    with open(full_name + ".throughput.total", 'w') as f:
        value = sum(throughput) * 1.0 / len(throughput)
        f.write(str(value) + "\n")

    with open(full_name, 'w') as f:
        for value in total_lat:
            f.write(str(value) + "\n")

    full_name = full_name + ".total"
    with open(full_name, 'w') as f:
        value = sum(total_lat) * 1.0 / len(total_lat)
        f.write(str(value) + "\n")


if __name__ == "__main__":
    main()