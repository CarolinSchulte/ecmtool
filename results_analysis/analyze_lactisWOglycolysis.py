import os
import cbmpy as cbm
import csv

"""CONSTANTS"""
model_name = "LactisFULLWOGlycolysis"

# Define directories for finding models
model_dir = os.path.join(os.getcwd(), "models")

model_path = os.path.join(model_dir, model_name + ".xml")
mod = cbm.readSBML3FBC(model_path)
old_fba_result = cbm.doFBA(mod)
# ex_reacs = [re_id for re_id in mod.getReactionIds() if re_id[:4] == 'R_EX']
# ex_reac_tuples = [(re_id, mod.getReaction(re_id).getValue()) for re_id in mod.getReactionIds() if re_id[:4] == 'R_EX']
# medium = [ex_reac for ex_reac in ex_reac_tuples if ex_reac[1] < 0.]
# ex_reac_tuples2 = [(re_id, mod.getReaction(re_id).getValue()) for re_id in mod.getReactionIds() if re_id[:4] == 'R_DM']
# medium2 = [ex_reac for ex_reac in ex_reac_tuples2 if ex_reac[1] < 0.]
# ex_reac_tuples3 = [(re_id, mod.getReaction(re_id).getValue()) for re_id in mod.getReactionIds() if re_id[:4] == 'R_SK']
# medium3 = [ex_reac for ex_reac in ex_reac_tuples3 if ex_reac[1] < 0.]
DER = cbm.CBTools.findDeadEndReactions(mod)
ex_reacs = list(list(zip(*DER))[1])

ex_reac_tuples = [(re_id, mod.getReaction(re_id).getValue()) for re_id in ex_reacs]
medium = [ex_reac for ex_reac in ex_reac_tuples if ex_reac[1] < 0.]
medium_reacs = list(list(zip(*medium))[0])
cbm.CBCPLEX.cplx_MinimizeNumActiveFluxes(mod, optPercentage=100., selected_reactions=medium_reacs)

medium_reac_tuples = [(re_id, mod.getReaction(re_id).getValue()) for re_id in medium_reacs]
minimal_medium = [ex_reac for ex_reac in medium_reac_tuples if ex_reac[1] < 0.]

for reac_id in ex_reacs:
    if reac_id not in list(list(zip(*minimal_medium))[0]):
        reac = mod.getReaction(reac_id)
        reac_lb = mod.getFluxBoundByReactionID(reac_id, 'lower')
        reac_lb.setValue(0.)
        # result_fba = cbm.doFBA(mod)
        # if (old_fba_result-result_fba)/old_fba_result > 0.5:
        #    pass

cbm.doFBA(mod)

# real_medium = []
# for reac_id in ex_reacs:
#     reac = mod.getReaction(reac_id)
#     if reac.getValue() >= 0:
#         reac_lb = mod.getFluxBoundByReactionID(reac_id, 'lower')
#         reac_lb.setValue(0.)
#     else:
#         real_medium.append(reac_id)

fva_result = cbm.CBCPLEX.cplx_FluxVariabilityAnalysis(mod, selected_reactions=[reac[0] for reac in medium])
nzrc_ex_reacs = [(re_id, fva_result[0][re_ind, 2], fva_result[0][re_ind, 3], mod.getReaction(re_id).getValue()) for
                 re_ind, re_id in enumerate(fva_result[1])]

minimal_medium = []
minimal_outputs = []
weird_ones = []
for nzrc_ex_reac in nzrc_ex_reacs:
    re_id = nzrc_ex_reac[0]
    fva_min = nzrc_ex_reac[1]
    fva_max = nzrc_ex_reac[2]
    re_flux = nzrc_ex_reac[3]
    if re_flux > 0.:
        # This is an output
        if fva_min > 1e-8:
            # We need to be able to output this
            minimal_outputs.append(re_id)
        else:
            weird_ones.append((re_id, re_flux, fva_min, fva_max))
    elif re_flux < 0.:
        # This is an input
        if fva_max < 1e-8:
            # We need this in the medium
            minimal_medium.append(re_id)
        else:
            weird_ones.append((re_id, re_flux, fva_min, fva_max))

# minimal medium seems to be

essential_inputs = []
non_essential_minimal = []
essential_input_obj_diffs = []
for reac_id in minimal_medium:
    reac = mod.getReaction(reac_id)
    reac_lb = mod.getFluxBoundByReactionID(reac_id, 'lower')
    cons_val_orig = reac_lb.value
    reac_lb.setValue(0.)
    fba_result = cbm.doFBA(mod)
    if (old_fba_result - fba_result)/old_fba_result > 0.1:
        essential_inputs.append(reac_id)
        essential_input_obj_diffs.append(old_fba_result - fba_result)
    else:
        non_essential_minimal.append(reac_id)
    reac_lb.setValue(cons_val_orig)

# Store essential inputs
with open('essential_inputs_iIT341.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(minimal_medium)

# print("The lower bound for '{0}' is currently '{1}'".format(reac_tuple[0], reac_tuple[1]))
# cons_val = input('What do you want it to become?')
# if not cons_val:
#     cons_val = reac_tuple[1]
# else:
#     cons_val = float(cons_val)
# reac_lb.setValue(cons_val)

# ecms_matrix, full_network_ecm = calc_ECMs(model_path, print_results=True)
#
# # Find all metabolite_ids in the order used by ECMtool
# metab_ids = [metab.id for metab in full_network_ecm.metabolites]
# # Create dataframe with the ecms as columns and the metabolites as index
# ecms_df = pd.DataFrame(ecms_matrix, index=metab_ids)
#
# ext_indices = [ind for ind, metab in enumerate(full_network_ecm.metabolites) if metab.is_external]
# ext_metab_ids = [metab for ind, metab in enumerate(metab_ids) if ind in ext_indices]
# ecms_matrix_ext = ecms_matrix[ext_indices, :]
# ecms_df = pd.DataFrame(ecms_matrix_ext, index=ext_metab_ids)
#
# ecms_df.to_csv(path_or_buf='ecms_iJR904_ext.csv', index=True)
# ecms_df.to_csv(path_or_buf='ecms_iJR904.csv', index=True)
