import sys
import io
import contextlib
import importlib.util
from flask import Flask, request, jsonify, render_template
import numpy as np

app = Flask(__name__)

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

mod_bland = load_module('mod_bland', 'bland.py')
mod_donhinh = load_module('mod_donhinh', 'donhinh.py')
mod_2pha = load_module('mod_2pha', '2pha.py')
mod_dual = load_module('mod_dual', 'donhinhdoingau.py')
mod_2phadual = load_module('mod_2phadual', 'donhinh2phadoingaugoc.py')

@contextlib.contextmanager
def capture_stdout():
    old = sys.stdout
    capturer = io.StringIO()
    sys.stdout = capturer
    try:
        yield capturer
    finally:
        sys.stdout = old

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/solve', methods=['POST'])
def solve():
    data = request.json
    num_vars = int(data['num_vars'])
    num_constraints = int(data['num_constraints'])
    problem_type = int(data['problem_type'])
    method = data['method']
    c = [float(x) for x in data['c']]
    t = [int(x) for x in data['t']]
    i_vec = [int(x) for x in data['i_vec']]
    mt = [[float(val) for val in row] for row in data['mt']]
    b = [float(x) for x in data['b']]
    
    if method == 'hinh_hoc':
        if num_vars != 2:
            return jsonify({"error": "Phương pháp hình học chỉ áp dụng cho bài toán 2 biến."})
        res = solve_geometric(num_vars, num_constraints, problem_type, c, t, i_vec, mt, b)
        return jsonify(res)

    output_text = ""
    result = {}
    steps_data = []
    
    try:
        with capture_stdout() as out:
            (old_pt, old_t, old_i, new_pt, new_t, new_i, c_tr, mt_tr, b_tr) = mod_donhinh.transform_problem(
                problem_type, num_vars, num_constraints, c, t, i_vec, mt, b
            )
            
            if method == 'donhinh':
                res = mod_donhinh.simplex(c_tr, mt_tr, b_tr, old_i, old_pt)
                steps_data = mod_donhinh.global_steps
                result = {
                    "status": res["status"],
                    "objective": res["objective"],
                    "x": res["x"],
                    "xt": res["xt"]
                }
            elif method == 'bland':
                res = mod_bland.bland_rule(c_tr, mt_tr, b_tr, old_i, old_pt)
                steps_data = mod_bland.global_steps
                result = {
                    "status": res["status"],
                    "objective": res["objective"],
                    "x": res["x"],
                    "xt": res["xt"]
                }
            else:
                A_np = np.array(mt_tr, dtype=float)
                b_np = np.array(b_tr, dtype=float)
                c_np = np.array(c_tr, dtype=float)
                
                if method == '2pha':
                    sol, val = mod_2pha.two_phase_simplex_min(A_np, b_np, c_np)
                    steps_data = mod_2pha.global_steps
                elif method == 'dual':
                    sol, val = mod_dual.dual_simplex_min(A_np, b_np, c_np)
                    steps_data = mod_dual.global_steps
                elif method == '2pha_dual':
                    sol, val = mod_2phadual.two_phase_dual_original_min(A_np, b_np, c_np)
                    steps_data = mod_2phadual.global_steps
                else:
                    return jsonify({"error": "Phương pháp không hợp lệ."})
                    
                if isinstance(sol, str):
                    result = {"status": sol}
                elif sol is None:
                    result = {"status": "unbounded or infeasible"}
                else:
                    total_tr_vars = len(c_tr)
                    x_tr = [sol.get(f"x{j+1}", 0.0) for j in range(total_tr_vars)]
                    xt = []
                    ptr = 0
                    for iv in old_i:
                        if iv == 1:
                            xt.append(x_tr[ptr])
                            ptr += 1
                        elif iv == -1:
                            xt.append(-x_tr[ptr])
                            ptr += 1
                        else:
                            xt.append(x_tr[ptr] - x_tr[ptr+1])
                            ptr += 2
                    
                    obj = val * (-old_pt)
                    result = {
                        "status": "optimal",
                        "objective": obj,
                        "x": x_tr,
                        "xt": xt
                    }
                    
        output_text = out.getvalue()
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()})
        
    return jsonify({
        "output": output_text,
        "result": result,
        "steps": steps_data
    })

def solve_geometric(num_vars, num_constraints, problem_type, c, t, i_vec, mt, b):
    lines = []
    for j in range(2):
        if i_vec[j] == 1:
            row = [0.0, 0.0]
            row[j] = -1.0
            lines.append({'a': row[0], 'b': row[1], 'c': 0.0, 'op': '<=', 'name': f"x{j+1} >= 0"})
        elif i_vec[j] == -1:
            row = [0.0, 0.0]
            row[j] = 1.0
            lines.append({'a': row[0], 'b': row[1], 'c': 0.0, 'op': '<=', 'name': f"x{j+1} <= 0"})
            
    for r in range(num_constraints):
        a1, a2 = mt[r][0], mt[r][1]
        br = b[r]
        name = f"Ràng buộc {r+1}"
        if t[r] == -1:
            lines.append({'a': a1, 'b': a2, 'c': br, 'op': '<=', 'name': name})
        elif t[r] == 1:
            lines.append({'a': -a1, 'b': -a2, 'c': -br, 'op': '<=', 'name': name})
        elif t[r] == 0:
            lines.append({'a': a1, 'b': a2, 'c': br, 'op': '==', 'name': name})
            
    equations = [(line['a'], line['b'], line['c']) for line in lines]
    vertices = []
    
    for i in range(len(equations)):
        for j in range(i+1, len(equations)):
            A_mat = np.array([[equations[i][0], equations[i][1]], [equations[j][0], equations[j][1]]])
            B_mat = np.array([equations[i][2], equations[j][2]])
            if abs(np.linalg.det(A_mat)) > 1e-8:
                try:
                    pt = np.linalg.solve(A_mat, B_mat)
                    vertices.append((pt[0], pt[1]))
                except:
                    pass
                    
    feasible = []
    for x, y in vertices:
        is_feasible = True
        for line in lines:
            val = line['a']*x + line['b']*y
            if line['op'] == '<=' and val > line['c'] + 1e-8:
                is_feasible = False
                break
            elif line['op'] == '==' and abs(val - line['c']) > 1e-8:
                is_feasible = False
                break
        if is_feasible:
            feasible.append((round(x, 8), round(y, 8)))
            
    feasible = list(set(feasible))
    if not feasible:
        return {"error": "Bài toán vô nghiệm (không có vùng khả thi)."}
        
    results = []
    for x, y in feasible:
        z = c[0]*x + c[1]*y
        results.append({'x': x, 'y': y, 'z': z})
        
    opt = max(results, key=lambda r: r['z']) if problem_type == 1 else min(results, key=lambda r: r['z'])
    
    output_text = "=== Các đỉnh khả thi và giá trị z ===\n"
    for r in results:
        output_text += f"x1 = {r['x']:.6f}, x2 = {r['y']:.6f}, z = {r['z']:.6f}\n"
    output_text += f"\nNghiệm tối ưu:\nx1* = {opt['x']:.6f}, x2* = {opt['y']:.6f}, z* = {opt['z']:.6f}\n"
    
    return {
        "output": output_text,
        "result": {
            "status": "optimal",
            "objective": opt['z'],
            "xt": [opt['x'], opt['y']]
        },
        "plot_data": {
            "feasible": feasible,
            "lines": lines,
            "opt": opt
        }
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)
