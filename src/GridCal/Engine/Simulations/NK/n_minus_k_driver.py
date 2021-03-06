# This file is part of GridCal.
#
# GridCal is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GridCal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GridCal.  If not, see <http://www.gnu.org/licenses/>.
import time
import datetime
import numpy as np
import pandas as pd
from itertools import combinations
from PySide2.QtCore import QThread, Signal

from GridCal.Engine.basic_structures import Logger
from GridCal.Engine.Core.multi_circuit import MultiCircuit
from GridCal.Engine.Core.time_series_pf_data import compile_time_circuit, split_time_circuit_into_islands, TimeCircuit
from GridCal.Engine.Simulations.PowerFlow.power_flow_worker import PowerFlowOptions, SolverType, single_island_pf
from GridCal.Engine.Simulations.NK.n_minus_k_results import NMinusKResults


def enumerate_states_n_k(m, k=1):
    """
    Enumerates the states to produce the so called N-k failures
    :param m: number of branches
    :param k: failure level
    :return: binary array (number of states, m)
    """

    # num = int(math.factorial(k) / math.factorial(m-k))
    states = list()
    indices = list()
    arr = np.ones(m, dtype=int).tolist()

    idx = list(range(m))
    for k1 in range(k + 1):
        for failed in combinations(idx, k1):
            indices.append(failed)
            arr2 = arr.copy()
            for j in failed:
                arr2[j] = 0
            states.append(arr2)

    return np.array(states), indices


def set_base_profile(nc: TimeCircuit):
    """
    Re-index all the time based profiles
    :return: Nothing, this is done in-place
    """
    now = datetime.datetime.now()
    dte = datetime.datetime(year=now.year, month=1, day=1, hour=0)
    nc.time_array = pd.to_datetime([dte])
    nc.ntime = len(nc.time_array)

    # branch
    nc.branch_active_prof = nc.branch_active.reshape(1, -1)  # np.zeros((n_time, n_br), dtype=int)
    nc.temp_oper_prof = nc.line_temp_oper.reshape(1, -1)  # np.zeros((n_time, n_br), dtype=float)
    nc.br_rate_profile = nc.branch_rates.reshape(1, -1)  # np.zeros((n_time, n_br), dtype=float)

    # load
    nc.load_active_prof = nc.load_active.reshape(1, -1)  # np.zeros((n_time, n_ld), dtype=bool)

    nc.load_power_profile = nc.load_s.reshape(1, -1)  # np.zeros((n_time, n_ld), dtype=complex)

    # battery
    nc.battery_active_prof = nc.battery_active.reshape(1, -1)  # np.zeros((n_time, n_batt), dtype=bool)
    nc.battery_power_profile = nc.battery_p.reshape(1, -1)  # np.zeros((n_time, n_batt), dtype=float)
    nc.battery_voltage_profile = nc.battery_v.reshape(1, -1)  # np.zeros((n_time, n_batt), dtype=float)

    # static generator
    nc.static_gen_active_prof = nc.static_generator_active.reshape(1, -1)  # np.zeros((n_time, n_sta_gen), dtype=bool)
    nc.static_gen_power_profile = nc.static_generator_s.reshape(1, -1)  # np.zeros((n_time, n_sta_gen), dtype=complex)

    # controlled generator
    nc.generator_active_prof = nc.generator_active.reshape(1, -1)  # np.zeros((n_time, n_gen), dtype=bool)
    nc.generator_power_profile = nc.generator_p.reshape(1, -1)  # np.zeros((n_time, n_gen), dtype=float)
    nc.generator_power_factor_profile = nc.generator_pf.reshape(1, -1)  # np.zeros((n_time, n_gen), dtype=float)
    nc.generator_voltage_profile = nc.generator_v.reshape(1, -1)  # np.zeros((n_time, n_gen), dtype=float)

    # shunt
    nc.shunt_active_prof = nc.shunt_active.reshape(1, -1)  # np.zeros((n_time, n_sh), dtype=bool)
    nc.shunt_admittance_profile = nc.shunt_admittance.reshape(1, -1)  # np.zeros((n_time, n_sh), dtype=complex)


def re_index_time(nc: TimeCircuit, t_idx):
    """
    Re-index all the time based profiles
    :param t_idx: new indices of the time profiles
    :return: Nothing, this is done in-place
    """

    nc.time_array = nc.time_array[t_idx]
    nc.ntime = len(t_idx)

    # branch
    nc.branch_active_prof = nc.branch_active[t_idx, :]  # np.zeros((n_time, n_br), dtype=int)
    # nc.temp_oper_prof = nc.line_temp_oper[t_idx, :]  # np.zeros((n_time, n_br), dtype=float)
    nc.br_rate_profile = nc.branch_rates[t_idx, :]  # np.zeros((n_time, n_br), dtype=float)

    # load
    nc.load_active_prof = nc.load_active[t_idx, :]  # np.zeros((n_time, n_ld), dtype=bool)

    nc.load_power_profile = nc.load_s[t_idx, :]  # np.zeros((n_time, n_ld), dtype=complex)

    # battery
    nc.battery_active_prof = nc.battery_active[t_idx, :]  # np.zeros((n_time, n_batt), dtype=bool)
    nc.battery_power_profile = nc.battery_p[t_idx, :]  # np.zeros((n_time, n_batt), dtype=float)
    nc.battery_voltage_profile = nc.battery_v[t_idx, :]  # np.zeros((n_time, n_batt), dtype=float)

    # static generator
    nc.static_gen_active_prof = nc.static_generator_active[t_idx, :]  # np.zeros((n_time, n_sta_gen), dtype=bool)
    nc.static_gen_power_profile = nc.static_generator_s[t_idx, :]  # np.zeros((n_time, n_sta_gen), dtype=complex)

    # controlled generator
    nc.generator_active_prof = nc.generator_active[t_idx, :]  # np.zeros((n_time, n_gen), dtype=bool)
    nc.generator_power_profile = nc.generator_p[t_idx, :]  # np.zeros((n_time, n_gen), dtype=float)
    nc.generator_power_factor_profile = nc.generator_pf[t_idx, :]  # np.zeros((n_time, n_gen), dtype=float)
    nc.generator_voltage_profile = nc.generator_v[t_idx, :]  # np.zeros((n_time, n_gen), dtype=float)

    # shunt
    nc.shunt_active_prof = nc.shunt_active[t_idx, :]  # np.zeros((n_time, n_sh), dtype=bool)
    nc.shunt_admittance_profile = nc.shunt_admittance[t_idx, :]  # np.zeros((n_time, n_sh), dtype=complex)


class NMinusKOptions:

    def __init__(self, use_multi_threading):

        self.use_multi_threading = use_multi_threading


class NMinusK(QThread):
    progress_signal = Signal(float)
    progress_text = Signal(str)
    done_signal = Signal()
    name = 'N-1/OTDF'

    def __init__(self, grid: MultiCircuit, options: NMinusKOptions, pf_options: PowerFlowOptions):
        """
        N - k class constructor
        @param grid: MultiCircuit Object
        @param options: N-k options
        @:param pf_options: power flow options
        """
        QThread.__init__(self)

        # Grid to run
        self.grid = grid

        # Options to use
        self.options = options

        # power flow options
        self.pf_options = pf_options

        # N-K results
        self.results = NMinusKResults(n=0, m=0, nt=0, n_tr=0, bus_names=(),
                                      branch_names=(), transformer_names=(), bus_types=(),
                                      time_array=None, states=None)

        # set cancel state
        self.__cancel__ = False

        self.all_solved = True

        self.logger = Logger()

        self.elapsed = 0.0

        self.branch_names = list()

    def get_steps(self):
        """
        Get variations list of strings
        """
        if self.results is not None:
            return [v for v in self.branch_names]
        else:
            return list()

    def n_minus_k(self, k=1, indices=None, vmin=0, states_number_limit=None):
        """
        Run N-K simulation in series
        :param k: Parameter level (1 for n-1, 2 for n-2, etc...)
        :param indices: time indices {np.array([0])}
        :param vmin: minimum nominal voltage to allow (filters out branches and buses below)
        :param states_number_limit: limit the amount of states
        :return: Nothing, saves a report
        """

        self.progress_text.emit("Filtering elements by voltage")

        # filter branches
        branch_names = list()
        branch_index = list()
        branches = list()  # list of filtered branches
        for i, branch in enumerate(self.grid.lines):
            if branch.bus_from.Vnom > vmin or branch.bus_to.Vnom > vmin:
                branch_names.append(branch.name)
                branch_index.append(i)
                branches.append(branch)
        branch_index = np.array(branch_index)

        self.branch_names = branch_names

        # filter buses
        bus_names = list()
        bus_index = list()
        for i, bus in enumerate(self.grid.buses):
            if bus.Vnom > vmin:
                bus_names.append(bus.name)
                bus_index.append(i)
        bus_index = np.array(bus_index)

        # get N-k states
        self.progress_text.emit("Enumerating states")
        states, failed_indices = enumerate_states_n_k(m=len(branch_names), k=k)

        # limit states for memory reasons
        if states_number_limit is not None:
            states = states[:states_number_limit, :]
            failed_indices = failed_indices[:states_number_limit]

        # compile the multi-circuit
        self.progress_text.emit("Compiling assets...")
        self.progress_signal.emit(0)

        numerical_circuit = compile_time_circuit(circuit=self.grid,
                                                 apply_temperature=self.pf_options.apply_temperature_correction,
                                                 branch_tolerance_mode=self.pf_options.branch_impedance_tolerance_mode)

        # re-index the profile (this is essential for time-compatibility)
        self.progress_signal.emit(100)

        # if no base profile time is given, pick the base values
        if indices is None:
            time_indices = np.array([0])
            set_base_profile(numerical_circuit)
        else:
            time_indices = indices

        # construct the profile indices
        profile_indices = np.tile(time_indices, len(states))
        re_index_time(numerical_circuit, t_idx=profile_indices)

        # set the branch states
        numerical_circuit.branch_active[:, branch_index] = np.tile(states, (len(time_indices), 1))

        # initialize the power flow
        pf_options = PowerFlowOptions(solver_type=SolverType.LACPF)

        # initialize the grid time series results we will append the island results with another function
        n = self.grid.get_bus_number()
        m = self.grid.get_branch_number()
        nt = len(profile_indices)

        n_k_results = NMinusKResults(n, m, nt, time_array=numerical_circuit.time_array)

        # do the topological computation
        self.progress_text.emit("Compiling topology...")
        self.progress_signal.emit(0.0)

        calc_inputs = split_time_circuit_into_islands(numeric_circuit=numerical_circuit,
                                                      ignore_single_node_islands=self.pf_options.ignore_single_node_islands)

        n_k_results.bus_types = numerical_circuit.bus_types

        self.progress_text.emit("Simulating states...")
        npart = len(calc_inputs)
        k = 1

        # For every island, run the time series
        for island_index, calculation_input in enumerate(calc_inputs):

            self.progress_signal.emit((island_index + 1) / npart * 100.0)

            # find the original indices
            bus_original_idx = calculation_input.original_bus_idx
            branch_original_idx = calculation_input.original_branch_idx

            # declare a results object for the partition
            # nt = calculation_input.ntime
            nt = len(calculation_input.original_time_idx)
            n = calculation_input.nbus
            m = calculation_input.nbr
            partial_results = NMinusKResults(n, m, nt)
            last_voltage = calculation_input.Vbus

            # traverse the time profiles of the partition and simulate each time step
            for it, t in enumerate(calculation_input.original_time_idx):
                # set the power values
                # if the storage dispatch option is active, the batteries power is not included
                # therefore, it shall be included after processing

                I = calculation_input.Ibus[:, it]
                S = calculation_input.Sbus[:, it]
                branch_rates = calculation_input.branch_rates[it, :]

                # run power flow at the circuit
                res = single_island_pf(circuit=calculation_input, Vbus=last_voltage, Sbus=S, Ibus=I,
                                       branch_rates=branch_rates, options=pf_options, logger=self.logger)

                # Recycle voltage solution
                last_voltage = res.voltage

                # store circuit results at the time index 't'
                partial_results.set_at(it, res)

            # merge the circuit's results
            n_k_results.apply_from_island(partial_results, bus_original_idx, branch_original_idx,
                                          calculation_input.original_time_idx, 'TS')

            k += 1

        return n_k_results

    def n_minus_k_mt(self, k=1, indices=None, vmin=200, states_number_limit=None):
        """
        Run N-K simulation in series
        :param k: Parameter level (1 for n-1, 2 for n-2, etc...)
        :param indices: time indices {np.array([0])}
        :param vmin: minimum nominal voltage to allow (filters out branches and buses below)
        :param states_number_limit: limit the amount of states
        :return: Nothing, saves a report
        """
        self.progress_text.emit("Filtering elements by voltage")

        # filter branches
        branch_names = list()
        branch_index = list()
        branches = list()  # list of filtered branches
        for i, branch in enumerate(self.grid.lines):
            if branch.bus_from.Vnom > vmin or branch.bus_to.Vnom > vmin:
                branch_names.append(branch.name)
                branch_index.append(i)
                branches.append(branch)
        branch_index = np.array(branch_index)

        # filter buses
        bus_names = list()
        bus_index = list()
        for i, bus in enumerate(self.grid.buses):
            if bus.Vnom > vmin:
                bus_names.append(bus.name)
                bus_index.append(i)
        bus_index = np.array(bus_index)

        # get N-k states
        self.progress_text.emit("Enumerating states")
        states, failed_indices = enumerate_states_n_k(m=len(branch_names), k=k)

        # limit states for memory reasons
        if states_number_limit is not None:
            states = states[:states_number_limit, :]
            failed_indices = failed_indices[:states_number_limit]

        # compile the multi-circuit
        self.progress_text.emit("Compiling assets...")
        self.progress_signal.emit(0)
        numerical_circuit = self.grid.compile_time_series()

        # if no base profile time is given, pick the base values
        if indices is None:
            time_indices = np.array([0])
            numerical_circuit.set_base_profile()
        else:
            time_indices = indices

        # re-index the profile (this is essential for time-compatibility)
        self.progress_signal.emit(100)
        # construct the profile indices
        profile_indices = np.tile(time_indices, len(states))
        numerical_circuit.re_index_time(t_idx=profile_indices)

        # set the branch states
        numerical_circuit.branch_active_prof[:, branch_index] = np.tile(states, (len(time_indices), 1))

        # initialize the power flow
        pf_options = PowerFlowOptions(solver_type=SolverType.LACPF)

        # initialize the grid time series results we will append the island results with another function
        n = len(self.grid.buses)
        m = self.circuit.get_branch_number()
        nt = len(profile_indices)

        n_k_results = NMinusKResults(n, m, nt, time_array=numerical_circuit.time_array, states=states)

        # do the topological computation
        self.progress_text.emit("Compiling topology...")
        self.progress_signal.emit(0.0)
        calc_inputs_dict = numerical_circuit.compute(ignore_single_node_islands=pf_options.ignore_single_node_islands)

        n_k_results.bus_types = numerical_circuit.bus_types

        # for each partition of the profiles...
        self.progress_text.emit("Simulating states...")
        for t_key, calc_inputs in calc_inputs_dict.items():

            # For every island, run the time series
            for island_index, calculation_input in enumerate(calc_inputs):

                # find the original indices
                bus_original_idx = calculation_input.original_bus_idx
                branch_original_idx = calculation_input.original_branch_idx

                # if there are valid profiles...
                if self.grid.time_profile is not None:

                    # declare a results object for the partition
                    # nt = calculation_input.ntime
                    nt = len(calculation_input.original_time_idx)
                    n = calculation_input.nbus
                    m = calculation_input.nbr
                    partial_results = NMinusKResults(n, m, nt)
                    last_voltage = calculation_input.Vbus

                    # traverse the time profiles of the partition and simulate each time step
                    for it, t in enumerate(calculation_input.original_time_idx):
                        self.progress_signal.emit(it / nt * 100.0)

                        # set the power values
                        # if the storage dispatch option is active, the batteries power is not included
                        # therefore, it shall be included after processing
                        Ysh = calculation_input.Ysh_prof[:, it]
                        I = calculation_input.Ibus_prof[:, it]
                        S = calculation_input.Sbus_prof[:, it]
                        branch_rates = calculation_input.branch_rates_prof[it, :]

                        # run power flow at the circuit
                        res = single_island_pf(circuit=calculation_input, Vbus=last_voltage, Sbus=S, Ibus=I,
                                               branch_rates=branch_rates, options=pf_options, logger=self.logger)

                        # Recycle voltage solution
                        last_voltage = res.voltage

                        # store circuit results at the time index 't'
                        partial_results.set_at(it, res)

                    # merge the circuit's results

                    n_k_results.apply_from_island(partial_results, bus_original_idx, branch_original_idx,
                                                  calculation_input.original_time_idx, 'TS')
                else:
                    self.progress_text.emit('There are no profiles')
                    self.logger.append('There are no profiles')

        return n_k_results

    def run(self):
        """

        :return:
        """
        start = time.time()
        if self.options.use_multi_threading:
            self.results = self.n_minus_k_mt(k=1, indices=None, vmin=0, states_number_limit=None)

        else:
            self.results = self.n_minus_k(k=1, indices=None, vmin=0, states_number_limit=None)

        self.progress_text.emit('Computing OTDF...')
        if self.results is not None:
            self.results.branch_names = np.array([b.name for b in self.grid.lines])
            self.results.otdf = self.get_otdf(failure_flow_limit=1.0/100.0)

        end = time.time()
        self.elapsed = end - start
        self.progress_text.emit('Done!')
        self.done_signal.emit()

    def get_otdf(self, failure_flow_limit=0.0):
        """
        Outage Transfer Distribution Factors (OTDF)
        :return: OTDF matrix with the failures as rows
        """
        if self.results is None:
            return None
        else:
            p_branch = self.results.Sbranch.real
            m = p_branch.shape[1]
            otdf = np.zeros((m, m))
            for i in range(m):
                # (power of line_i at the base - power of line_i at the failure) / power of the failed line at the base
                if abs(p_branch[0, i]) >= failure_flow_limit:
                    otdf[i, :] = (p_branch[i + 1, :] - p_branch[0, :]) / (p_branch[0, i] + 1e-12)

            return otdf

    def cancel(self):
        self.__cancel__ = True


if __name__ == '__main__':
    import os
    import pandas as pd
    from GridCal.Engine import FileOpen, SolverType

    # fname = '/home/santi/Documentos/GitHub/GridCal/Grids_and_profiles/grids/Lynn 5 Bus pv.gridcal'
    # fname = '/home/santi/Documentos/GitHub/GridCal/Grids_and_profiles/grids/IEEE39_1W.gridcal'
    # fname = '/home/santi/Documentos/GitHub/GridCal/Grids_and_profiles/grids/grid_2_islands.xlsx'
    # fname = '/home/santi/Documentos/GitHub/GridCal/Grids_and_profiles/grids/2869 Pegase.gridcal'
    fname = os.path.join('..', '..', '..', '..', '..', 'Grids_and_profiles', 'grids', 'IEEE 30 Bus with storage.xlsx')
    # fname = os.path.join('..', '..', '..', '..', '..', 'Grids_and_profiles', 'grids', '2869 Pegase.gridcal')

    main_circuit = FileOpen(fname).open()

    pf_options_ = PowerFlowOptions(solver_type=SolverType.LACPF)
    options_ = NMinusKOptions(use_multi_threading=False)
    simulation = NMinusK(grid=main_circuit, options=options_, pf_options=pf_options_)
    simulation.run()

    otdf_ = simulation.get_otdf()

    # save the result
    br_names = [b.name for b in main_circuit.branches]
    br_names2 = ['#' + b.name for b in main_circuit.branches]
    w = pd.ExcelWriter('OTDF IEEE30.xlsx')
    pd.DataFrame(data=simulation.results.Sbranch.real,
                 columns=br_names,
                 index=['base'] + br_names2).to_excel(w, sheet_name='branch power')
    pd.DataFrame(data=otdf_,
                 columns=br_names,
                 index=br_names2).to_excel(w, sheet_name='OTDF')
    w.save()