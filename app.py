import sys
import io
import contextlib
import importlib.util
from flask import Flask, request, jsonify, render_template
import numpy as np

app = Flask(__name__)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)

    if spec is None or spec.loader is None:
        raise ImportError(f"Không thể load module: {path}")

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


def validate_input(data):
    if data is None:
        return "Không nhận được dữ liệu JSON từ client."

    required_fields = [
        'num_vars',
        'num_constraints',
        'problem_type',
        'method',
        'c',
        't',
        'i_vec',
        'mt',
        'b'
    ]

    for field in required_fields:
        if field not in data:
            return f"Thiếu trường dữ liệu: {field}"

    try:
        num_vars = int(data['num_vars'])
        num_constraints = int(data['num_constraints'])
        problem_type = int(data['problem_type'])
    except (ValueError, TypeError):
        return "Số biến, số ràng buộc hoặc loại bài toán không hợp lệ."

    if num_vars <= 0:
        return "Số biến phải lớn hơn 0."

    if num_constraints <= 0:
        return "Số ràng buộc phải lớn hơn 0."

    if problem_type not in [-1, 1]:
        return "Loại bài toán không hợp lệ. Chỉ nhận Min hoặc Max."

    valid_methods = ['donhinh', 'bland', '2pha', 'dual', '2pha_dual', 'hinh_hoc']
    if data['method'] not in valid_methods:
        return "Phương pháp giải không hợp lệ."

    if len(data['c']) != num_vars:
        return "Số hệ số hàm mục tiêu không khớp với số biến."

    if len(data['i_vec']) != num_vars:
        return "Số điều kiện biến không khớp với số biến."

    if len(data['mt']) != num_constraints:
        return "Số dòng ma trận ràng buộc không khớp với số ràng buộc."

    if len(data['t']) != num_constraints:
        return "Số dấu ràng buộc không khớp với số ràng buộc."

    if len(data['b']) != num_constraints:
        return "Số hệ số vế phải không khớp với số ràng buộc."

    for row in data['mt']:
        if len(row) != num_vars:
            return "Một dòng ràng buộc có số hệ số không khớp với số biến."

    try:
        [float(x) for x in data['c']]
        [int(x) for x in data['t']]
        [int(x) for x in data['i_vec']]
        [[float(val) for val in row] for row in data['mt']]
        [float(x) for x in data['b']]
    except (ValueError, TypeError):
        return "Dữ liệu nhập phải là số hợp lệ."

    for sign in data['t']:
        if int(sign) not in [-1, 0, 1]:
            return "Dấu ràng buộc không hợp lệ."

    for condition in data['i_vec']:
        if int(condition) not in [-1, 0, 1]:
            return "Điều kiện biến không hợp lệ."

    return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/solve', methods=['POST'])
def solve():
    data = request.json

    input_error = validate_input(data)
    if input_error:
        return jsonify({"error": input_error}), 400

    try:
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
                return jsonify({
                    "error": "Phương pháp hình học chỉ áp dụng cho bài toán 2 biến."
                }), 400

            res = solve_geometric(
                num_vars,
                num_constraints,
                problem_type,
                c,
                t,
                i_vec,
                mt,
                b
            )
            return jsonify(res)

        output_text = ""
        result = {}
        steps_data = []

        with capture_stdout() as out:
            (
                old_pt,
                old_t,
                old_i,
                new_pt,
                new_t,
                new_i,
                c_tr,
                mt_tr,
                b_tr
            ) = mod_donhinh.transform_problem(
                problem_type,
                num_vars,
                num_constraints,
                c,
                t,
                i_vec,
                mt,
                b
            )

            # Simplex thường và Bland cần nghiệm cơ sở ban đầu khả thi.
            # Nếu RHS sau chuẩn hóa âm, slack basis ban đầu không khả thi.
            if method in ['donhinh', 'bland'] and any(bi < -1e-9 for bi in b_tr):
                return jsonify({
                    "error": (
                        "Simplex thường/Bland cần nghiệm cơ sở ban đầu khả thi. "
                        "Bài toán sau chuẩn hóa có RHS âm, hãy dùng phương pháp Đơn hình 2 pha."
                    )
                }), 400

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
                    sol, val = mod_2phadual.two_phase_dual_original_min(
                        A_np,
                        b_np,
                        c_np
                    )
                    steps_data = mod_2phadual.global_steps

                else:
                    return jsonify({"error": "Phương pháp không hợp lệ."}), 400

                if isinstance(sol, str):
                    result = {"status": sol}

                elif sol is None:
                    result = {"status": "unbounded or infeasible"}

                else:
                    total_tr_vars = len(c_tr)
                    x_tr = [sol.get(f"x{j + 1}", 0.0) for j in range(total_tr_vars)]

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
                            xt.append(x_tr[ptr] - x_tr[ptr + 1])
                            ptr += 2

                    obj = val * (-old_pt)

                    result = {
                        "status": "optimal",
                        "objective": obj,
                        "x": x_tr,
                        "xt": xt
                    }

        output_text = out.getvalue()

        return jsonify({
            "output": output_text,
            "result": result,
            "steps": steps_data
        })

    except Exception as e:
        # Không trả traceback ra frontend để tránh lộ thông tin nội bộ.
        # Khi cần debug, xem lỗi trong terminal/server log.
        print("Internal error:", str(e))

        return jsonify({
            "error": "Đã xảy ra lỗi trong quá trình giải. Vui lòng kiểm tra lại dữ liệu nhập."
        }), 500


def solve_geometric(num_vars, num_constraints, problem_type, c, t, i_vec, mt, b):
    lines = []

    for j in range(2):
        if i_vec[j] == 1:
            row = [0.0, 0.0]
            row[j] = -1.0

            lines.append({
                'a': row[0],
                'b': row[1],
                'c': 0.0,
                'op': '<=',
                'name': f"x{j + 1} >= 0"
            })

        elif i_vec[j] == -1:
            row = [0.0, 0.0]
            row[j] = 1.0

            lines.append({
                'a': row[0],
                'b': row[1],
                'c': 0.0,
                'op': '<=',
                'name': f"x{j + 1} <= 0"
            })

    for r in range(num_constraints):
        a1, a2 = mt[r][0], mt[r][1]
        br = b[r]
        name = f"Ràng buộc {r + 1}"

        if t[r] == -1:
            lines.append({
                'a': a1,
                'b': a2,
                'c': br,
                'op': '<=',
                'name': name
            })

        elif t[r] == 1:
            lines.append({
                'a': -a1,
                'b': -a2,
                'c': -br,
                'op': '<=',
                'name': name
            })

        elif t[r] == 0:
            lines.append({
                'a': a1,
                'b': a2,
                'c': br,
                'op': '==',
                'name': name
            })

    equations = [(line['a'], line['b'], line['c']) for line in lines]
    vertices = []

    for i in range(len(equations)):
        for j in range(i + 1, len(equations)):
            A_mat = np.array([
                [equations[i][0], equations[i][1]],
                [equations[j][0], equations[j][1]]
            ])

            B_mat = np.array([
                equations[i][2],
                equations[j][2]
            ])

            if abs(np.linalg.det(A_mat)) > 1e-8:
                try:
                    pt = np.linalg.solve(A_mat, B_mat)
                    vertices.append((pt[0], pt[1]))
                except np.linalg.LinAlgError:
                    pass

    feasible = []

    for x, y in vertices:
        is_feasible = True

        for line in lines:
            val = line['a'] * x + line['b'] * y

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
        return {
            "error": "Bài toán vô nghiệm hoặc vùng khả thi không tạo được đỉnh hữu hạn."
        }

    results = []

    for x, y in feasible:
        z = c[0] * x + c[1] * y
        results.append({
            'x': x,
            'y': y,
            'z': z
        })

    if problem_type == 1:
        opt = max(results, key=lambda r: r['z'])
    else:
        opt = min(results, key=lambda r: r['z'])

    output_text = "=== Các đỉnh khả thi và giá trị z ===\n"

    for r in results:
        output_text += (
            f"x1 = {r['x']:.6f}, "
            f"x2 = {r['y']:.6f}, "
            f"z = {r['z']:.6f}\n"
        )

    output_text += (
        "\nNghiệm tối ưu tìm được trên các đỉnh hữu hạn:\n"
        f"x1* = {opt['x']:.6f}, "
        f"x2* = {opt['y']:.6f}, "
        f"z* = {opt['z']:.6f}\n"
    )

    output_text += (
        "\nLưu ý: Phương pháp hình học hiện tại xét các đỉnh hữu hạn tìm được. "
        "Với vùng khả thi không bị chặn, cần kiểm tra thêm trường hợp không giới nội.\n"
    )

    return {
        "output": output_text,
        "warning": (
            "Phương pháp hình học hiện tại chưa kiểm tra đầy đủ trường hợp không giới nội."
        ),
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
    app.run(port=5000)
