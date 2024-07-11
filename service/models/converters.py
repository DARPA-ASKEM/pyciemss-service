from collections import defaultdict

# TODO: Do not use Torch in PyCIEMSS Library interface
import torch
from utils.tds import fetch_interventions
from typing import Dict
from models.base import HMIIntervention


def fetch_and_convert_static_interventions(policy_intervention_id, job_id):
    if not (policy_intervention_id):
        return defaultdict(dict)
    policy_intervention = fetch_interventions(policy_intervention_id, job_id)
    interventionList = policy_intervention["interventions"]
    return convert_static_interventions(interventionList)


# Used to convert from HMI Intervention Policy -> pyciemss static interventions.
def convert_static_interventions(interventions: list[HMIIntervention]):
    if not (interventions):
        return defaultdict(dict)
    static_interventions: Dict[torch.Tensor, Dict[str, any]] = defaultdict(dict)
    for inter in interventions:
        for static_inter in inter.static_interventions:
            time = torch.tensor(float(static_inter.timestep))
            parameter_name = inter.applied_to
            value = torch.tensor(float(static_inter.value))
            static_interventions[time][parameter_name] = value
    return static_interventions


def convert_to_solution_mapping(config):
    individual_to_ensemble = {
        individual_state: ensemble_state
        for (ensemble_state, individual_state) in config.solution_mappings.items()
    }

    def solution_mapping(individual_states):
        ensemble_map = defaultdict(lambda: 0)
        for state, value in individual_states.items():
            ensemble_state = (
                individual_to_ensemble[state]
                if state in individual_to_ensemble
                else "uncategorized"
            )
            ensemble_map[ensemble_state] += value
        return ensemble_map

    return solution_mapping
