// Display mirror of app/money.py. The server remains authoritative for totals.
// Separator written as an escape so it can't drift to a non-breaking space.
const SEP = " ";

export const fmt = (n) =>
  String(Math.round(n || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, SEP);
