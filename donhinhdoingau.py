import numpy as np

global_steps = []

def dual_simplex_min(A, b, c):
    global global_steps
    global_steps.clear()

    m, n = A.shape

    A_ext = np.hstack((A.astype(float), np.eye(m, dtype=float)))
    total_vars = n + m

    var_names = [f"x{j+1}" for j in range(n)] + [f"s{i+1}" for i in range(m)]
    basis = [f"s{i+1}" for i in range(m)]

    tableau = np.zeros((m+1, total_vars+1))
    tableau[:m, :total_vars] = A_ext
    tableau[:m, -1] = b.astype(float)
    tableau[-1, :n] = c.astype(float)
    tableau[-1, n:] = 0.0
    tableau[-1, -1] = 0.0

    def record_step(tbl, basis, entering=None, leaving=None):
        global_steps.append({
            "tableau": tbl.tolist(),
            "basis": list(basis),
            "col_names": list(var_names),
            "entering": entering,
            "leaving": leaving
        })

    record_step(tableau, basis)

    def pivot_dual(tbl, basis):
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
            raise ValueError("LP infeasible (Dual phase).")

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

    def pivot_primal(tbl, basis):
        rows, cols = tbl.shape
        num_vars = cols - 1

        obj_row = tbl[-1, :num_vars]
        entering_idx = int(np.argmin(obj_row))
        if obj_row[entering_idx] >= -1e-9:
            return None, None, True

        ratios = np.full(m, np.inf)
        for i in range(m):
            a_ij = tbl[i, entering_idx]
            if a_ij > 1e-9:
                ratios[i] = tbl[i, -1] / a_ij
        leaving_idx = int(np.argmin(ratios))
        if ratios[leaving_idx] == np.inf:
            raise ValueError("LP unbounded (Primal phase).")

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

    while True:
        rhs = tableau[:m, -1]
        if np.any(rhs < -1e-9):
            entering, leaving, is_opt = pivot_dual(tableau, basis)
            if is_opt:
                record_step(tableau, basis)
            else:
                record_step(tableau, basis)
            continue

        obj_row = tableau[-1, :total_vars]
        if np.any(obj_row < -1e-9):
            entering, leaving, is_opt = pivot_primal(tableau, basis)
            if is_opt:
                record_step(tableau, basis)
                break
            else:
                record_step(tableau, basis)
            continue

        record_step(tableau, basis)
        break

    x_vals = np.zeros(total_vars)
    for i in range(m):
        var = basis[i]
        idx = var_names.index(var)
        x_vals[idx] = tableau[i, -1]

    solution = {f"x{j+1}": float(x_vals[j]) for j in range(n)}
    optimal_value = float(np.dot(c, np.array([solution[f"x{j+1}"] for j in range(n)])))

    return solution, optimal_value
