from collections import defaultdict

# TODO: Do not use Torch in PyCIEMSS Library interface
import torch
from utils.tds import fetch_interventions
from typing import Dict, Callable
from models.base import HMIIntervention


def fetch_and_convert_static_interventions(
    policy_intervention_id, model_config, job_id
):
    if not (policy_intervention_id):
        return defaultdict(dict), defaultdict(dict)
    policy_intervention = fetch_interventions(policy_intervention_id, job_id)
    interventionList: list[HMIIntervention] = []
    for inter in policy_intervention["interventions"]:
        intervention = HMIIntervention(
            name=inter["name"],
            static_interventions=inter["static_interventions"],
            dynamic_interventions=inter["dynamic_interventions"],
        )
        interventionList.append(intervention)
    return convert_static_interventions(interventionList, model_config)


def fetch_and_convert_dynamic_interventions(policy_intervention_id, job_id):
    if not (policy_intervention_id):
        return defaultdict(dict), defaultdict(dict)
    policy_intervention = fetch_interventions(policy_intervention_id, job_id)
    interventionList: list[HMIIntervention] = []
    for inter in policy_intervention["interventions"]:
        intervention = HMIIntervention(
            name=inter["name"],
            static_interventions=inter["static_interventions"],
            dynamic_interventions=inter["dynamic_interventions"],
        )
        interventionList.append(intervention)
    return convert_dynamic_interventions(interventionList)


def get_semantic_value(semantic):
    """Helper function to get the correct value based on distribution type"""
    distribution = semantic.get("distribution", {})
    if distribution.get("type") == "StandardUniform1":
        params = distribution.get("parameters", {})
        return (params.get("maximum", 0) + params.get("minimum", 0)) / 2
    return semantic["distribution"]["parameters"]["value"]


def get_static_intervention_value(static_inter, model_map):
    """Get static intervention value with distribution and percentage handling"""

    # If the intervention is not a type of parameter or value type of percentage, return the value directly
    if static_inter.type != "parameter" or static_inter.value_type != "percentage":
        return torch.tensor(float(static_inter.value))

    semantic_name = static_inter.applied_to
    parameter = model_map["parameters"][static_inter.applied_to]

    if not parameter:
        raise ValueError(f"Could not find semantic for {semantic_name}")

    base_value = get_semantic_value(parameter)

    return torch.tensor(float(base_value) * (static_inter.value / 100))


# Used to convert from HMI Intervention Policy -> pyciemss static interventions.
def convert_static_interventions(interventions: list[HMIIntervention], model_config):
    model_map = create_model_config_map(model_config)
    if not (interventions):
        return defaultdict(dict), defaultdict(dict)
    static_param_interventions: Dict[torch.Tensor, Dict[str, any]] = defaultdict(dict)
    static_state_interventions: Dict[torch.Tensor, Dict[str, any]] = defaultdict(dict)
    for inter in interventions:
        for static_inter in inter.static_interventions:
            time = torch.tensor(float(static_inter.timestep))
            parameter_name = static_inter.applied_to
            value = get_static_intervention_value(static_inter, model_map)
            if static_inter.type == "parameter":
                static_param_interventions[time][parameter_name] = value
            if static_inter.type == "state":
                static_state_interventions[time][parameter_name] = value
    return static_param_interventions, static_state_interventions


def create_model_config_map(model_config):
    model_map = {
        "initials": {},
        "parameters": {},
    }
    for intitial in model_config["initial_semantic_list"]:
        model_map["initials"][intitial["target"]] = intitial
    for param in model_config["parameter_semantic_list"]:
        model_map["parameters"][param["reference_id"]] = param
    return model_map


# Define the threshold for when the intervention should be applied.
# Can support further functions options in the future
# https://github.com/ciemss/pyciemss/blob/main/docs/source/interfaces.ipynb
def make_var_threshold(var: str, threshold: torch.Tensor):
    def var_threshold(time, state):
        return state[var] - threshold

    return var_threshold


# Used to convert from HMI Intervention Policy -> pyciemss dynamic interventions.
def convert_dynamic_interventions(interventions: list[HMIIntervention]):
    if not (interventions):
        return defaultdict(dict), defaultdict(dict)
    dynamic_parameter_interventions: Dict[
        Callable[[torch.Tensor, Dict[str, torch.Tensor]], torch.Tensor],
        Dict[str, any],
    ] = defaultdict(dict)
    dynamic_state_interventions: Dict[
        Callable[[torch.Tensor, Dict[str, torch.Tensor]], torch.Tensor],
        Dict[str, any],
    ] = defaultdict(dict)
    for inter in interventions:
        for dynamic_inter in inter.dynamic_interventions:
            parameter_name = dynamic_inter.applied_to
            threshold_value = torch.tensor(float(dynamic_inter.threshold))
            to_value = torch.tensor(float(dynamic_inter.value))
            threshold_func = make_var_threshold(
                dynamic_inter.parameter, threshold_value
            )
            if dynamic_inter.type == "parameter":
                dynamic_parameter_interventions[threshold_func].update(
                    {parameter_name: to_value}
                )
            if dynamic_inter.type == "state":
                dynamic_state_interventions[threshold_func].update(
                    {parameter_name: to_value}
                )

    return dynamic_parameter_interventions, dynamic_state_interventions


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
