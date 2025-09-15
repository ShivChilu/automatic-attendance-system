import React, { useEffect, useMemo, useState } from "react";
import CameraCapture from "./CameraCapture";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Label } from "./ui/label";

export default function TeacherScan({ me }) {
  const [facingMode, setFacingMode] = useState("user");
  const [section, setSection] = useState(null);
  const [sections, setSections] = useState([]);
  const [status, setStatus] = useState("");
  const [summary, setSummary] = useState(null);
  const [sampleUrl, setSampleUrl] = useState("https://images.pexels.com/photos/2379004/pexels-photo-2379004.jpeg?auto=compress&cs=tinysrgb&dpr=1&w=256");

  useEffect(() => {
    api.get("/sections").then((res) => {
      setSections(res.data);
      if (me?.section_id) {
        const s = res.data.find((x) => x.id === me.section_id);
        if (s) setSection(s);
      }
    }).catch(()=>{});
  }, [me]);

  const onCapture = async (blob) => {
    try {
      if (!section) { setStatus("Select a section first"); return; }
      const fd = new FormData();
      fd.append("image", blob, "scan.jpg");
      const res = await api.post("/attendance/mark", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setStatus(res.data.status || "");
      await loadSummary(section.id);
    } catch (err) {
      setStatus(err?.response?.data?.detail || "Scan failed");
    }
  };

  const addSampleAndScan = async () => {
    try {
      setStatus("");
      const resp = await fetch(sampleUrl);
      const blob = await resp.blob();
      await onCapture(blob);
    } catch (e) {
      setStatus("Failed to load sample image URL");
    }
  };

  const loadSummary = async (sectionId) => {
    try {
      const today = new Date().toISOString().slice(0,10);
      const res = await api.get("/attendance/summary", { params: { section_id: sectionId, date: today } });
      setSummary(res.data);
    } catch (e) {
      // ignore for now
    }
  };

  useEffect(() => {
    if (section) loadSummary(section.id);
  }, [section]);

  return (
    <div className="card wide">
      <h3>Scan Attendance</h3>
      <div className="form_row"><Label>Section</Label>
        <select className="select" value={section?.id || ''} onChange={(e) => {
          const s = sections.find((x) => x.id === e.target.value);
          setSection(s || null);
        }}>
          <option value="">Select section</option>
          {sections.map((s) => (<option key={s.id} value={s.id}>{s.name}{s.grade ? ` (Grade ${s.grade})` : ''}</option>))}
        </select>
      </div>

      <CameraCapture facingMode={facingMode} onToggleFacing={()=>setFacingMode(facingMode === 'user' ? 'environment' : 'user')} onCapture={(blob)=>onCapture(blob)} captureLabel="Scan Student" />
      <div className="form_row" style={{ display:'grid', gridTemplateColumns:'1fr auto', gap: 8, marginTop: 8 }}>
        <input className="input" value={sampleUrl} onChange={(e)=>setSampleUrl(e.target.value)} placeholder="Sample image URL" />
        <Button type="button" className="btn_secondary" onClick={addSampleAndScan}>Use sample</Button>
      </div>

      {status && <div className="muted" style={{ marginTop: 8 }}>{status}</div>}

      {summary && (
        <div className="table_wrap" style={{ marginTop: 12 }}>
          <table>
            <thead><tr><th>Student</th><th>Present</th></tr></thead>
            <tbody>
              {summary.items.map((it) => (
                <tr key={it.student_id}>
                  <td>{it.name}</td>
                  <td>{it.present ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="muted" style={{ marginTop: 8 }}>Present: {summary.present_count} / {summary.total}</div>
        </div>
      )}
    </div>
  );
}