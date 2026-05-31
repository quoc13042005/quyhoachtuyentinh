// Plotly setup

document.getElementById('btn-generate').addEventListener('click', generateInputGrid);
document.getElementById('btn-solve').addEventListener('click', solveLP);

function generateInputGrid() {
    const numVars = parseInt(document.getElementById('num_vars').value);
    const numConstraints = parseInt(document.getElementById('num_constraints').value);

    // Objective function inputs
    const cInputs = document.getElementById('c-inputs');
    cInputs.innerHTML = '';
    for (let i = 0; i < numVars; i++) {
        cInputs.innerHTML += `
            <div class="coefficient-item">
                <input type="number" step="any" id="c_${i}" value="0">
                <span>x<sub>${i+1}</sub></span>
                ${i < numVars - 1 ? '<span>+</span>' : ''}
            </div>
        `;
    }

    // Constraints inputs
    const mtInputs = document.getElementById('mt-inputs');
    mtInputs.innerHTML = '';
    for (let i = 0; i < numConstraints; i++) {
        let rowHtml = `<div class="constraint-row">`;
        for (let j = 0; j < numVars; j++) {
            rowHtml += `
                <div class="coefficient-item">
                    <input type="number" step="any" id="a_${i}_${j}" value="0">
                    <span>x<sub>${j+1}</sub></span>
                    ${j < numVars - 1 ? '<span>+</span>' : ''}
                </div>
            `;
        }
        rowHtml += `
            <select id="t_${i}">
                <option value="-1">&le;</option>
                <option value="1">&ge;</option>
                <option value="0">=</option>
            </select>
            <input type="number" step="any" id="b_${i}" class="rhs" value="0">
        </div>`;
        mtInputs.innerHTML += rowHtml;
    }

    // Variable conditions
    const ivecInputs = document.getElementById('ivec-inputs');
    ivecInputs.innerHTML = '';
    for (let i = 0; i < numVars; i++) {
        ivecInputs.innerHTML += `
            <div class="input-group" style="flex-direction: row; align-items: center; gap: 5px;">
                <label>x<sub>${i+1}</sub></label>
                <select id="i_${i}">
                    <option value="1">&ge; 0</option>
                    <option value="-1">&le; 0</option>
                    <option value="0">Tự do</option>
                </select>
            </div>
        `;
    }

    document.getElementById('input-section').style.display = 'block';
    document.getElementById('result-section').style.display = 'none';
}

async function solveLP() {
    const numVars = parseInt(document.getElementById('num_vars').value);
    const numConstraints = parseInt(document.getElementById('num_constraints').value);
    const problemType = parseInt(document.getElementById('problem_type').value);
    const method = document.getElementById('method').value;

    const c = [];
    for (let i = 0; i < numVars; i++) c.push(parseFloat(document.getElementById(`c_${i}`).value));

    const i_vec = [];
    for (let i = 0; i < numVars; i++) i_vec.push(parseInt(document.getElementById(`i_${i}`).value));

    const mt = [];
    const t = [];
    const b = [];
    for (let i = 0; i < numConstraints; i++) {
        const row = [];
        for (let j = 0; j < numVars; j++) {
            row.push(parseFloat(document.getElementById(`a_${i}_${j}`).value));
        }
        mt.push(row);
        t.push(parseInt(document.getElementById(`t_${i}`).value));
        b.push(parseFloat(document.getElementById(`b_${i}`).value));
    }

    const payload = { num_vars: numVars, num_constraints: numConstraints, problem_type: problemType, method, c, mt, t, b, i_vec };

    document.getElementById('loading').style.display = 'flex';
    document.getElementById('result-section').style.display = 'none';
    document.getElementById('chart-container').style.display = 'none';

    try {
        const response = await fetch('/solve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        
        document.getElementById('loading').style.display = 'none';
        document.getElementById('result-section').style.display = 'block';

        const summaryDiv = document.getElementById('result-summary');
        const outputLog = document.getElementById('output-log');

        if (data.error) {
            summaryDiv.className = 'result-summary error';
            summaryDiv.innerHTML = `<strong>Lỗi:</strong> ${data.error}`;
            outputLog.textContent = data.trace || '';
            return;
        }

        const res = data.result;
        if (res.status === 'optimal') {
            summaryDiv.className = 'result-summary';
            let xStr = res.xt.map((v, i) => `x<sub>${i+1}</sub> = ${v.toFixed(6)}`).join(', ');
            summaryDiv.innerHTML = `
                <strong>Trạng thái:</strong> Tối ưu<br>
                <strong>Giá trị Z tối ưu:</strong> ${res.objective.toFixed(6)}<br>
                <strong>Nghiệm:</strong> ${xStr}
            `;
        } else if (res.status === 'unbounded') {
            let limitStr = (problemType === 1) ? 'Max Z = +&infin;' : 'Min Z = -&infin;';
            summaryDiv.className = 'result-summary error';
            summaryDiv.innerHTML = `<strong>Trạng thái:</strong> Bài toán không giới nội.<br><strong>Kết luận:</strong> ${limitStr}`;
        } else if (res.status === 'infeasible') {
            summaryDiv.className = 'result-summary error';
            summaryDiv.innerHTML = `<strong>Trạng thái:</strong> Bài toán vô nghiệm (Không có phương án khả thi).`;
        } else {
            summaryDiv.className = 'result-summary error';
            summaryDiv.innerHTML = `<strong>Trạng thái:</strong> Không có nghiệm tối ưu hữu hạn (${res.status})`;
        }

        const dictLog = document.getElementById('dictionary-log');
        if (method !== 'hinh_hoc' && data.steps && data.steps.length > 0) {
            outputLog.style.display = 'none';
            dictLog.style.display = 'block';
            renderDictionary(data.steps, dictLog, method);
        } else {
            outputLog.style.display = 'block';
            dictLog.style.display = 'none';
            outputLog.textContent = data.output || 'Không có log chi tiết.';
        }

        if (method === 'hinh_hoc' && data.plot_data) {
            drawChart(data.plot_data, c);
        }

    } catch (err) {
        document.getElementById('loading').style.display = 'none';
        alert('Đã xảy ra lỗi khi gọi API: ' + err.message);
    }
}

function floatToFractionHtml(val) {
    let absVal = Math.abs(val);
    if (Math.abs(absVal - Math.round(absVal)) < 1e-5) {
        return Math.round(absVal).toString();
    }
    const tolerance = 1e-5;
    let h1 = 1, h2 = 0, k1 = 0, k2 = 1;
    let b = absVal;
    do {
        let a = Math.floor(b);
        let aux = h1; h1 = a * h1 + h2; h2 = aux;
        aux = k1; k1 = a * k1 + k2; k2 = aux;
        b = 1 / (b - a);
    } while (Math.abs(absVal - h1 / k1) > absVal * tolerance && k1 <= 1000);

    if (k1 === 1) return h1.toString();
    return `<div class="fraction"><span class="num">${h1}</span><span class="den">${k1}</span></div>`;
}

function formatVar(name) {
    if (name === null || name === undefined || name === '') return '';
    let strName = String(name);
    if (strName === "z'") return "<i>z'</i>";
    let display = strName;
    if (strName.startsWith('s')) {
        display = 'w' + strName.slice(1);
    }
    if (display.length > 1 && !isNaN(display.slice(1))) {
        return `<i>${display[0]}</i><sub>${display.slice(1)}</sub>`;
    }
    return `<i>${display}</i>`;
}

function renderDictionary(steps, container, method) {
    container.innerHTML = '';
    steps.forEach((step, idx) => {
        const stepDiv = document.createElement('div');
        stepDiv.className = 'dict-step';
        
        let objIdx = 0; 
        if (['2pha', 'dual', '2pha_dual'].includes(method)) {
            objIdx = step.tableau.length - 1;
        }

        // Bỏ chữ sau pivot như user yêu cầu
        // Nếu là bước 0 thì hiện "Từ vựng ban đầu:", còn lại có thể chỉ để một divider hoặc bỏ luôn
        if (idx === 0) {
            const title = document.createElement('div');
            title.className = 'dict-title';
            title.textContent = "Đơn hình:";
            stepDiv.appendChild(title);
        }

        const m = step.basis.length; 
        const nVars = step.col_names.length; 
        const rhsCol = step.tableau[objIdx].length - 1;

        // Xác định các biến không cơ sở (Non-basic variables) cho bước này
        const nonBasicVars = [];
        for (let j = 0; j < nVars; j++) {
            let varName = step.col_names[j];
            if (varName === 'RHS' || varName === 'rhs') continue;
            if (!step.basis.includes(varName)) {
                nonBasicVars.push({ name: varName, index: j });
            }
        }

        // Tạo bảng
        let tableHtml = `<table class="dict-table">`;

        function buildRow(lhsRaw, rhsVal, coeffs, isObj) {
            let trClass = isObj ? 'dict-obj-row' : '';
            let html = `<tr class="${trClass}">`;
            
            // Cột mũi tên ra (Leaving)
            if (step.leaving && lhsRaw === step.leaving) {
                html += `<td class="td-arrow-left">&larr;</td>`;
            } else {
                html += `<td class="td-arrow-left"></td>`;
            }

            // Cột LHS
            html += `<td class="td-lhs">${formatVar(lhsRaw)}</td>`;
            // Cột Dấu =
            html += `<td class="td-equals">=</td>`;

            // Cột RHS Constant
            let currentRhs = isObj ? -rhsVal : rhsVal;
            if (Math.abs(currentRhs) > 1e-9) {
                let prefix = currentRhs < 0 ? '-' : '';
                html += `<td class="td-rhs-const">${prefix}${floatToFractionHtml(currentRhs)}</td>`;
            } else {
                html += `<td class="td-rhs-const"></td>`; // Trống
            }

            let isFirstPrintedTerm = (Math.abs(currentRhs) <= 1e-9);

            nonBasicVars.forEach(nbv => {
                let coef = coeffs[nbv.index];
                if (Math.abs(coef) < 1e-9) {
                    html += `<td class="td-term"></td>`; // Trống nếu hệ số = 0
                    return;
                }
                
                let displayCoef = isObj ? coef : -coef;
                let sign = '';
                
                if (displayCoef > 1e-9) {
                    sign = isFirstPrintedTerm ? '' : '+';
                } else if (displayCoef < -1e-9) {
                    sign = '-';
                }
                
                let absCoef = Math.abs(displayCoef);
                let numStr = Math.abs(absCoef - 1) < 1e-9 ? '' : floatToFractionHtml(absCoef);
                
                isFirstPrintedTerm = false;

                let isEnteringCol = (step.entering && nbv.name === step.entering);
                let isLeavingRow = (step.leaving && lhsRaw === step.leaving);

                let arrowHtml = '';
                if (isEnteringCol && isObj) {
                    arrowHtml = `<div class="dict-arrow-down">&darr;</div>`;
                }

                let isPivot = isEnteringCol && isLeavingRow;
                let wrapClass = isPivot ? 'circled-term' : '';

                html += `<td class="td-term">
                            <div class="term-content ${wrapClass}">
                                ${arrowHtml}
                                <span class="term-sign">${sign}</span>
                                <span class="term-coef">${numStr}</span>
                                <span class="term-var">${formatVar(nbv.name)}</span>
                            </div>
                         </td>`;
            });

            html += `</tr>`;
            return html;
        }

        // Objective row
        let zLhs = step.obj_name || "z'";
        tableHtml += buildRow(zLhs, step.tableau[objIdx][rhsCol], step.tableau[objIdx], true);

        // Constraints rows
        let rowOffset = (objIdx === 0) ? 1 : 0;
        for (let i = 0; i < m; i++) {
            let rIdx = i + rowOffset;
            let bv = step.basis[i];
            tableHtml += buildRow(bv, step.tableau[rIdx][rhsCol], step.tableau[rIdx], false);
        }

        tableHtml += `</table>`;
        stepDiv.innerHTML += tableHtml;
        container.appendChild(stepDiv);
    });
}

function sortVertices(vertices) {
    if (vertices.length <= 2) return vertices;
    const cx = vertices.reduce((sum, v) => sum + v[0], 0) / vertices.length;
    const cy = vertices.reduce((sum, v) => sum + v[1], 0) / vertices.length;
    return vertices.slice().sort((a, b) => {
        return Math.atan2(a[1] - cy, a[0] - cx) - Math.atan2(b[1] - cy, b[0] - cx);
    });
}

function drawChart(plotData, c) {
    document.getElementById('chart-container').style.display = 'block';
    
    // Sắp xếp các đỉnh để tạo đa giác lồi
    const sortedPoints = sortVertices(plotData.feasible);
    // Lặp lại điểm đầu để đóng đa giác
    if(sortedPoints.length > 0) {
        sortedPoints.push(sortedPoints[0]);
    }
    
    const polyX = sortedPoints.map(pt => pt[0]);
    const polyY = sortedPoints.map(pt => pt[1]);
    
    // Trace cho vùng khả thi
    const tracePolygon = {
        x: polyX,
        y: polyY,
        fill: 'toself',
        fillcolor: 'rgba(59, 130, 246, 0.4)',
        line: { color: 'rgba(59, 130, 246, 1)' },
        name: 'Vùng khả thi',
        mode: 'lines+markers',
        marker: { size: 6 }
    };
    
    const traceOpt = {
        x: [plotData.opt.x],
        y: [plotData.opt.y],
        mode: 'markers',
        marker: { symbol: 'star', size: 16, color: 'red' },
        name: 'Nghiệm tối ưu'
    };
    
    // Tính toán giới hạn của đồ thị để vẽ đường thẳng dài
    const allX = plotData.feasible.map(pt => pt[0]);
    const allY = plotData.feasible.map(pt => pt[1]);
    const minX = Math.min(...allX) - 5;
    const maxX = Math.max(...allX) + 5;
    const minY = Math.min(...allY) - 5;
    const maxY = Math.max(...allY) + 5;
    
    // Hàm vẽ đường thẳng Z = c1*x1 + c2*x2
    function getZLine(Z) {
        if (Math.abs(c[1]) > 1e-8) {
            // x2 = (Z - c1*x1) / c2
            return {
                x: [minX, maxX],
                y: [(Z - c[0]*minX) / c[1], (Z - c[0]*maxX) / c[1]]
            };
        } else {
            // c2 == 0 => c1*x1 = Z => x1 = Z / c1
            const xVal = Z / c[0];
            return {
                x: [xVal, xVal],
                y: [minY, maxY]
            };
        }
    }
    
    const initialZ = plotData.opt.z;
    const initialLine = getZLine(initialZ);
    
    const traceZ = {
        x: initialLine.x,
        y: initialLine.y,
        mode: 'lines',
        line: { color: 'green', dash: 'dash', width: 2 },
        name: 'Hàm mục tiêu Z'
    };
    
    const layout = {
        title: 'Đồ thị phương pháp Hình học',
        xaxis: { title: 'x1', range: [minX, maxX] },
        yaxis: { title: 'x2', range: [minY, maxY] },
        hovermode: 'closest',
        plot_bgcolor: 'rgba(0,0,0,0)',
        paper_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#333' }
    };
    
    Plotly.newPlot('lpChart', [tracePolygon, traceOpt, traceZ], layout);
    
    // Thiết lập Slider
    const zSliderContainer = document.getElementById('z-slider-container');
    const zSlider = document.getElementById('z-slider');
    const zValueDisplay = document.getElementById('z-value');
    
    zSliderContainer.style.display = 'block';
    
    // Xác định range cho Z
    const zValues = plotData.feasible.map(pt => c[0]*pt[0] + c[1]*pt[1]);
    let minZ = Math.min(...zValues);
    let maxZ = Math.max(...zValues);
    if (minZ === maxZ) { minZ -= 10; maxZ += 10; }
    
    zSlider.min = minZ - Math.abs(maxZ - minZ)*0.5;
    zSlider.max = maxZ + Math.abs(maxZ - minZ)*0.5;
    zSlider.step = (zSlider.max - zSlider.min) / 200;
    zSlider.value = initialZ;
    zValueDisplay.textContent = initialZ.toFixed(2);
    
    zSlider.oninput = function() {
        const val = parseFloat(this.value);
        zValueDisplay.textContent = val.toFixed(2);
        const newLine = getZLine(val);
        Plotly.update('lpChart', {x: [newLine.x], y: [newLine.y]}, {}, [2]); // Update trace 2 (traceZ)
    };
}
