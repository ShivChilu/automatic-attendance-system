import React, { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Label } from "./ui/label";

function StatCard({ title, value, subtitle, accent = "#1e40af" }) {
  return (
    <div className="card narrow animate-scale-in">
      <div className="stats_card" style={{ background: 'white', color: '#1f2937' }}>
        <div className="stats_number" style={{ color: accent }}>{value}</div>
        <div className="stats_label" style={{ color: '#6b7280' }}>{title}</div>
        {subtitle && <div className="text-xs mt-2" style={{ color: '#6b7280' }}>{subtitle}</div>}
      </div>
    </div>
  );
}

export default function AnalyticsGov() {
  const [dateStr, setDateStr] = useState(() => new Date().toISOString().slice(0,10));
  const [loading, setLoading] = useState(false);
  const [schoolsDaily, setSchoolsDaily] = useState(null);
  const [trend, setTrend] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const d = dateStr;
      const [s1, t1] = await Promise.all([
        api.get("/attendance/schools/daily", { params: { date: d } }),
        api.get("/attendance/trends", { params: { from: d, to: d } })
      ]);
      setSchoolsDaily(s1.data);
      setTrend(t1.data);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="card wide animate-slide-in">
      <h3 className="card_title" style={{ color: '#1f2937' }}>📈 Government Analytics</h3>

      <div className="grid md:grid-cols-4 gap-4">
        <div className="form_row">
          <Label className="form_label">Date</Label>
          <input className="form_input" type="date" value={dateStr} onChange={(e)=>setDateStr(e.target.value)} />
        </div>
        <div className="flex items-end">
          <Button className="btn_secondary" onClick={load} disabled={loading}>🔁 Refresh</Button>
        </div>
        {schoolsDaily && (
          <>
            <StatCard title="Total Schools" value={schoolsDaily.total_schools} />
            <StatCard title="Present Today" value={schoolsDaily.total_present} subtitle={`${schoolsDaily.total_students} total students`} accent="#059669" />
          </>
        )}
      </div>

      {schoolsDaily && (
        <div className="table_wrap" style={{ marginTop: '1rem' }}>
          <table>
            <thead>
              <tr>
                <th>School</th>
                <th>Total Students</th>
                <th>Present</th>
                <th>Attendance %</th>
              </tr>
            </thead>
            <tbody>
              {schoolsDaily.items.map(s => (
                <tr key={s.school_id}>
                  <td><span className="font-semibold text-gray-800">{s.name}</span></td>
                  <td>{s.total_students}</td>
                  <td>{s.present_count}</td>
                  <td>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-green-500 h-2 rounded-full" style={{ width: `${s.percent}%` }}></div>
                    </div>
                    <div className="text-xs text-gray-600 mt-1">{s.percent}%</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {trend && (
        <div className="card wide animate-fade-in" style={{ marginTop: '1rem' }}>
          <h4 className="font-semibold text-gray-800 mb-2">Daily Trend</h4>
          <div className="table_wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Present</th>
                  <th>Total Students</th>
                  <th>%</th>
                </tr>
              </thead>
              <tbody>
                {trend.items.map((d) => (
                  <tr key={d.date}>
                    <td>{d.date}</td>
                    <td>{d.present_count}</td>
                    <td>{d.total_students}</td>
                    <td>{d.percent}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}