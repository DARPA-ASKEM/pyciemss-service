import json
import os


def parse_samples_into_file(samples):
    samples_str = json.dumps(samples)
    samples_dict = json.loads(samples_str)

    states = {}
    params = {}
    for key, value in samples_dict.items():
        if key.split("_")[1] == "sol":
            states[key] = value
        else:
            params[key] = value

    file_output_json = {
        "0": {
            "description": "PyCIEMSS integration demo",
            "initials": {
                str(i): {"name": k, "identifiers": {}, "value": list(v[:, 0])}
                for i, (k, v) in enumerate(states.items())
            },
            "parameters": {
                str(i): {"name": k, "identifiers": {}, "value": list(v)}
                for i, (k, v) in enumerate(params.items())
            },
            "output": {
                str(i): {"name": k, "identifiers": {}, "value": v.tolist()}
                for i, (k, v) in enumerate(states.items())
            },
        }
    }

    with open("sim_output.json", "w") as f:
        f.write(json.dumps(file_output_json, indent=4))
