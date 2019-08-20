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

import numpy as np

from GridCal.Engine.Core.multi_circuit import MultiCircuit
from GridCal.Engine.Devices.branch import Branch
from GridCal.Engine.Devices.bus import Bus
from GridCal.Engine.Devices.generator import Generator
from GridCal.Engine.Devices.load import Load
from GridCal.Engine.Simulations.PowerFlow.steady_state.power_flow_runnable import PowerFlow
from GridCal.Engine.Simulations.PowerFlow.steady_state.power_flow_options import \
    PowerFlowOptions
from GridCal.Engine.Simulations.PowerFlow.steady_state.solver_type import SolverType
from GridCal.print_power_flow_results import print_power_flow_results
from tests.conftest import ROOT_PATH


def test_demo_5_node(root_path):
    np.core.arrayprint.set_printoptions(precision=4)

    grid = MultiCircuit()

    # Add buses
    bus_1 = Bus('Bus 1', vnom=20)
    # bus_1.is_slack = True
    grid.add_bus(bus_1)
    gen1 = Generator('Slack Generator', voltage_module=1.0)
    grid.add_generator(bus_1, gen1)

    bus_2 = Bus('Bus 2', vnom=20)
    grid.add_bus(bus_2)
    grid.add_load(bus_2, Load('load 2', P=40, Q=20))

    bus_3 = Bus('Bus 3', vnom=20)
    grid.add_bus(bus_3)
    grid.add_load(bus_3, Load('load 3', P=25, Q=15))

    bus_4 = Bus('Bus 4', vnom=20)
    grid.add_bus(bus_4)
    grid.add_load(bus_4, Load('load 4', P=40, Q=20))

    bus_5 = Bus('Bus 5', vnom=20)
    grid.add_bus(bus_5)
    grid.add_load(bus_5, Load('load 5', P=50, Q=20))

    # add branches (Lines in this case)
    grid.add_branch(Branch(bus_1, bus_2, 'line 1-2', r=0.05, x=0.11, b=0.02))
    grid.add_branch(Branch(bus_1, bus_3, 'line 1-3', r=0.05, x=0.11, b=0.02))
    grid.add_branch(Branch(bus_1, bus_5, 'line 1-5', r=0.03, x=0.08, b=0.02))
    grid.add_branch(Branch(bus_2, bus_3, 'line 2-3', r=0.04, x=0.09, b=0.02))
    grid.add_branch(Branch(bus_2, bus_5, 'line 2-5', r=0.04, x=0.09, b=0.02))
    grid.add_branch(Branch(bus_3, bus_4, 'line 3-4', r=0.06, x=0.13, b=0.03))
    grid.add_branch(Branch(bus_4, bus_5, 'line 4-5', r=0.04, x=0.09, b=0.02))
    # grid.plot_graph()
    print('\n\n', grid.name)

    options = PowerFlowOptions(SolverType.NR, verbose=False)

    power_flow = PowerFlow(grid, options)
    power_flow.run()

    print_power_flow_results(power_flow=power_flow)

    # fname = root_path / 'data' / 'output' / 'test_demo_5_node.png'
    # plt.savefig(fname=fname)


if __name__ == '__main__':
    test_demo_5_node(root_path=ROOT_PATH)
