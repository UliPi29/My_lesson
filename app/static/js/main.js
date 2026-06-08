/** Фильтрует таблицу по содержимему data-атрибутов строк. */
function filterTable(inputId, tableId) {
    const val = document.getElementById(inputId).value.toLowerCase();
    const rows = document.querySelectorAll('#' + tableId + ' tbody tr');
    rows.forEach(function(row) {
        const attrs = row.attributes;
        let hasData = false;
        let match = false;
        for (let i = 0; i < attrs.length; i++) {
            if (attrs[i].name.startsWith('data-')) {
                hasData = true;
                if (attrs[i].value.toLowerCase().includes(val)) {
                    match = true;
                    break;
                }
            }
        }
        if (hasData) {
            row.style.display = match ? '' : 'none';
        }
    });
}

/** Сортирует строки таблицы по указанному столбцу (только для statsTable). */
function sortTable(col, order) {
    if (!order) return;
    const table = document.getElementById('statsTable');
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const isAsc = order === 'asc';

    rows.sort(function(a, b) {
        let valA = a.getAttribute('data-' + col);
        let valB = b.getAttribute('data-' + col);
        if (col === 'name') {
            return isAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        return isAsc ? parseFloat(valA) - parseFloat(valB) : parseFloat(valB) - parseFloat(valA);
    });

    rows.forEach(function(row) {
        table.querySelector('tbody').appendChild(row);
    });
}

/** Показывает модальное окно подтверждения для GET-ссылки. */
function confirmAction(url, text, btnText) {
    var btn = document.getElementById('confirmModalBtn');
    btn.href = url;
    btn.onclick = null;
    document.getElementById('confirmModalBody').textContent = text || 'Вы уверены?';
    document.getElementById('confirmModalBtnText').textContent = btnText || 'Удалить';
    var modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    modal.show();
    return false;
}

/** Показывает модальное окно подтверждения для отправки формы. */
function confirmFormSubmit(form, text, btnText) {
    var btn = document.getElementById('confirmModalBtn');
    btn.href = '#';
    btn.onclick = function(e) {
        e.preventDefault();
        form.submit();
    };
    document.getElementById('confirmModalBody').textContent = text || 'Вы уверены?';
    document.getElementById('confirmModalBtnText').textContent = btnText || 'Удалить';
    var modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    modal.show();
    return false;
}