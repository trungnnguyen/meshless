import os
import inspect

import numpy as np
from scipy.sparse import coo_matrix

from meshless.composite.laminate import read_stack
from meshless.sparse import solve
from meshless.linear_buckling import lb
from meshless.espim.read_mesh import read_mesh
from meshless.espim.plate2d_calc_k0 import calc_k0
from meshless.espim.plate2d_calc_kG import calc_kG
from meshless.espim.plate2d_add_k0s import add_k0s

THISDIR = os.path.dirname(inspect.getfile(inspect.currentframe()))

def test_calc_linear_buckling():
    do_plot = False
    E11 = 71.e9
    nu = 0.33
    plyt = 0.007
    lam = read_stack([0], plyt=plyt, laminaprop=(E11, E11, nu))
    ans = {'edge-based': 6.310135, 'cell-based': 7.59683,
            'cell-based-no-smoothing': 5.3855713}
    for prop_from_nodes in [True, False]:
        for k0s_method in ['edge-based', 'cell-based', 'cell-based-no-smoothing']:
            nodes, trias, edges = read_mesh(os.path.join(THISDIR, 'nastran_plate_16_nodes.dat'))
            for tria in trias:
                tria.prop = lam
            for node in nodes:
                node.prop = lam
            k0 = calc_k0(nodes, trias, edges, prop_from_nodes)
            add_k0s(k0, edges, trias, prop_from_nodes, k0s_method)

            # running static subcase first
            dof = 5
            n = k0.shape[0] // 5
            fext = np.zeros(n*dof, dtype=np.float64)
            fext[nodes[3].index*dof + 0] = -500.
            fext[nodes[4].index*dof + 0] = -1000.
            fext[nodes[5].index*dof + 0] = -1000.
            fext[nodes[6].index*dof + 0] = -500.

            # boundary conditions
            def bc(K):
                for i in [0, 9, 10, 11]:
                    for j in [0, 1, 2]:
                        K[nodes[i].index*dof+j, :] = 0
                        K[:, nodes[i].index*dof+j] = 0

                for i in [1, 2, 3, 4, 5, 6, 7, 8]:
                    for j in [1, 2]:
                        K[nodes[i].index*dof+j, :] = 0
                        K[:, nodes[i].index*dof+j] = 0

            bc(k0)
            k0 = coo_matrix(k0)
            d = solve(k0, fext, silent=True)
            kG = calc_kG(d, edges, prop_from_nodes)
            bc(kG)
            kG = coo_matrix(kG)

            eigvals, eigvecs = lb(k0, kG, silent=True)
            assert np.isclose(eigvals[0], ans[k0s_method])

            if do_plot:
                do_plot = False
                import matplotlib.pyplot as plt
                ind0 = np.array([[n.index, i] for (i, n) in enumerate(nodes)])
                ind0 = ind0[np.argsort(ind0[:, 0])]
                nodes = np.array(nodes)[ind0[:, 1]]
                xyz = np.array([n.xyz for n in nodes])
                ind = np.lexsort((xyz[:, 1], xyz[:, 0]))
                w = eigvecs[:, 0][2::5][ind]
                #w = d[0::5][ind]
                xyz = xyz[ind]
                levels = np.linspace(w.min(), w.max(), 400)
                plt.figure(dpi=100)
                plt.contourf(xyz[:, 0].reshape(4, 4), xyz[:, 1].reshape(4, 4), w.reshape(4, 4),
                        levels=levels)
                plt.show()

if __name__ == '__main__':
    test_calc_linear_buckling()

