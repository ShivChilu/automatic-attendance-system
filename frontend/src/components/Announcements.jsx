import React, { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

export default function Announcements({ me }) {
  const isAdmin = me?.role === 'SCHOOL_ADMIN' || me?.role === 'CO_ADMIN';
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [sendAll, setSendAll] = useState(true);
  const [teachers, setTeachers] = useState([]);
  const [selectedTeacherIds, setSelectedTeacherIds] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const loadTeachers = async () => {
    try {
      const res = await api.get("/users", { params: { role: "TEACHER" } });
      setTeachers(res.data.users || []);
    } catch (e) { setTeachers([]); }
  };

  const loadAnnouncements = async () => {
    try {
      const res = await api.get("/announcements");
      setItems(res.data.items || []);
    } catch (e) { setItems([]); }
  };

  useEffect(() => { loadAnnouncements(); if (isAdmin) loadTeachers(); }, [me]);

  const submit = async (e) => {
    e.preventDefault();
    setMsg(""); setLoading(true);
    try {
      const payload = { title, description, target_all: sendAll };
      if (!sendAll) payload.target_teacher_ids = selectedTeacherIds;
      const res = await api.post("/announcements", payload);
      setMsg("✅ Announcement sent");
      setTitle(""); setDescription(""); setSelectedTeacherIds([]); setSendAll(true);
      loadAnnouncements();
    } catch (e) {
      setMsg(`❌ ${e?.response?.data?.detail || 'Failed to send'}`);
    } finally { setLoading(false); }
  };

  return (
    <div className="card wide animate-slide-in">
      <h3 className="card_title" style={{ color: '#1f2937' }}>📢 Announcements</h3>

      {isAdmin && (
        <form onSubmit={submit} className="space-y-4">
          <div className="form_row">
            <Label className="form_label">Title</Label>
            <Input value={title} onChange={(e)=>setTitle(e.target.value)} className="form_input" placeholder="Short title" required />
          </div>
          <div className="form_row">
            <Label className="form_label">Description</Label>
            <textarea className="form_input" rows={4} value={description} onChange={(e)=>setDescription(e.target.value)} placeholder="Details" required />
          </div>
          <div className="form_row">
            <Label className="form_label">Target</Label>
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm">
                <input type="radio" name="target" checked={sendAll} onChange={()=>{ setSendAll(true); setSelectedTeacherIds([]); }} /> All Teachers
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="radio" name="target" checked={!sendAll} onChange={()=> setSendAll(false)} /> Specific Teachers
              </label>
              {!sendAll && (
                <select multiple className="select" value={selectedTeacherIds} onChange={(e)=> setSelectedTeacherIds(Array.from(e.target.selectedOptions).map(o=>o.value))}>
                  {teachers.map(t => <option key={t.id} value={t.id}>{t.full_name} — {t.email}</option>)}
                </select>
              )}
            </div>
          </div>
          <Button className="btn_primary" type="submit" disabled={loading}>{loading ? 'Sending...' : 'Send Announcement'}</Button>
          {msg && <div className={msg.startsWith('✅') ? 'success_message' : 'error_text'}>{msg}</div>}
        </form>
      )}

      <div className="mt-8">
        <h4 className="text-lg font-semibold text-gray-800 mb-2">Recent</h4>
        <div className="space-y-3">
          {items.map(it => (
            <div key={it.id} className="p-3 border rounded-xl bg-white">
              <div className="font-semibold text-gray-900">{it.title}</div>
              <div className="text-sm text-gray-700 line-clamp-2">{it.description}</div>
              <div className="text-xs text-gray-500 mt-1">{new Date(it.created_at).toLocaleString()} {it.target_all ? '• All Teachers' : `• ${it.target_teacher_ids?.length || 0} teacher(s)`}</div>
            </div>
          ))}
          {items.length === 0 && <div className="text-xs text-gray-500">No announcements yet</div>}
        </div>
      </div>
    </div>
  );
}
