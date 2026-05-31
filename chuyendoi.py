import numpy as np
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

def input_vector(name):
    v = input(f"Input elements of vector {name}, separated by space: ")
    return np.array([float(x) for x in v.strip().split()])

def input_matrix():
    rows = int(input("Input number of rows for matrix mt: "))
    print("Input each row, elements separated by space:")
    mat = []
    for i in range(rows):
        row_str = input(f"Row {i+1}: ")
        mat.append([float(x) for x in row_str.strip().split()])
    return np.array(mat)

c = input_vector('c')
b = input_vector('b')
t = input_vector('t')
i_vec = input_vector('i')

mt = input_matrix()

c_new = b
b_new = c
t_new = i_vec
i_new = t
mt_new = mt.T

print("c_new =", c_new)
print("b_new =", b_new)
print("t_new =", t_new)
print("i_new =", i_new)
print("mt_new (transpose of mt):")
print(mt_new)
