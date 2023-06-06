from __future__ import annotations

from fastapi import APIRouter

from .models import (
    CalibratePostRequest,
    CalibratePostResponse,
    CalibrateSimulatePostRequest,
    CalibrateSimulatePostResponse,
    EnsemblePostRequest,
    EnsemblePostResponse,
    SimulatePostRequest,
    SimulatePostResponse,
    StatusSimulationIdGetResponse,
)

router = APIRouter()


@router.post('/calibrate', response_model=CalibratePostResponse)
def calibrate_model(body: CalibratePostRequest) -> CalibratePostResponse:
    """
    Calibrate a model (SciML only)
    """
    pass


@router.post('/calibrate_simulate', response_model=CalibrateSimulatePostResponse)
def calibratesimulate_model(
    body: CalibrateSimulatePostRequest,
) -> CalibrateSimulatePostResponse:
    """
    Calibrate a model (CIEMSS only)
    """
    pass


@router.post('/ensemble', response_model=EnsemblePostResponse)
def create_ensemble(body: EnsemblePostRequest) -> EnsemblePostResponse:
    """
    Perform an ensemble simulation
    """
    pass


@router.post('/simulate', response_model=SimulatePostResponse)
def simulate_model(body: SimulatePostRequest) -> SimulatePostResponse:
    """
    Perform a simulation
    """
    pass


@router.get('/status/{simulation_id}', response_model=StatusSimulationIdGetResponse)
def get_status(simulation_id: str) -> StatusSimulationIdGetResponse:
    """
    Retrieve the status of a simulation
    """
    pass
