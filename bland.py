import sys
sys.stdout.reconfigure(encoding='utf-8')

global_steps = []

def transform_problem(problem_type, num_vars, num_constraints, c, t, i_vec, mt, b):
    old_problem_type = problem_type
    old_t = t.copy()
    old_i = i_vec.copy()

    if problem_type == 1:
        c = [-ci for ci in c]
    new_problem_type = -1

    original_n_vars = num_vars
    num_rows = len(mt)

    mt_transformed = [[] for _ in range(num_rows)]
    c_transformed = []
    new_i = []

    for x in range(original_n_vars):
        cx = c[x]
        col = [mt[r][x] for r in range(num_rows)]
        if i_vec[x] == 1:
            c_transformed.append(cx)
            new_i.append(1)
            for r in range(num_rows):
                mt_transformed[r].append(col[r])
        elif i_vec[x] == -1:
            c_transformed.append(-cx)
            new_i.append(1)
            for r in range(num_rows):
                mt_transformed[r].append(-col[r])
        elif i_vec[x] == 0:
            c_transformed.append(cx)
            new_i.append(1)
            for r in range(num_rows):
                mt_transformed[r].append(col[r])
            c_transformed.append(-cx)
            new_i.append(1)
            for r in range(num_rows):
                mt_transformed[r].append(-col[r])
        else:
            raise ValueError(f"i_vec[{x}] must be -1, 0 or 1.")

    new_t = []
    new_b = []
    new_mt2 = []
    for r in range(len(old_t)):
        tr = old_t[r]
        row = mt_transformed[r]
        br = b[r]
        if tr == 1:
            new_row = [-val for val in row]
            new_bval = -br
            new_t.append(-1)
            new_mt2.append(new_row)
            new_b.append(new_bval)
        elif tr == -1:
            new_t.append(-1)
            new_mt2.append(row.copy())
            new_b.append(br)
        elif tr == 0:
            new_t.append(-1)
            new_mt2.append(row.copy())
            new_b.append(br)
            new_t.append(-1)
            new_mt2.append([-val for val in row])
            new_b.append(-br)
        else:
            raise ValueError(f"t[{r}] must be -1, 0 or 1.")

    return (
        old_problem_type, old_t, old_i,
        new_problem_type, new_t, new_i,
        c_transformed, new_mt2, new_b
    )

def bland_rule(c, A, b, old_i, old_problem_type):
    global global_steps
    global_steps.clear()
    m = len(A)
    if m == 0:
        x0 = [0.0] * len(c)
        xt0 = []
        ptr = 0
        for iv in old_i:
            if iv == 1:
                xt0.append(x0[ptr]); ptr += 1
            elif iv == -1:
                xt0.append(-x0[ptr]); ptr += 1
            else:
                xt0.append(x0[ptr] - x0[ptr+1]); ptr += 2
        return {"objective": 0.0, "x": x0, "xt": xt0, "status": "optimal"}

    n = len(A[0])
    N = n + m

    col_names = [f"x{j+1}" for j in range(n)] + [f"s{i+1}" for i in range(m)]
    tableau = [[0.0] * (N + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(n):
            tableau[i][j] = float(A[i-1][j])
        tableau[i][n + (i-1)] = 1.0
        tableau[i][N] = float(b[i-1])

    for j in range(n):
        tableau[0][j] = float(c[j])

    basic_vars = [n + i for i in range(m)]

    def record_step(tab, basic_vars, entering=None, leaving=None):
        global_steps.append({
            "tableau": [row[:] for row in tab],
            "basis": [col_names[idx] for idx in basic_vars],
            "col_names": list(col_names),
            "entering": entering,
            "leaving": leaving
        })

    record_step(tableau, basic_vars)

    while True:
        entering = None
        for j in range(N):
            if tableau[0][j] < 0:
                entering = j
                break

        if entering is None:
            break

        ratios = [float('inf')] * (m + 1)
        for i in range(1, m + 1):
            aij = tableau[i][entering]
            if aij > 0:
                ratios[i] = tableau[i][N] / aij

        if all(tableau[i][entering] <= 0 for i in range(1, m + 1)):
            return {"objective": None, "x": None, "xt": None, "status": "unbounded"}

        leaving = None
        min_ratio = float('inf')
        for i in range(1, m + 1):
            if ratios[i] < min_ratio - 1e-12:
                min_ratio = ratios[i]
                leaving = i
            elif abs(ratios[i] - min_ratio) <= 1e-12:
                if leaving is not None and basic_vars[i-1] < basic_vars[leaving-1]:
                    leaving = i

        old_basic = basic_vars[leaving-1]
        
        global_steps[-1]["entering"] = col_names[entering]
        global_steps[-1]["leaving"] = col_names[old_basic]

        pivot_val = tableau[leaving][entering]
        for j in range(N + 1):
            tableau[leaving][j] /= pivot_val
        for i in range(m + 1):
            if i == leaving:
                continue
            factor = tableau[i][entering]
            if abs(factor) > 1e-12:
                for j in range(N + 1):
                    tableau[i][j] -= factor * tableau[leaving][j]

        basic_vars[leaving-1] = entering
        record_step(tableau, basic_vars)

    x = [0.0] * n
    for i in range(1, m + 1):
        idx = basic_vars[i-1]
        if idx < n:
            val = tableau[i][N]
            x[idx] = 0.0 if abs(val) < 1e-9 else val

    obj = tableau[0][N] * old_problem_type
    if abs(obj) < 1e-9:
        obj = 0.0

    xt = []
    ptr = 0
    for iv in old_i:
        if iv == 1:
            xt.append(x[ptr]); ptr += 1
        elif iv == -1:
            xt.append(-x[ptr]); ptr += 1
        else:
            xt.append(x[ptr] - x[ptr+1]); ptr += 2

    return {"objective": obj, "x": x, "xt": xt, "status": "optimal"}
