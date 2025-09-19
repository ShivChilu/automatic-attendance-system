import React, { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import CameraCapture from "./CameraCapture";
import { Button } from "./ui/button";
import { Label } from "./ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";

function TimeSelect({ label, value, onChange }) {
  const times = useMemo(() => {
    const arr = [];
    for (let h = 7; h <= 19; h++) {
      for (let m = 0; m < 60; m += 15) {
        const hh = String(h).padStart(2, "0");
        const mm = String(m).padStart(2, "0");
        arr.push(`${hh}:${mm}`);
      }
    }
    return arr;
  }, []);
  return (
    <div className="form_row">
      <Label className="form_label">{label}</Label>
      <select className="select" value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Select</option>
        {times.map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
    </div>
  );
}

function minuteOfDay(hhmm) {
  if (!hhmm) return null;
  const [hh, mm] = hhmm.split(":").map((x) => parseInt(x, 10));
  if (Number.isNaN(hh) || Number.isNaN(mm)) return null;
  return hh * 60 + mm;
}

export default function TeacherAttendanceFlow({ me }) {
  const [sections, setSections] = useState([]);
  const [assignedSection, setAssignedSection] = useState(null);

  // Step A inputs
  const [dateStr, setDateStr] = useState(() => new Date().toISOString().slice(0, 10));
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");

  // Session state
  const [session, setSession] = useState(null);
  const [detail, setDetail] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [status, setStatus] = useState("");
  const [twinSelect, setTwinSelect] = useState({ open: false, candidates: [], blob: null });

  // History of today's sessions
  const [todaySessions, setTodaySessions] = useState([]);

  useEffect(() => {
    // Load sections to resolve assigned section name
    api.get("/sections").then((res) => {
      setSections(res.data || []);
      if (me?.section_id) {
        const s = res.data.find((x) => x.id === me.section_id);
        if (s) setAssignedSection(s);
      }
    }).catch(() => {});
  }, [me]);

  const loadSession = async (sessionId) => {
    try {
      const res = await api.get(`/attendance/sessions/${sessionId}`);
      setDetail(res.data);
    } catch (e) {
      // ignore
    }
  };

  const refreshTodaySessions = async () => {
    try {
      const res = await api.get("/attendance/sessions", { params: { date: new Date().toISOString().slice(0,10) } });
      setTodaySessions(res.data || []);
    } catch (e) {}
  };

  useEffect(() => { refreshTodaySessions(); }, []);

  const validateTimes = () => {
    const s = minuteOfDay(startTime);
    const e = minuteOfDay(endTime);
    if (s == null || e == null) return "Please select valid times";
    if (e <= s) return "End time must be after start time";
    const duration = e - s;
    if (duration < 45 || duration > 120) return "Class duration must be between 45 mins and 2 hours.";
    return null;
  };

  const startAttendance = async () => {
    setStatus("");
    if (!assignedSection) {
      alert("No section assigned to you. Ask admin to assign a section.");
      return;
    }
    // Date must be today only
    const todayStr = new Date().toISOString().slice(0,10);
    if (dateStr !== todayStr) {
      alert("Date must be today");
      return;
    }
    const err = validateTimes();
    if (err) { alert(err); return; }
    try {
      const res = await api.post("/attendance/sessions", {
        section_id: assignedSection.id,
        date: dateStr,
        start_time: startTime,
        end_time: endTime,
      });
      setSession(res.data);
      await loadSession(res.data.id);
      await refreshTodaySessions();
      setStatus("✅ Session started. You can begin scanning.");
    } catch (e) {
      alert(e?.response?.data?.detail || "Failed to start session");
    }
  };

  const onCapture = async (blob) => {
    if (!session) { setStatus("⚠️ Start a session first"); return; }
    setIsScanning(true);
    setStatus("🔍 Analyzing face...");
    try {
      const fd = new FormData();
      fd.append("image", blob, "scan.jpg");
      fd.append("section_id", session.section_id);
      fd.append("session_id", session.id);
      const res = await api.post("/attendance/mark", fd, { headers: { "Content-Type": "multipart/form-data" } });
      if (res.data?.twin_conflict && Array.isArray(res.data?.twin_candidates)) {
        setTwinSelect({ open: true, candidates: res.data.twin_candidates, blob });
        return;
      }
      const result = res.data.status || "";
      setStatus(result);
      await loadSession(session.id);
    } catch (e) {
      setStatus(`❌ ${e?.response?.data?.detail || "Scan failed"}`);
    } finally {
      setIsScanning(false);
    }
  };

  const confirmTwin = async (studentId) => {
    if (!session) return;
    try {
      const fd2 = new FormData();
      fd2.append("image", twinSelect.blob, "scan.jpg");
      fd2.append("section_id", session.section_id);
      fd2.append("session_id", session.id);
      fd2.append("confirmed_student_id", studentId);
      const res2 = await api.post("/attendance/mark", fd2, { headers: { "Content-Type": "multipart/form-data" } });
      const result2 = res2.data.status || "";
      setStatus(result2);
      await loadSession(session.id);
      setTwinSelect({ open: false, candidates: [], blob: null });
    } catch (e) {
      setStatus("❌ Twin confirmation failed");
    }
  };

  const manualMark = async (studentId, status) => {
    if (!session) return;
    try {
      await api.post("/attendance/manual-mark", { session_id: session.id, student_id: studentId, status });
      await loadSession(session.id);
    } catch (e) {
      alert(e?.response?.data?.detail || "Failed to update status");
    }
  };

  const submitSession = async () => {
    if (!session) return;
    if (!confirm(`Are you sure you want to submit attendance for Section ${assignedSection?.name} from ${session.start_time} to ${session.end_time}?`)) return;
    try {
      await api.post(`/attendance/sessions/${session.id}/submit`);
      await loadSession(session.id);
      setStatus("✅ Attendance submitted and locked.");
    } catch (e) {
      alert(e?.response?.data?.detail || "Failed to submit");
    }
  };

  const locked = !!detail?.session?.locked;

  return (
    <div className="card wide animate-slide-in">
      <h3 className="card_title" style={{ color: '#1f2937' }}>👨‍🏫 Mark Attendance</h3>

      {/* Step A: Select Section & Time */}
      {!session && (
        <div className="bg-white rounded-xl border-2 border-gray-200 p-4 mb-6">
          <div className="grid md:grid-cols-3 gap-4">
            <div className="form_row">
              <Label className="form_label">Section</Label>
              <select className="select" value={assignedSection?.id || ''} onChange={(e)=>{
                const s = sections.find(x => x.id === e.target.value);
                setAssignedSection(s || null);
              }} disabled={!!me?.section_id}>
                <option value="">— Select —</option>
                {sections.map(s => <option key={s.id} value={s.id}>{s.name}{s.grade ? ` (Grade ${s.grade})` : ''}</option>)}
              </select>
              {me?.section_id && <div className="text-xs text-gray-500 mt-1">Assigned section</div>}
            </div>
            <div className="form_row">
              <Label className="form_label">Date</Label>
              <input className="form_input" type="date" value={dateStr} onChange={(e)=>setDateStr(e.target.value)} max={new Date().toISOString().slice(0,10)} min={new Date().toISOString().slice(0,10)} />
              <div className="text-xs text-gray-500 mt-1">Only today is allowed</div>
            </div>
            <div className="hidden md:block" />
            <TimeSelect label="From Time" value={startTime} onChange={setStartTime} />
            <TimeSelect label="To Time" value={endTime} onChange={setEndTime} />
            <div className="flex items-end">
              <Button className="btn_primary" onClick={startAttendance}>▶️ Start Attendance</Button>
            </div>
          </div>
          <div className="text-sm text-gray-600 mt-2">Duration must be between 45 minutes and 2 hours.</div>
        </div>
      )}

      {/* Step B: Scanning and manual controls */}
      {session && (
        <div className="space-y-6">
          <div className={`p-4 rounded-xl ${locked ? 'bg-gray-100 border-2 border-gray-300' : 'bg-blue-50 border-2 border-blue-200'}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="font-semibold text-gray-800">Section: {assignedSection?.name}</div>
                <div className="text-sm text-gray-600">Time: {session.start_time} - {session.end_time} • Date: {session.date}</div>
              </div>
              <div className="flex gap-2">
                <Button className="btn_secondary" onClick={refreshTodaySessions}>🔁 Refresh Sessions</Button>
                {!locked && (
                  <Button className="btn_success" onClick={submitSession}>✅ Submit Attendance</Button>
                )}
              </div>
            </div>
          </div>

          {/* Scanner + Students */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <div className={`bg-gradient-to-br from-green-50 to-blue-50 border-2 rounded-xl p-6 ${locked ? 'opacity-60 pointer-events-none' : 'border-green-200'}`}>
                <CameraCapture 
                  facingMode={'user'}
                  onToggleFacing={()=>{}}
                  onCapture={(blob)=>onCapture(blob)} 
                  captureLabel={isScanning ? "🔍 Scanning..." : (locked ? "🔒 Session Locked" : "📸 Scan Student Face")} 
                />
                {status && (
                  <div className={`mt-4 p-3 rounded-xl text-sm ${status.includes('marked') ? 'bg-green-50 text-green-700 border border-green-200' : status.startsWith('❌') ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-blue-50 text-blue-700 border border-blue-200'}`}>{status}</div>
                )}
              </div>
            </div>

            <div>
              {/* Today's Sessions list */}
              <div className="bg-white rounded-xl border-2 border-gray-200 p-4 mb-6">
                <div className="font-semibold text-gray-800 mb-2">🗓️ Today's Sessions</div>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {todaySessions.map(s => (
                    <div key={s.id} className={`p-2 rounded-lg border ${session?.id === s.id ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-gray-50'}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-sm font-semibold text-gray-800">{s.start_time} - {s.end_time}</div>
                          <div className="text-xs text-gray-600">{s.date} {s.locked ? '• Locked' : ''}</div>
                        </div>
                        <Button className="btn_secondary" onClick={async()=>{ setSession(s); await loadSession(s.id); }}>Open</Button>
                      </div>
                    </div>
                  ))}
                  {todaySessions.length === 0 && <div className="text-xs text-gray-500">No sessions yet</div>}
                </div>
              </div>
            </div>
          </div>

          {/* Students table */}
          {detail && (
            <div>
              <div className="table_wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Status</th>
                      <th>Marked At</th>
                      {!locked && <th>Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {detail.students.map(st => (
                      <tr key={st.student_id}>
                        <td><span className="font-semibold text-gray-800">{st.name}</span></td>
                        <td>
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${st.status === 'Present' ? 'bg-green-100 text-green-800 border border-green-200' : st.status === 'Absent' ? 'bg-red-100 text-red-800 border border-red-200' : 'bg-gray-100 text-gray-600 border border-gray-200'}`}>
                            {st.status}
                          </span>
                        </td>
                        <td><span className="text-xs text-gray-500">{st.marked_at ? new Date(st.marked_at).toLocaleTimeString() : '-'}</span></td>
                        {!locked && (
                          <td style={{display:'flex', gap:'0.5rem'}}>
                            <Button className="btn_success" onClick={()=> manualMark(st.student_id, 'Present')}>Mark Present</Button>
                            <Button className="btn_danger" onClick={()=> manualMark(st.student_id, 'Absent')}>Mark Absent</Button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Twin selection dialog */}
      <Dialog open={twinSelect.open} onOpenChange={(open)=> setTwinSelect(prev => ({...prev, open}))}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>👯 Two students detected as similar. Please confirm manually.</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-3">
            {twinSelect.candidates.map(c => (
              <div key={c.id} className="flex items-center justify-between p-3 border rounded-xl">
                <div>
                  <div className="font-semibold">{c.name}</div>
                  <div className="text-xs text-gray-500">ID: {c.id}</div>
                </div>
                <Button className="btn_primary" onClick={() => confirmTwin(c.id)}>Select</Button>
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button className="btn_secondary" onClick={()=> setTwinSelect({ open: false, candidates: [], blob: null })}>Cancel</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}