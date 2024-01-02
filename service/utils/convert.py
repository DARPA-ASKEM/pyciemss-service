from collections import defaultdict


def convert_to_static_interventions(interventions):
    static_interventions = defaultdict(dict)
    for i in interventions:
        static_interventions[i.timestep][i.name] = i.value
    return static_interventions
