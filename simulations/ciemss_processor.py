import os
import numpy as np
from pyciemss.PetriNetODE.interfaces import load_and_sample_petri_model

def simulate_model(*args, **kwargs):

    model = kwargs.get("model")
    num_samples = kwargs.get("num_samples")
    start_epoch = kwargs.get("start_epoch")
    end_epoch = kwargs.get("end_epoch")
    add_uncertainty = kwargs.get("add_uncertainty", True)
    
    #Generate timepoints
    time_count = end_epoch - start_epoch
    timepoints = map(float, range(1, time_count + 1))

    
    samples = load_and_sample_petri_model(
        model, num_samples, timepoints=timepoints, add_uncertainty=add_uncertainty
    )

    return samples