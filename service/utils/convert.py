from collections import defaultdict


def convert_to_static_interventions(interventions):
    static_interventions = defaultdict(dict)
    for i in interventions:
        static_interventions[i.timestep][i.name] = i.value
    return static_interventions


def convert_to_solution_mapping(config):
    flipped_map = {
        to: from_state for (from_state, to) in config.solution_mappings.items()
    }

    def solution_mapping(individual_states):
        ensemble_map = {}
        for state, value in individual_states.items():
            ensemble_map[flipped_map[state]] = value * config.weight
        return ensemble_map

    return solution_mapping
