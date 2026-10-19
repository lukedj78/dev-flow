// Sample rows in an app screen: realistic, logged in fallbacks_applied — not proof on a public page.
const ROWS = [{ client: "Eliška Novák", seats: 12 }, { client: "Tomás Capellini", seats: 7 }];

export default function Dashboard() {
  return <ul>{ROWS.map((r) => <li key={r.client} className="tabular-nums">{r.client} · {r.seats}</li>)}</ul>;
}
