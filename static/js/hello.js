// Client-side sorting for any table with class "sortable-table" and
// per-column "sortable" <th> classes. Originally built for just the
// standings table (L6); generalized so careers.html could reuse it for
// re-ranking by Points For instead of duplicating the logic.
//
// Behaviour:
// - First click on a column sorts it descending; clicking the same
//   header again flips to ascending.
// - Every sortable column is a plain number, so the sort is numeric.
// - Ties keep the table's original row order (each row's starting
//   position), so the result is the same no matter what was sorted
//   before.

(function () {
  function initSortableTable(table) {
    var headers = table.tHead.rows[0].cells;
    var body = table.tBodies[0];
    var rows = Array.prototype.slice.call(body.rows);

    // Each row's original position is the tie-breaker.
    rows.forEach(function (row, i) { row._rank = i; });

    var sorted = { col: -1, dir: -1 };

    function sortTable(col, dir) {
      rows.sort(function (a, b) {
        var d = parseFloat(a.cells[col].textContent) -
                parseFloat(b.cells[col].textContent);
        return d !== 0 ? d * dir : a._rank - b._rank;
      });
      rows.forEach(function (row) { body.appendChild(row); });
    }

    Array.prototype.forEach.call(headers, function (th, col) {
      if (!th.classList.contains("sortable")) return;
      th.addEventListener("click", function () {
        var dir = (sorted.col === col && sorted.dir === -1) ? 1 : -1;
        sorted = { col: col, dir: dir };
        sortTable(col, dir);
        Array.prototype.forEach.call(headers, function (h) {
          h.classList.remove("asc", "desc");
          h.removeAttribute("aria-sort");
        });
        th.classList.add(dir === -1 ? "desc" : "asc");
        th.setAttribute("aria-sort", dir === -1 ? "descending" : "ascending");
      });
    });
  }

  document.querySelectorAll("table.sortable-table").forEach(initSortableTable);
})();
