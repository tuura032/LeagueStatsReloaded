function myFunction() {
    document.getElementById("demo").innerHTML += "Hello World!";
    console.log('hello word, console!');
  }

// L6 — client-side sorting for the standings table.
//
// Replaces the dead v1 route links in the table headers (/total_wins,
// /total_points, /average_score, /h2h, /top6, and / on the Rank header)
// with click-to-sort columns. This finishes the 2019 "new js table"
// commit. Vanilla JS, no library.
//
// Behaviour:
// - First click on a column sorts it descending (v1's server-side sorts
//   were all DESC); clicking the same header again flips to ascending.
// - Every sortable column is a plain number, so the sort is numeric.
// - Ties keep the official standings order (each row's original
//   position), so the result is the same no matter what was sorted
//   before.
// - The Rank cell is the team's standings rank, not its row position,
//   so it stays with the team when rows move.

(function () {
  var table = document.getElementById("standings-table");
  if (!table) return;

  var headers = table.tHead.rows[0].cells;
  var body = table.tBodies[0];
  var rows = Array.prototype.slice.call(body.rows);

  // Each row's original position (its standings rank) is the tie-breaker.
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
})();