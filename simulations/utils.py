import json
import requests
import sys


def parse_samples_into_file(samples):
    # samples_str = json.dumps(samples)
    # samples_dict = json.loads(samples)

    pyciemss_results = {"states": {}, "params": {}}
    for key, value in samples.items():
        key_components = key.split("_")
        if len(key_components) > 1:
            if key_components[1] == "sol":
                pyciemss_results["states"][key] = value
        else:
            pyciemss_results["params"][key] = value

    print(pyciemss_results)

    file_output_json = {
        "0": {
            "description": "PyCIEMSS integration demo",
            "initials": {
                str(i): {"name": k, "identifiers": {}, "value": v.tolist()[0][0]}
                for i, (k, v) in enumerate(pyciemss_results["states"].items())
            },
            "parameters": {
                str(i): {"name": k, "identifiers": {}, "value": v.tolist()}
                for i, (k, v) in enumerate(pyciemss_results["params"].items())
            },
            "output": {
                str(i): {"name": k, "identifiers": {}, "value": v.tolist()}
                for i, (k, v) in enumerate(pyciemss_results["states"].items())
            },
        }
    }

    with open("sim_output.json", "w") as f:
        f.write(json.dumps(file_output_json))


def update_tds_status(url, status, result_files=[]):
    tds_payload = requests.get(url)
    print(vars(tds_payload).keys())
    print(tds_payload.json())
    sys.stdout.flush()

    tds_payload = tds_payload.json()

    tds_payload["status"] = status
    if result_files:
        tds_payload["result_files"] = result_files

    update_response = requests.put(url, tds_payload)

    return update_response.content()
