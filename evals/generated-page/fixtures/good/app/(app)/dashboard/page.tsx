// Sample rows in an app screen: realistic, logged in fallbacks_applied — not proof on a public page.
const ROWS = [{ client: "Eliška Novák", seats: 12 }, { client: "Tomás Capellini", seats: 7 }];

export default function Dashboard() {
  return (
    <section>
      <p>1,204 customers this quarter</p>
      <p>You manage 12 clients</p>
      <ul>{ROWS.map((r) => <li key={r.client} className="tabular-nums">{r.client} · {r.seats}</li>)}</ul>
    </section>
  );
}
