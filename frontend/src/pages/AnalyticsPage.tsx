import {
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, FileText, FolderKanban, MessageSquareText, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getErrorMessage, workspaceApi } from "../lib/api";

const colors = ["#2563eb", "#8b5cf6", "#06b6d4", "#f59e0b", "#22c55e"];

export function AnalyticsPage() {
  const query = useQuery({ queryKey: ["analytics"], queryFn: workspaceApi.analytics });
  const data = query.data;
  const daily = new Map<string, { date: string; messages: number; documents: number }>();
  data?.activity.forEach((activity) => {
    const date = activity.timestamp.slice(0, 10);
    const day = daily.get(date) ?? { date, messages: 0, documents: 0 };
    if (activity.kind === "Message") day.messages += 1;
    if (activity.kind === "Document") day.documents += 1;
    daily.set(date, day);
  });
  const chartData = [...daily.values()].sort((a, b) => a.date.localeCompare(b.date));
  const counts = data?.counts;
  const metrics = [
    { label: "Projects", value: counts?.projects ?? 0, icon: FolderKanban, accent: "blue" },
    { label: "Conversations", value: counts?.conversations ?? 0, icon: MessageSquareText, accent: "purple" },
    { label: "Messages", value: counts?.messages ?? 0, icon: Activity, accent: "cyan" },
    { label: "Documents", value: counts?.documents ?? 0, icon: FileText, accent: "amber" },
    { label: "Indexed files", value: counts?.indexed_documents ?? 0, icon: Sparkles, accent: "green" },
  ];

  if (query.isError) return <div className="inline-error">{getErrorMessage(query.error)}</div>;

  return (
    <div className="page-scroll analytics-page">
      <header className="page-title-block">
        <div className="page-title-icon"><Activity size={19} /></div>
        <div><h1>Workspace analytics</h1><p>Real usage metrics from your local Agentic RAG workspace.</p></div>
      </header>
      <div className="metrics-grid">
        {metrics.map(({ label, value, icon: Icon, accent }) => (
          <article className="analytics-metric-card" key={label}>
            <div className={`metric-icon metric-${accent}`}><Icon size={18} /></div>
            <span>{label}</span>
            <strong>{query.isLoading ? "—" : value}</strong>
          </article>
        ))}
      </div>
      <div className="analytics-chart-grid">
        <section className="chart-card activity-chart">
          <div className="chart-heading"><div><h2>Workspace activity</h2><p>Messages and document uploads over time</p></div><span className="chart-legend-dot" /></div>
          {chartData.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData} margin={{ top: 10, right: 12, bottom: 4, left: -18 }}>
                <CartesianGrid stroke="#edf0f6" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="date" tickFormatter={(value: string) => value.slice(5)} tickLine={false} axisLine={false} fontSize={11} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={11} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="messages" name="Messages" stroke="#2563eb" strokeWidth={2.5} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="documents" name="Documents" stroke="#8b5cf6" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : <ChartEmpty text="Activity appears after you send messages or upload documents." />}
        </section>
        <section className="chart-card type-chart">
          <div className="chart-heading"><div><h2>Document types</h2><p>Files across active conversations</p></div></div>
          {data?.document_types.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={data.document_types} dataKey="count" nameKey="type" innerRadius={62} outerRadius={94} paddingAngle={4}>
                  {data.document_types.map((entry, index) => <Cell key={entry.type} fill={colors[index % colors.length]} />)}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : <ChartEmpty text="Document type statistics appear after you upload a file." />}
        </section>
      </div>
      <section className="activity-table-card">
        <div className="chart-heading"><div><h2>Recent activity</h2><p>Your latest workspace changes</p></div></div>
        {data?.activity.length ? (
          <div className="recent-activity-list">
            {data.activity.map((item, index) => (
              <div className="recent-activity-row" key={`${item.timestamp}-${item.kind}-${index}`}>
                <span className={`activity-kind-icon activity-${item.kind.toLowerCase()}`}>{item.kind === "Message" ? <MessageSquareText size={15} /> : <FileText size={15} />}</span>
                <span><strong>{item.title}</strong><small>{item.kind}</small></span>
                <time>{new Date(item.timestamp).toLocaleString()}</time>
              </div>
            ))}
          </div>
        ) : <ChartEmpty text="No recent activity has been recorded." />}
      </section>
    </div>
  );
}

function ChartEmpty({ text }: { text: string }) {
  return <div className="chart-empty"><Activity size={21} /><span>{text}</span></div>;
}
