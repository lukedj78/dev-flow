import { Area, AreaChart } from "recharts";

export function RevenueChart({ data }: { data: { m: string; v: number }[] }) {
  return (
    <AreaChart data={data}>
      <defs>
        <linearGradient id="fillRevenue" x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.8} />
        </linearGradient>
      </defs>
      <Area dataKey="v" fill="url(#fillRevenue)" />
    </AreaChart>
  );
}
