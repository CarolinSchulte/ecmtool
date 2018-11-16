from scipy.optimize import linprog

from helpers import *
from time import time
from conversion_cone import get_conversion_cone
from argparse import ArgumentParser

if __name__ == '__main__':
    start = time()

    parser = ArgumentParser(description='Calculate Elementary Conversion Modes from an SBML model. For medium-to large networks, be sure to define --inputs and --outputs. This reduces the enumeration problem complexity considerably.')
    parser.add_argument('--model_path', default='models/e_coli_core.xml', help='Relative or absolute path to an SBML model .xml file')
    parser.add_argument('--compress', type=bool, default=True, help='Perform compression to which the conversions are invariant, and reduce the network size considerably (default: True)')
    parser.add_argument('--out_path', default='conversion_cone.csv', help='Relative or absolute path to the .csv file you want to save the calculated conversions to')
    parser.add_argument('--add_objective_metabolite', type=bool, default=True, help='Add a virtual metabolite containing the stoichiometry of the objective function of the model')
    parser.add_argument('--check_feasibility', type=bool, default=False, help='For each found ECM, verify that a feasible flux exists that produces it')
    parser.add_argument('--print_metabolites', type=bool, default=True, help='Print the names and IDs of metabolites in the (compressed) metabolic network')
    parser.add_argument('--inputs', type=str, default='', help='Comma-separated list of external metabolite indices, as given by --print_metabolites true, that can only be consumed')
    parser.add_argument('--outputs', type=str, default='', help='Comma-separated list of external metabolite indices, as given by --print_metabolites true, that can only be produced')
    args = parser.parse_args()

    model_path = args.model_path

    network = extract_sbml_stoichiometry(model_path, add_objective=args.add_objective_metabolite)
    orig_ids = [m.id for m in network.metabolites]
    orig_N = network.N

    if args.compress:
        network.compress(verbose=True)
    # add_debug_tags(network)

    for index, item in enumerate(network.metabolites):
        print(index, item.id, item.name)

    symbolic = True
    # inputs = [1] # Glucose
    # inputs = [13, 22, 23, 25, 1] # Glucose, ammonium, O2, phosphate, acetate
    inputs = [int(index) for index in args.inputs.split(',') if len(index)]
    # Acetate, acetaldehyde, 2-oxoglutarate, CO2, ethanol, formate, D-fructose, fumarate, L-glutamine, L-glutamate,
    # H2O, H+, lactate, L-malate, pyruvate, succinate
    # output_exceptions = [6, 8, 14, 19, 24, 28, 29, 31, 36, 38, 41, 43, 46, 48, 62, 69]
    outputs = [int(index) for index in args.outputs.split(',') if len(index)]
    if len(outputs) < 1:
        # If no outputs are given, define all external metabolites that are not inputs as outputs
        outputs = np.setdiff1d(network.external_metabolite_indices(), inputs)
    cone = get_conversion_cone(network.N, network.external_metabolite_indices(), network.reversible_reaction_indices(),
                               # verbose=True, symbolic=symbolic)
                               input_metabolites=inputs, output_metabolites=outputs, verbose=True, symbolic=symbolic)

    # Undo compression so we have results in the same dimensionality as original data
    expanded_c = np.zeros(shape=(cone.shape[0], len(orig_ids)))
    for column, id in enumerate([m.id for m in network.metabolites]):
        orig_column = [index for index, orig_id in enumerate(orig_ids) if orig_id == id][0]
        expanded_c[:, orig_column] = cone[:, column]

    np.savetxt(args.out_path, expanded_c, delimiter=',')

    for index, ecm in enumerate(cone):
        # if not ecm[-1]:
        #     continue

        # Normalise by objective metabolite, if applicable
        if args.add_objective_metabolite and ecm[-1] > 0:
            ecm /= ecm[-1]
            expanded_c[index, :] /= expanded_c[index, -1]

        print('\nECM #%d:' % index)
        for metabolite_index, stoichiometry_val in enumerate(ecm):
            if stoichiometry_val != 0.0:
                print('%d %s\t\t->\t%.4f' % (metabolite_index, network.metabolites[metabolite_index].name, stoichiometry_val))

        if args.check_feasibility:
            allowed_error = 10**-6
            solution = linprog(c=[0] * orig_N.shape[1], A_eq=orig_N, b_eq=expanded_c[index, :],
                               bounds=[(-1000, 1000)] * orig_N.shape[1], options={'tol': allowed_error})
            print('ECM satisfies stoichiometry' if solution.status == 0 else 'ECM does not satisfy stoichiometry')

    end = time()
    print('Ran in %f seconds' % (end - start))
    pass