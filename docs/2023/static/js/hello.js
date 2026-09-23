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
// - Headers are keyboard-operable (Tab to focus, Enter/Space to sort).
//
// Decoration rows: a tbody can contain full-width rows that aren't data
// -- home.html's "playoff line" divider is a single <td colspan="10">.
// Those are excluded from the sort (indexing cells[col] on them throws,
// which used to abort Array.sort and silently kill sorting on the whole
// page) and are only shown while the rows are in their original order,
// since "top 6 make it" is a claim about the default ranking and becomes
// a lie once the table is re-sorted by, say, Points For.

(function () {
  function initSortableTable(table) {
    var headers = table.tHead.rows[0].cells;
    var colCount = headers.length;
    var body = table.tBodies[0];
    var allRows = Array.prototype.slice.call(body.rows);

    // A data row has a cell for every column; anything narrower is a
    // decoration row (colspan divider, section label, ...).
    var rows = allRows.filter(function (row) {
      return row.cells.length === colCount;
    });
    var decorations = allRows
      .map(function (row, i) { return { row: row, index: i }; })
      .filter(function (d) { return d.row.cells.length !== colCount; });

    // Each row's original position is the tie-breaker.
    rows.forEach(function (row, i) { row._rank = i; });

    var sorted = { col: -1, dir: -1 };

    function inOriginalOrder() {
      for (var i = 0; i < rows.length; i++) {
        if (rows[i]._rank !== i) return false;
      }
      return true;
    }

    // A cell sorts on its data-sort attribute when it has one, else on its
    // text. Needed wherever the displayed text is not the number: "1st" is
    // fine, but the champion's cell reads "<trophy> 1st" and parseFloat of
    // that is NaN, which would feed NaN to the comparator and scramble the
    // table.
    function cellValue(row, col) {
      var cell = row.cells[col];
      if (!cell) return NaN;
      var explicit = cell.getAttribute("data-sort");
      return parseFloat(explicit !== null ? explicit : cell.textContent);
    }

    function sortTable(col, dir) {
      rows.sort(function (a, b) {
        var av = cellValue(a, col), bv = cellValue(b, col);
        // Rows with no value for this column sink to the bottom either
        // way, rather than landing wherever NaN comparisons drop them.
        if (isNaN(av) && isNaN(bv)) return a._rank - b._rank;
        if (isNaN(av)) return 1;
        if (isNaN(bv)) return -1;
        var d = av - bv;
        return d !== 0 ? d * dir : a._rank - b._rank;
      });

      decorations.forEach(function (d) { d.row.remove(); });
      rows.forEach(function (row) { body.appendChild(row); });

      // Put the decorations back only when the data is in its original
      // order; otherwise they'd label the wrong rows.
      if (inOriginalOrder()) {
        decorations.forEach(function (d) {
          var before = body.rows[d.index] || null;
          body.insertBefore(d.row, before);
        });
      }
    }

    Array.prototype.forEach.call(headers, function (th, col) {
      if (!th.classList.contains("sortable")) return;

      // Keyboard access: a <th> with a click handler is unreachable by
      // Tab and inert to Enter/Space without these.
      th.setAttribute("tabindex", "0");
      th.setAttribute("role", "button");

      function activate() {
        var dir = (sorted.col === col && sorted.dir === -1) ? 1 : -1;
        sorted = { col: col, dir: dir };
        sortTable(col, dir);
        Array.prototype.forEach.call(headers, function (h) {
          h.classList.remove("asc", "desc");
          h.removeAttribute("aria-sort");
        });
        th.classList.add(dir === -1 ? "desc" : "asc");
        th.setAttribute("aria-sort", dir === -1 ? "descending" : "ascending");
      }

      th.addEventListener("click", activate);
      th.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
          e.preventDefault();
          activate();
        }
      });
    });
  }

  document.querySelectorAll("table.sortable-table").forEach(initSortableTable);
})();
