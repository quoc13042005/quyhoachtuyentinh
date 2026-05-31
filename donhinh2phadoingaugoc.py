import numpy as np

global_steps = []

def two_phase_dual_original_min(A, b, c):
    global global_steps
    global_steps.clear()

    m, n = A.shape

    A_ext = np.hstack((A.astype(float), np.eye(m, dtype=float)))
    var_names = [f"x{j+1}" for j in range(n)] + [f"s{i+1}" for i in range(m)]
    basis = [f"s{i+1}" for i in range(m)]
    total_vars = n + m

    tableau = np.zeros((m+1, total_vars+1))
    tableau[:m, :total_vars] = A_ext
    tableau[:m, -1] = b.astype(float)
    for j in range(n):
        tableau[-1, j] = abs(c[j])
    
    for i in range(m):
        tableau[-1, :] -= tableau[i, :]

    def record_step(tbl, basis, entering=None, leaving=None):
        global_steps.append({
            "tableau": tbl.tolist(),
            "basis": list(basis),
            "col_names": list(var_names),
            "entering": entering,
            "leaving": leaving
        })

    record_step(tableau, basis)

    def dual_pivot(tbl, basis):
        rows, cols = tbl.shape
        num_vars = cols - 1

        rhs = tbl[:m, -1]
        leaving_idx = int(np.argmin(rhs))
        if rhs[leaving_idx] >= -1e-9:
            return None, None, True

        row_k = tbl[leaving_idx, :num_vars]
        obj_row = tbl[-1, :num_vars]
        candidates = []
        for j in range(num_vars):
            if row_k[j] < -1e-9:
                ratio = obj_row[j] / row_k[j]
                candidates.append((ratio, j))
        if not candidates:
            raise ValueError("Auxiliary LP is infeasible.")

        _, entering_idx = min(candidates, key=lambda x: x[0])

        entering_var = var_names[entering_idx]
        leaving_var = basis[leaving_idx]
        global_steps[-1]["entering"] = entering_var
        global_steps[-1]["leaving"] = leaving_var

        pivot_val = tbl[leaving_idx, entering_idx]
        tbl[leaving_idx, :] /= pivot_val
        for i in range(rows):
            if i != leaving_idx:
                tbl[i, :] -= tbl[i, entering_idx] * tbl[leaving_idx, :]

        basis[leaving_idx] = entering_var
        return entering_var, leaving_var, False

    try:
        while True:
            entering, leaving, done = dual_pivot(tableau, basis)
            if done:
                record_step(tableau, basis)
                break
            record_step(tableau, basis)
    except ValueError:
        return None, None

    w_val = tableau[-1, -1]
    if w_val > 1e-8:
        return None, None

    tableau[-1, :] = 0.0
    for j in range(n):
        tableau[-1, j] = -c[j]
        
    for i in range(m):
        var = basis[i]
        idx = var_names.index(var)
        coef = tableau[-1, idx]
        if abs(coef) > 1e-12:
            tableau[-1, :] -= coef * tableau[i, :]

    record_step(tableau, basis)

    def primal_pivot(tbl, basis):
        rows, cols = tbl.shape
        num_vars = cols - 1

        obj_row = tbl[-1, :num_vars]
        entering_idx = int(np.argmax(obj_row))
        if obj_row[entering_idx] <= 1e-9:
            return None, None, True

        ratios = np.full(m, np.inf)
        for i in range(m):
            a_ij = tbl[i, entering_idx]
            if a_ij > 1e-9:
                ratios[i] = tbl[i, -1] / a_ij
        leaving_idx = int(np.argmin(ratios))
        if ratios[leaving_idx] == np.inf:
            raise ValueError("Original LP is unbounded.")

        entering_var = var_names[entering_idx]
        leaving_var = basis[leaving_idx]
        global_steps[-1]["entering"] = entering_var
        global_steps[-1]["leaving"] = leaving_var

        pivot_val = tbl[leaving_idx, entering_idx]
        tbl[leaving_idx, :] /= pivot_val
        for i in range(rows):
            if i != leaving_idx:
                tbl[i, :] -= tbl[i, entering_idx] * tbl[leaving_idx, :]

        basis[leaving_idx] = entering_var
        return entering_var, leaving_var, False

    try:
        while True:
            entering, leaving, done = primal_pivot(tableau, basis)
            if done:
                record_step(tableau, basis)
                break
            record_step(tableau, basis)
    except ValueError:
        return None, None

    x_vals = np.zeros(total_vars)
    for i in range(m):
        var = basis[i]
        idx = var_names.index(var)
        x_vals[idx] = tableau[i, -1]

    solution = {f"x{j+1}": float(x_vals[j]) for j in range(n)}
    optimal_value = float(np.dot(c, np.array([solution[f"x{j+1}"] for j in range(n)])))
    return solution, optimal_value
