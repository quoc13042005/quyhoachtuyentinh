import numpy as np

lines = [
    (-1, -2, 6),
    (1, -2, 4),
    (-1, 1, 1),
    (1, 0, 0),
    (0, 1, 0)
]

vertices = []
for i in range(len(lines)):
    for j in range(i + 1, len(lines)):
        a1, b1, c1 = lines[i]
        a2, b2, c2 = lines[j]
        A = np.array([[a1, b1], [a2, b2]])
        B = np.array([c1, c2])
        det = np.linalg.det(A)
        if abs(det) < 1e-8:
            continue
        x, y = np.linalg.solve(A, B)
        vertices.append((x, y))
