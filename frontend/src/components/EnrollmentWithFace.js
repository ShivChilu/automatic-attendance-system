import React, { useEffect, useMemo, useState } from "react";
import CameraCapture from "./CameraCapture";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

export default function EnrollmentWithFace({ sections = [] }) {
  const [selectedSec, setSelectedSec] = useState("");
  const [name, setName] = useState("");
  const [parentMobile, setParentMobile] = useState("");
  const [hasTwin, setHasTwin] = useState(false);
  const [twinGroupId, setTwinGroupId] = useState("");
  const [facingMode, setFacingMode] = useState("user");
  const [shots, setShots] = useState([]); // { blob, url }
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [sampleUrl, setSampleUrl] = useState("https://images.pexels.com/photos/2379004/pexels-photo-2379004.jpeg?auto=compress&cs=tinysrgb&dpr=1&w=256");

  const canSubmit = useMemo(() => name && selectedSec && shots.length >= 1, [name, selectedSec, shots.length]);

  const onCapture = (blob, url) => {
    setShots((arr) => (arr.length >= 5 ? arr : [...arr, { blob, url }]));
  };

  const removeShot = (idx) => {
    setShots((arr) => arr.filter((_, i) => i !== idx));
  };

  const addSample = async () => {
    try {
      setMessage("");
      const resp = await fetch(sampleUrl);
      const blob = await resp.blob();
      const reader = new FileReader();
      reader.onload = () => setShots((arr) => (arr.length >= 5 ? arr : [...arr, { blob, url: reader.result }]));
      reader.readAsDataURL(blob);
    } catch (e) {
      setMessage("Failed to load sample image URL");
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true); setMessage("");
    try {
      const fd = new FormData();
      fd.append("name", name);
      fd.append("section_id", selectedSec);
      if (parentMobile) fd.append("parent_mobile", parentMobile);
      fd.append("has_twin", hasTwin ? "true" : "false");
      if (twinGroupId) fd.append("twin_group_id", twinGroupId);
      shots.forEach((s, i) => fd.append("images", s.blob, `shot_${i+1}.jpg`));
      const res = await api.post("/students/enroll", fd);
      setMessage(`Enrolled ${res.data.name}. Embeddings: ${res.data.embeddings_count}`);
      setName(""); setParentMobile(""); setHasTwin(false); setTwinGroupId(""); setShots([]);
    } catch (err) {
      setMessage(err?.response?.data?.detail || "Enrollment failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h3>Enroll Student (Face)</h3>
      <form onSubmit={submit}>
        <div className="form_row"><Label>Section</Label>
          <select className="select" value={selectedSec} onChange={(e) => setSelectedSec(e.target.value)} required>
            <option value="">Select section</option>
            {sections.map((s) => (<option key={s.id} value={s.id}>{s.name}{s.grade ? ` (Grade ${s.grade})` : ''}</option>))}
          </select>
        </div>
        <div className="form_row"><Label>Student name</Label><Input value={name} onChange={(e) => setName(e.target.value)} required /></div>
        <div className="form_row"><Label>Parent mobile</Label><Input value={parentMobile} onChange={(e) => setParentMobile(e.target.value)} placeholder="9876543210" /></div>
        <div className="form_row" style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 8 }}>
          <label style={{ display:'flex', alignItems:'center', gap:8 }}>
            <input type="checkbox" checked={hasTwin} onChange={(e)=>setHasTwin(e.target.checked)} /> Has twin
          </label>
          <Input value={twinGroupId} onChange={(e)=>setTwinGroupId(e.target.value)} placeholder="Twin group id (optional)" />
        </div>

        <div className="form_row">
          <Label>Camera</Label>
          <CameraCapture facingMode={facingMode} onToggleFacing={()=>setFacingMode(facingMode === 'user' ? 'environment' : 'user')} onCapture={onCapture} captureLabel="Capture image" />
          <div className="muted small" style={{ marginTop: 6 }}>Tip: Capture 3–5 shots (front + sides). You can also add a sample URL for testing.</div>
          <div className="form_row" style={{ display:'grid', gridTemplateColumns:'1fr auto', gap: 8, marginTop: 8 }}>
            <Input value={sampleUrl} onChange={(e)=>setSampleUrl(e.target.value)} placeholder="Sample image URL" />
            <Button type="button" className="btn_secondary" onClick={addSample}>Add sample</Button>
          </div>
        </div>

        {shots.length > 0 && (
          <div className="thumbs">
            {shots.map((s, i) => (
              <div key={i} className="thumb">
                <img src={s.url} alt={`shot_${i+1}`} />
                <button type="button" className="btn_secondary" onClick={()=>removeShot(i)}>Remove</button>
              </div>
            ))}
          </div>
        )}

        {message && <div className="muted" style={{ marginTop: 8 }}>{message}</div>}
        <Button type="submit" className="btn_primary" disabled={!canSubmit || loading}>{loading ? 'Enrolling...' : 'Enroll Student'}</Button>
      </form>
    </div>
  );
}