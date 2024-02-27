from collections import defaultdict

# TODO: Do not use Torch in PyCIEMSS Library interface
import torch


def convert_to_static_interventions(interventions):
    static_interventions = defaultdict(dict)
    for i in interventions:
        static_interventions[i.timestep][i.name] = torch.tensor(i.value)
    return static_interventions


def convert_optimize_to_static_interventions(interventions):
    static_interventions = defaultdict(dict)
    for i in interventions:
        static_interventions[i.name] = torch.tensor(i.timestep)
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
