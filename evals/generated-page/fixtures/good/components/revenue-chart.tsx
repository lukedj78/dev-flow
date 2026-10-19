import { Area, AreaChart } from "recharts";

export function RevenueChart({ data }: { data: { m: string; v: number }[] }) {
  return (
    <AreaChart data={data}>
      <Area dataKey="v" fill="var(--chart-1)" fillOpacity={0.2} stroke="var(--chart-1)" />
    </AreaChart>
  );
}
