#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-License-Identifier: Apache-2.0
# Copyright 2022 Stéphane Caron
# Copyright 2023-2024 Inria

"""Free-for-all test set."""

import os
from typing import Iterator, Union

import numpy as np
import qpbenchmark
import scipy.io as spio
import scipy.sparse as spa
from qpbenchmark.benchmark import main
from qpbenchmark.problem import Problem


class FreeForAll(qpbenchmark.TestSet):
    """Free-for-all test set.

    Note:
        This test set is open to proposals from the community. Feel free to
        `submit a new problem
        <https://github.com/qpsolvers/free_for_all_qpbenchmark/issues/new?template=new_problem.md>`__.
    """

    @property
    def description(self) -> str:
        return "Community-built test set to benchmark QP solvers."

    @property
    def title(self) -> str:
        return "Free-for-all test set"

    @property
    def sparse_only(self) -> bool:
        return True

    def __init__(self):
        """Initialize test set."""
        super().__init__()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, "data")
        self.data_dir = data_dir
        self.__add_known_solver_issues()
        self.__add_known_solver_timeouts()

    def __add_known_solver_issues(self):
        self.known_solver_issues.add(("CONT-100", "highs"))
        self.known_solver_issues.add(("CONT-101", "highs"))
        self.known_solver_issues.add(("CONT-200", "highs"))
        self.known_solver_issues.add(("CONT-201", "highs"))
        self.known_solver_issues.add(("CONT-300", "highs"))

    def __add_known_solver_timeouts(self):
        minutes = 60.0  # [s]
        self.known_solver_timeouts.update(
            {
                ("CONT-100", "proxqp", "*"): 5 * minutes,
                ("CONT-101", "proxqp", "*"): 30 * minutes,
                ("CONT-200", "cvxopt", "*"): 5 * minutes,
                ("CONT-200", "proxqp", "*"): 20 * minutes,
                ("CONT-201", "cvxopt", "*"): 3 * minutes,
                ("CONT-201", "proxqp", "*"): 30 * minutes,
                ("CONT-300", "cvxopt", "*"): 20 * minutes,
                ("CONT-300", "proxqp", "*"): 60 * minutes,
            }
        )

    def load_problem_from_mat_file(self, path):
        """Load problem from MAT file.

        Args:
            path: Path to file.

        Notes:
            We assume that matrix files result from calling `sif2mat.m` in
            proxqp_benchmark. In particular, ``A = [sparse(A_c); speye(n)];``
            and the infinity constant is set to 1e20.
        """
        assert path.endswith(".mat")
        name = os.path.basename(path)[:-4]

        mat_dict = spio.loadmat(path)
        P = mat_dict["P"].astype(float).tocsc()
        q = mat_dict["q"].T.flatten().astype(float)
        A = mat_dict["A"].astype(float).tocsc()
        l = mat_dict["l"].T.flatten().astype(float)
        u = mat_dict["u"].T.flatten().astype(float)
        n = mat_dict["n"].T.flatten().astype(int)[0]
        m = mat_dict["m"].T.flatten().astype(int)[0]
        assert A.shape == (m, n)

        # Infinity constant is 1e20
        A[A > +9e19] = +np.inf
        l[l > +9e19] = +np.inf
        u[u > +9e19] = +np.inf
        A[A < -9e19] = -np.inf
        l[l < -9e19] = -np.inf
        u[u < -9e19] = -np.inf

        # A == vstack([C, spa.eye(n)])
        lb = l[-n:]
        ub = u[-n:]
        C = A[:-n]
        l_c = l[:-n]
        u_c = u[:-n]

        return self.convert_problem_from_double_sided(
            P, q, C, l_c, u_c, lb, ub, name=name
        )

    @staticmethod
    def convert_problem_from_double_sided(
        P: Union[np.ndarray, spa.csc_matrix],
        q: np.ndarray,
        C: Union[np.ndarray, spa.csc_matrix],
        l: np.ndarray,
        u: np.ndarray,
        lb: np.ndarray,
        ub: np.ndarray,
        name: str,
    ):
        """Load problem from double-sided inequality format.

        Double-sided format is as follows:

        .. code::

            minimize        0.5 x^T P x + q^T x
            subject to      l <= C x <= u
                            lb <= x <= ub

        Args:
            P: Cost matrix.
            q: Cost vector.
            C: Constraint inequality matrix.
            l: Constraint lower bound.
            u: Constraint upper bound.
            lb: Box lower bound.
            ub: Box upper bound.
            name: Problem name.
        """
        bounds_are_equal = u - l < 1e-10

        eq_rows = np.asarray(bounds_are_equal).nonzero()
        A = C[eq_rows]
        b = u[eq_rows]

        ineq_rows = np.asarray(np.logical_not(bounds_are_equal)).nonzero()
        G = spa.vstack([C[ineq_rows], -C[ineq_rows]], format="csc")
        h = np.hstack([u[ineq_rows], -l[ineq_rows]])
        h_finite = h < np.inf
        if not h_finite.all():
            G = G[h_finite]
            h = h[h_finite]

        return qpbenchmark.Problem(
            P,
            q,
            G if G.size > 0 else None,
            h if h.size > 0 else None,
            A if A.size > 0 else None,
            b if b.size > 0 else None,
            lb,
            ub,
            name=name,
        )

    def __iter__(self) -> Iterator[Problem]:
        """Iterate over test set problems."""
        for fname in os.listdir(self.data_dir):
            if fname.endswith(".npz"):
                yield Problem.load(os.path.join(self.data_dir, fname))
            elif fname.endswith(".mat"):
                mat_path = os.path.join(self.data_dir, fname)
                problem = self.load_problem_from_mat_file(mat_path)
                yield problem


if __name__ == "__main__":
    test_set_path = os.path.abspath(__file__)
    test_set_dir = os.path.dirname(test_set_path)
    main(
        test_set_path=test_set_path,
        results_path=f"{test_set_dir}/results/qpbenchmark_results.csv",
    )
