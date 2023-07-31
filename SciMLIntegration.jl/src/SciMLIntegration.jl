module SciMLIntegration

import DataFrames: DataFrame, names
import DifferentialEquations: solve
import ModelingToolkit: remake, ODESystem, ODEProblem, Differential, @parameters
import Symbolics: Num, getname, @variables, substitute
import JSON
import MathML


# Separate keys and values
unzip(d::Dict) = (collect(keys(d)), collect(values(d)))

# Unzip a collection of pairs
unzip(ps) = first.(ps), last.(ps)


function coerce_model(val)
    obj = JSON.Parser.parse(val)
    model = obj["model"]
    ode = obj["semantics"]["ode"]

    t = only(@variables t)
    D = Differential(t)

    statenames = [Symbol(s["id"]) for s in model["states"]]
    statevars  = [only(@variables $s) for s in statenames]
    statefuncs = [only(@variables $s(t)) for s in statenames]

    # get parameter values and state initial values
    paramnames = [Symbol(x["id"]) for x in ode["parameters"]]
    paramvars = [only(@parameters $x) for x in paramnames]
    paramvals = [x["value"] for x in ode["parameters"]]
    sym_defs = paramvars .=> paramvals
    initial_exprs = [MathML.parse_str(x["expression_mathml"]) for x in ode["initials"]]
    initial_vals = map(x->substitute(x, sym_defs), initial_exprs)

    # build equations from transitions and rate expressions
    rates = Dict(Symbol(x["target"]) => MathML.parse_str(x["expression_mathml"]) for x in ode["rates"])
    eqs = Dict(s => Num(0) for s in statenames)
    for tr in model["transitions"]
        ratelaw = rates[Symbol(tr["id"])]
        for s in tr["input"]
            s = Symbol(s)
            eqs[s] = eqs[s] - ratelaw
        end
        for s in tr["output"]
            s = Symbol(s)
            eqs[s] = eqs[s] + ratelaw
        end
    end

    subst = Dict(zip(statevars, statefuncs))
    eqs = [D(statef) ~ substitute(eqs[state], subst) for (state, statef) in zip(statenames, statefuncs)]

    ODESystem(eqs, t, statefuncs, paramvars; defaults = [statefuncs .=> initial_vals; sym_defs], name=Symbol(obj["name"]))
end

function to_prob(amr, tspan)
    sys = coerce_model(amr)
    ODEProblem(sys, [], tspan, saveat=1)
end

# Transform list of args into Symbolics variables
function symbolize_args(incoming_values, sys_vars)
    pairs = collect(incoming_values)
    ks, values = unzip(pairs)
    symbols = Symbol.(ks)
    vars_as_symbols = getname.(sys_vars)
    symbols_to_vars = Dict(vars_as_symbols .=> sys_vars)
    Dict(
        [
            symbols_to_vars[vars_as_symbols[findfirst(x -> x == symbol, vars_as_symbols)]]
            for symbol in symbols
        ] .=> values
    )
end

function simulate(amr, tstart, tend)
    prob = to_prob(amr, (tstart, tend))
    sol = solve(prob; progress = true, progress_steps = 1)
    DataFrame(sol)
end

end # module SciMLIntegration
