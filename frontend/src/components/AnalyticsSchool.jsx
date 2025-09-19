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

export default function AnalyticsSchool() {
  const [dateStr, setDateStr] = useState(() => new Date().toISOString().slice(0,10));
  const [loading, setLoading] = useState(false);
  const [sectionsDaily, setSectionsDaily] = useState(null);
  const [teachersDaily, setTeachersDaily] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const d = dateStr;
      const [s1, t1] = await Promise.all([
        api.get("/attendance/sections/daily", { params: { date: d } }),
        api.get("/attendance/teachers/daily", { params: { date: d } }),
      ]);
      setSectionsDaily(s1.data);
      setTeachersDaily(t1.data);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const totalPct = sectionsDaily ? Math.round((sectionsDaily.total_present / Math.max(1, sectionsDaily.total_students)) * 100) : 0;

  return (
    <div className="card wide animate-slide-in">
      <h3 className="card_title" style={{ color: '#1f2937' }}>📈 School Daily Analytics</h3>

      <div className="grid md:grid-cols-5 gap-4">
        <div className="form_row">
          <Label className="form_label">Date</Label>
          <input className="form_input" type="date" value={dateStr} onChange={(e)=>setDateStr(e.target.value)} />
        </div>
        <div className="flex items-end">
          <Button className="btn_secondary" onClick={load} disabled={loading}>🔁 Refresh</Button>
        </div>
        {sectionsDaily && (
          <>
            <StatCard title="Sections" value={sectionsDaily.total_sections} />
            <StatCard title="Present" value={sectionsDaily.total_present} subtitle={`${sectionsDaily.total_students} students`} accent="#059669" />
            <StatCard title="Overall %" value={`${totalPct}%`} accent="#7c3aed" />
          </>
        )}
      </div>

      {sectionsDaily && (
        <div className="card wide animate-fade-in" style={{ marginTop: '1rem' }}>
          <h4 className="font-semibold text-gray-800 mb-2">Section-wise Attendance</h4>
          <div className="table_wrap">
            <table>
              <thead>
                <tr>
                  <th>Section</th>
                  <th>Total</th>
                  <th>Present</th>
                  <th>%</th>
                </tr>
              </thead>
              <tbody>
                {sectionsDaily.items.map((s) => (
                  <tr key={s.section_id}>
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
        </div>
      )}

      {teachersDaily && (
        <div className="card wide animate-fade-in" style={{ marginTop: '1rem' }}>
          <h4 className="font-semibold text-gray-800 mb-2">Teacher-wise Attendance</h4>
          <div className="table_wrap">
            <table>
              <thead>
                <tr>
                  <th>Teacher</th>
                  <th>Section</th>
                  <th>Present</th>
                  <th>% of Section</th>
                </tr>
              </thead>
              <tbody>
                {teachersDaily.items.map((t) => (
                  <tr key={t.teacher_id}>
                    <td>
                      <div className="font-semibold text-gray-800">{t.name}</div>
                      <div className="text-xs text-gray-500">{t.email}</div>
                    </td>
                    <td>{t.section_name || '-'}</td>
                    <td>{t.present_count}</td>
                    <td>{t.percent != null ? `${t.percent}%` : '-'}</td>
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