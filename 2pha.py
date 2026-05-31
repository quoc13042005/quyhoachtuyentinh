import numpy as np

global_steps = []

def two_phase_simplex_min(A, b, c):
    global global_steps
    global_steps.clear()

    m, n = A.shape
    total_vars = n + m + 1  # x_1..x_n, s_1..s_m, x_0
    
    var_names = [f"x{j+1}" for j in range(n)] + [f"s{i+1}" for i in range(m)] + ["x0"]
    basis = [f"s{i+1}" for i in range(m)]
    
    # tableau: m rows for constraints, 1 row for objective
    tableau = np.zeros((m+1, total_vars+1))
    
    for i in range(m):
        tableau[i, :n] = A[i]
        tableau[i, n+i] = 1.0        # slack
        tableau[i, total_vars-1] = -1.0  # x_0 coefficient is -1 in LHS
        tableau[i, -1] = b[i]
        
    def record_step(tbl, basis, obj_name, entering=None, leaving=None):
        global_steps.append({
            "tableau": tbl.tolist(),
            "basis": list(basis),
            "col_names": list(var_names),
            "obj_name": obj_name,
            "entering": entering,
            "leaving": leaving
        })

    # Kiểm tra nếu cần Pha 1 (có b_i < 0)
    needs_phase1 = np.any(b < -1e-9)
    
    if needs_phase1:
        # Mục tiêu Pha 1: epsilon = x0 (minimize) -> trong dictionary coeff của x0 là 1
        tableau[m, total_vars-1] = 1.0
        tableau[m, -1] = 0.0
        
        record_step(tableau, basis, "&epsilon;")
        
        # Special Pivot: x0 enters, biến có b_i âm nhất leaves
        leaving_idx = int(np.argmin(b))
        entering_idx = total_vars - 1 # x0
        
        entering_var = var_names[entering_idx]
        leaving_var = basis[leaving_idx]
        global_steps[-1]["entering"] = entering_var
        global_steps[-1]["leaving"] = leaving_var
        
        # Pivot
        pivot_val = tableau[leaving_idx, entering_idx]
        tableau[leaving_idx, :] /= pivot_val
        for i in range(m+1):
            if i != leaving_idx:
                tableau[i, :] -= tableau[i, entering_idx] * tableau[leaving_idx, :]
                
        basis[leaving_idx] = entering_var
        record_step(tableau, basis, "&epsilon;")
        
        # Vòng lặp Pha 1 (Minimize epsilon)
        while True:
            # Chọn biến vào có hệ số âm lớn nhất (để Minimize epsilon)
            obj_row = tableau[m, :-1]
            entering_idx = int(np.argmin(obj_row))
            if obj_row[entering_idx] >= -1e-9:
                break # Tối ưu Pha 1
                
            ratios = np.full(m, np.inf)
            for i in range(m):
                if tableau[i, entering_idx] > 1e-9:
                    ratios[i] = tableau[i, -1] / tableau[i, entering_idx]
                    
            leaving_idx = int(np.argmin(ratios))
            if ratios[leaving_idx] == np.inf:
                return "unbounded", None # Không giới hạn (không thể xảy ra trong Pha 1)
                
            entering_var = var_names[entering_idx]
            leaving_var = basis[leaving_idx]
            global_steps[-1]["entering"] = entering_var
            global_steps[-1]["leaving"] = leaving_var
            
            pivot_val = tableau[leaving_idx, entering_idx]
            tableau[leaving_idx, :] /= pivot_val
            for i in range(m+1):
                if i != leaving_idx:
                    tableau[i, :] -= tableau[i, entering_idx] * tableau[leaving_idx, :]
                    
            basis[leaving_idx] = entering_var
            record_step(tableau, basis, "&epsilon;")
            
        # Kiểm tra tính khả thi
        if abs(tableau[m, -1]) > 1e-9:
            return "infeasible", None # Vô nghiệm
            
        # Nếu x0 vẫn nằm trong cơ sở (với giá trị 0), đẩy nó ra
        if "x0" in basis:
            row_idx = basis.index("x0")
            pivot_col = -1
            for j in range(total_vars - 1): # Bỏ qua x0
                if abs(tableau[row_idx, j]) > 1e-9:
                    pivot_col = j
                    break
            if pivot_col != -1:
                entering_var = var_names[pivot_col]
                leaving_var = "x0"
                global_steps[-1]["entering"] = entering_var
                global_steps[-1]["leaving"] = leaving_var
                
                pivot_val = tableau[row_idx, pivot_col]
                tableau[row_idx, :] /= pivot_val
                for i in range(m+1):
                    if i != row_idx:
                        tableau[i, :] -= tableau[i, pivot_col] * tableau[row_idx, :]
                basis[row_idx] = entering_var
                record_step(tableau, basis, "&epsilon;")
                
    # Vứt bỏ x0
    x0_idx = var_names.index("x0")
    tableau = np.delete(tableau, x0_idx, axis=1)
    var_names.pop(x0_idx)
    total_vars -= 1
    
    # Thiết lập Pha 2 (Minimize z' = c^T x)
    tableau[m, :] = 0.0
    for j in range(n):
        tableau[m, j] = c[j] # Hiển thị z' = c_1 x_1 + c_2 x_2
        
    for i in range(m):
        var = basis[i]
        idx = var_names.index(var)
        factor = tableau[m, idx]
        if abs(factor) > 1e-12:
            tableau[m, :] -= factor * tableau[i, :]
            
    record_step(tableau, basis, "z'")
    
    # Vòng lặp Pha 2 (Minimize z')
    while True:
        obj_row = tableau[m, :-1]
        entering_idx = int(np.argmin(obj_row))
        
        # Nếu không còn hệ số âm -> Tối ưu
        if obj_row[entering_idx] >= -1e-9:
            break 
            
        ratios = np.full(m, np.inf)
        for i in range(m):
            if tableau[i, entering_idx] > 1e-9:
                ratios[i] = tableau[i, -1] / tableau[i, entering_idx]
                
        leaving_idx = int(np.argmin(ratios))
        if ratios[leaving_idx] == np.inf:
            return "unbounded", None # Không giới hạn
            
        entering_var = var_names[entering_idx]
        leaving_var = basis[leaving_idx]
        global_steps[-1]["entering"] = entering_var
        global_steps[-1]["leaving"] = leaving_var
        
        pivot_val = tableau[leaving_idx, entering_idx]
        tableau[leaving_idx, :] /= pivot_val
        for i in range(m+1):
            if i != leaving_idx:
                tableau[i, :] -= tableau[i, entering_idx] * tableau[leaving_idx, :]
                
        basis[leaving_idx] = entering_var
        record_step(tableau, basis, "z'")
        
    x_vals = np.zeros(total_vars)
    for i in range(m):
        var = basis[i]
        idx = var_names.index(var)
        x_vals[idx] = tableau[i, -1]

    solution = {f"x{j+1}": float(x_vals[j]) for j in range(n)}
    optimal_value = -float(tableau[m, -1])

    return solution, optimal_value
