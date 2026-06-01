import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


global_steps = []


def transform_problem(problem_type, num_vars, num_constraints, c, t, i_vec, mt, b):
    


    old_problem_type = problem_type
    old_t = t.copy()
    old_i = i_vec.copy()

    if problem_type not in [-1, 1]:
        raise ValueError("problem_type must be -1 for Min or 1 for Max.")

    if len(c) != num_vars:
        raise ValueError("Length of c must match num_vars.")

    if len(i_vec) != num_vars:
        raise ValueError("Length of i_vec must match num_vars.")

    if len(t) != num_constraints:
        raise ValueError("Length of t must match num_constraints.")

    if len(mt) != num_constraints:
        raise ValueError("Number of rows in mt must match num_constraints.")

    if len(b) != num_constraints:
        raise ValueError("Length of b must match num_constraints.")

    for row in mt:
        if len(row) != num_vars:
            raise ValueError("Each row in mt must have num_vars elements.")

    # Đưa Max về Min bằng cách đổi dấu hàm mục tiêu.
    if problem_type == 1:
        c = [-ci for ci in c]

    new_problem_type = -1

    original_n_vars = num_vars
    num_rows = len(mt)

    mt_transformed = [[] for _ in range(num_rows)]
    c_transformed = []
    new_i = []

    # Xử lý điều kiện dấu của biến.
    for x in range(original_n_vars):
        cx = c[x]
        col = [mt[r][x] for r in range(num_rows)]

        # x >= 0: giữ nguyên
        if i_vec[x] == 1:
            c_transformed.append(cx)
            new_i.append(1)

            for r in range(num_rows):
                mt_transformed[r].append(col[r])

        # x <= 0: đặt x = -x'
        elif i_vec[x] == -1:
            c_transformed.append(-cx)
            new_i.append(1)

            for r in range(num_rows):
                mt_transformed[r].append(-col[r])

        # x tự do: đặt x = x+ - x-
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

    # Đưa ràng buộc về dạng <=.
    for r in range(len(old_t)):
        tr = old_t[r]
        row = mt_transformed[r]
        br = b[r]

        # >= chuyển thành <= bằng cách nhân -1.
        if tr == 1:
            new_row = [-val for val in row]
            new_bval = -br

            new_t.append(-1)
            new_mt2.append(new_row)
            new_b.append(new_bval)

        # <= giữ nguyên.
        elif tr == -1:
            new_t.append(-1)
            new_mt2.append(row.copy())
            new_b.append(br)

        # = tách thành hai ràng buộc <=.
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
        old_problem_type,
        old_t,
        old_i,
        new_problem_type,
        new_t,
        new_i,
        c_transformed,
        new_mt2,
        new_b
    )


def simplex(c, A, b, old_i, old_problem_type):
    """
    Simplex thường.

    Lưu ý:
    - Hàm này giả định nghiệm cơ sở ban đầu khả thi.
    - Tức là sau khi chuẩn hóa, các RHS b_i nên >= 0.
    - Nếu có b_i âm, nên dùng Simplex 2 pha thay vì hàm này.
    """

    global global_steps
    global_steps.clear()

    steps = []

    m = len(A)

    # Trường hợp không có ràng buộc.
    if m == 0:
        x0 = [0.0] * len(c)

        xt0 = []
        ptr = 0

        for iv in old_i:
            if iv == 1:
                xt0.append(x0[ptr])
                ptr += 1

            elif iv == -1:
                xt0.append(-x0[ptr])
                ptr += 1

            else:
                xt0.append(x0[ptr] - x0[ptr + 1])
                ptr += 2

        result = {
            "objective": 0.0,
            "x": x0,
            "xt": xt0,
            "status": "optimal",
            "steps": steps
        }

        return result

    n = len(A[0])

    if len(c) != n:
        raise ValueError("Length of c must match the number of columns in A.")

    if len(b) != m:
        raise ValueError("Length of b must match the number of rows in A.")

    for row in A:
        if len(row) != n:
            raise ValueError("All rows in A must have the same length.")

    # Simplex thường cần RHS không âm để slack basis ban đầu khả thi.
    # Ở app.py bạn đã chặn case này rồi, nhưng giữ thêm ở đây cho an toàn.
    if any(bi < -1e-9 for bi in b):
        return {
            "objective": None,
            "x": None,
            "xt": None,
            "status": "initial_basis_infeasible",
            "message": "RHS có giá trị âm. Hãy dùng phương pháp Đơn hình 2 pha.",
            "steps": steps
        }

    N = n + m

    col_names = [f"x{j + 1}" for j in range(n)] + [f"s{i + 1}" for i in range(m)]

    # Tableau có m dòng ràng buộc + 1 dòng mục tiêu.
    # Cột cuối cùng là RHS.
    tableau = [[0.0] * (N + 1) for _ in range(m + 1)]

    # Ghi các ràng buộc.
    for i in range(1, m + 1):
        for j in range(n):
            tableau[i][j] = float(A[i - 1][j])

        # Slack variable.
        tableau[i][n + (i - 1)] = 1.0

        # RHS.
        tableau[i][N] = float(b[i - 1])

    # Ghi hàm mục tiêu.
    for j in range(n):
        tableau[0][j] = float(c[j])

    # Ban đầu slack variables là biến cơ sở.
    basic_vars = [n + i for i in range(m)]

    def record_step(tab, basis, entering=None, leaving=None):
        step = {
            "tableau": [row[:] for row in tab],
            "basis": [col_names[idx] for idx in basis],
            "col_names": list(col_names),
            "entering": entering,
            "leaving": leaving
        }

        steps.append(step)
        global_steps.append(step)

    record_step(tableau, basic_vars)

    while True:
        entering = None
        min_cost = 0.0

        # Chọn biến vào: hệ số âm nhất trên dòng mục tiêu.
        for j in range(N):
            if tableau[0][j] < min_cost:
                min_cost = tableau[0][j]
                entering = j

        # Không còn hệ số âm => tối ưu.
        if entering is None:
            break

        # Kiểm tra không giới nội.
        if all(tableau[i][entering] <= 1e-12 for i in range(1, m + 1)):
            return {
                "objective": None,
                "x": None,
                "xt": None,
                "status": "unbounded",
                "steps": steps
            }

        ratios = [float('inf')] * (m + 1)

        for i in range(1, m + 1):
            aij = tableau[i][entering]

            if aij > 1e-12:
                ratios[i] = tableau[i][N] / aij

        leaving = None
        min_ratio = float('inf')

        # Chọn biến ra theo minimum ratio test.
        for i in range(1, m + 1):
            if ratios[i] < min_ratio - 1e-12:
                min_ratio = ratios[i]
                leaving = i

        if leaving is None:
            return {
                "objective": None,
                "x": None,
                "xt": None,
                "status": "unbounded",
                "steps": steps
            }

        old_basic = basic_vars[leaving - 1]

        # Ghi biến vào/ra cho bước hiện tại.
        steps[-1]["entering"] = col_names[entering]
        steps[-1]["leaving"] = col_names[old_basic]

        global_steps[-1]["entering"] = col_names[entering]
        global_steps[-1]["leaving"] = col_names[old_basic]

        # Pivot.
        pivot_val = tableau[leaving][entering]

        if abs(pivot_val) < 1e-12:
            return {
                "objective": None,
                "x": None,
                "xt": None,
                "status": "numerical_error",
                "message": "Pivot quá nhỏ, có thể gây lỗi số học.",
                "steps": steps
            }

        # Chuẩn hóa dòng pivot.
        for j in range(N + 1):
            tableau[leaving][j] /= pivot_val

        # Khử các dòng còn lại.
        for i in range(m + 1):
            if i == leaving:
                continue

            factor = tableau[i][entering]

            if abs(factor) > 1e-12:
                for j in range(N + 1):
                    tableau[i][j] -= factor * tableau[leaving][j]

        basic_vars[leaving - 1] = entering

        record_step(tableau, basic_vars)

    # Trích nghiệm trên các biến đã chuẩn hóa.
    x = [0.0] * n

    for i in range(1, m + 1):
        idx = basic_vars[i - 1]

        if idx < n:
            val = tableau[i][N]
            x[idx] = 0.0 if abs(val) < 1e-9 else val

    # Đổi dấu giá trị mục tiêu về loại bài toán ban đầu.
    obj = tableau[0][N] * old_problem_type

    if abs(obj) < 1e-9:
        obj = 0.0

    # Khôi phục nghiệm theo biến gốc.
    xt = []
    ptr = 0

    for iv in old_i:
        if iv == 1:
            xt.append(x[ptr])
            ptr += 1

        elif iv == -1:
            xt.append(-x[ptr])
            ptr += 1

        else:
            val = x[ptr] - x[ptr + 1]
            xt.append(val)
            ptr += 2

    return {
        "objective": obj,
        "x": x,
        "xt": xt,
        "status": "optimal",
        "steps": steps
    }
