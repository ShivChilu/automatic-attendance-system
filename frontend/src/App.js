import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import "./App.css";
// shadcn ui components
import { Button } from "./components/ui/button";
import { Card } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import EnrollmentWithFace from "./components/EnrollmentWithFace";
import TeacherScan from "./components/TeacherScan";
import Sidebar from "./components/Sidebar";
import TeacherAttendanceFlow from "./components/TeacherAttendanceFlow.jsx";
import AnalyticsGov from "./components/AnalyticsGov.jsx";
import AnalyticsSchool from "./components/AnalyticsSchool.jsx";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API });

function useAuth() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [me, setMe] = useState(null);

  useEffect(() => {
    if (token) {
      localStorage.setItem("token", token);
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      api.get("/auth/me").then((res) => setMe(res.data)).catch(() => setMe(null));
    } else {
      delete api.defaults.headers.common["Authorization"];
      localStorage.removeItem("token");
      setMe(null);
    }
  }, [token]);

  return { token, setToken, me };
}

function useMySchool(enabled) {
  const [school, setSchool] = useState(null);
  useEffect(() => {
    if (!enabled) return;
    api.get("/schools/my").then((res) => setSchool(res.data)).catch(() => setSchool(null));
  }, [enabled]);
  return school;
}

function StatsCard({ title, value, icon, gradient, trend }) {
  return (
    <div className="card narrow animate-scale-in">
      <div className="stats_card" style={{ background: 'white', color: '#1f2937' }}>
        <div className="stats_number" style={{ color: '#1e40af' }}>{value}</div>
        <div className="stats_label" style={{ color: '#6b7280' }}>{title}</div>
        {trend && (
          <div className="text-xs mt-2" style={{ color: '#6b7280' }}>
            {trend > 0 ? '↗️' : '↘️'} {Math.abs(trend)}% from last month
          </div>
        )}
      </div>
    </div>
  );
}

function HeroSection({ title, subtitle, backgroundImage }) {
  return (
    <div className="card wide animate-fade-in" style={{ 
      backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.4)), url(${backgroundImage})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      color: 'white',
      minHeight: '200px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      textAlign: 'center',
      textShadow: '0 2px 4px rgba(0,0,0,0.8)'
    }}>
      <h1 className="text-4xl font-extrabold mb-4" style={{ color: 'white', textShadow: '0 2px 4px rgba(0,0,0,0.8)' }}>
        {title}
      </h1>
      <p className="text-xl font-medium" style={{ color: 'rgba(255,255,255,0.95)', textShadow: '0 1px 2px rgba(0,0,0,0.8)' }}>
        {subtitle}
      </p>
    </div>
  );
}

function Login({ onLoggedIn }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/auth/login", { email, password });
      onLoggedIn(res.data.access_token);
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="auth_box animate-scale-in">
        <h2 className="auth_title">Welcome Back</h2>
        <form onSubmit={submit}>
          <div className="form_row">
            <Label htmlFor="email" className="form_label" style={{ color: '#374151' }}>Email Address</Label>
            <Input 
              id="email" 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              className="form_input"
              placeholder="Enter your email address"
              required 
            />
          </div>
          <div className="form_row">
            <Label htmlFor="password" className="form_label" style={{ color: '#374151' }}>Password</Label>
            <Input 
              id="password" 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              className="form_input"
              placeholder="Enter your password"
              required 
            />
          </div>
          {error && <div className="error_text">⚠️ {error}</div>}
          <Button disabled={loading} className="btn_primary" type="submit" style={{ width: '100%', marginTop: '1rem' }}>
            {loading ? "Signing in..." : "Sign In"}
          </Button>
        </form>
        <div className="note">
          💡 <strong>Tip:</strong> Your login credentials are automatically emailed when your account is created by an administrator.
        </div>
      </div>
    </div>
  );
}

function GovAdmin({ me, currentSection, onSectionChange }) {
  const [form, setForm] = useState({ name: "", address_line1: "", city: "", state: "", pincode: "", principal_name: "", principal_email: "", principal_phone: "" });
  const [message, setMessage] = useState("");
  const [schools, setSchools] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState({});
  const [stats, setStats] = useState({ totalSchools: 0, totalStudents: 0, totalTeachers: 0 });

  const loadSchools = async () => {
    const res = await api.get("/schools");
    setSchools(res.data);
    setStats({
      totalSchools: res.data.length,
      totalStudents: res.data.reduce((acc, school) => acc + (school.student_count || 0), 0),
      totalTeachers: res.data.reduce((acc, school) => acc + (school.teacher_count || 0), 0)
    });
  };
  useEffect(() => { loadSchools(); }, []);

  const createSchool = async (e) => {
    e.preventDefault();
    setMessage("");
    try {
      const res = await api.post("/schools", form);
      setMessage(`✅ Successfully created school: ${res.data.name}`);
      setForm({ name: "", address_line1: "", city: "", state: "", pincode: "", principal_name: "", principal_email: "", principal_phone: "" });
      loadSchools();
    } catch (err) {
      setMessage(`❌ ${err?.response?.data?.detail || "Failed to create school"}`);
    }
  };

  const resend = async (email) => {
    try { 
      await api.post("/users/resend-credentials", { email }); 
      alert("✅ Credentials resent successfully"); 
    } catch (e) { 
      alert("❌ Failed to resend credentials"); 
    }
  };

  const startEdit = (s) => { setEditingId(s.id); setEditDraft({ ...s }); };
  const cancelEdit = () => { setEditingId(null); setEditDraft({}); };
  const saveEdit = async () => {
    const payload = { ...editDraft };
    delete payload.id; delete payload.created_at;
    await api.put(`/schools/${editingId}`, payload);
    setEditingId(null); setEditDraft({}); loadSchools();
  };
  const removeSchool = async (id) => {
    if (!confirm("⚠️ Are you sure you want to delete this school? All its sections, students, and users will be permanently removed.")) return;
    await api.delete(`/schools/${id}`); loadSchools();
  };

  const renderContent = () => {
    if (currentSection === 'create-school') {
      return (
        <div className="card wide animate-slide-in">
          <h3 className="card_title" style={{ color: '#1f2937' }}>🏫 Create New School</h3>
          <form onSubmit={createSchool}>
            <div className="form_row">
              <Label className="form_label" style={{ color: '#374151' }}>School Name</Label>
              <Input 
                value={form.name} 
                onChange={(e) => setForm({ ...form, name: e.target.value })} 
                className="form_input"
                placeholder="Enter school name"
                required 
              />
            </div>
            <div className="form_row">
              <Label className="form_label" style={{ color: '#374151' }}>Address</Label>
              <Input 
                value={form.address_line1} 
                onChange={(e) => setForm({ ...form, address_line1: e.target.value })} 
                className="form_input"
                placeholder="Enter school address"
              />
            </div>
            <div className="form_row" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '1rem' }}>
              <div>
                <Label className="form_label" style={{ color: '#374151' }}>City</Label>
                <Input 
                  value={form.city} 
                  onChange={(e) => setForm({ ...form, city: e.target.value })} 
                  className="form_input"
                  placeholder="City"
                />
              </div>
              <div>
                <Label className="form_label" style={{ color: '#374151' }}>State</Label>
                <Input 
                  value={form.state} 
                  onChange={(e) => setForm({ ...form, state: e.target.value })} 
                  className="form_input"
                  placeholder="State"
                />
              </div>
              <div>
                <Label className="form_label" style={{ color: '#374151' }}>Pincode</Label>
                <Input 
                  value={form.pincode} 
                  onChange={(e) => setForm({ ...form, pincode: e.target.value })} 
                  className="form_input"
                  placeholder="Pincode"
                />
              </div>
            </div>
            <div className="form_row">
              <Label className="form_label" style={{ color: '#374151' }}>Principal Name</Label>
              <Input 
                value={form.principal_name} 
                onChange={(e) => setForm({ ...form, principal_name: e.target.value })} 
                className="form_input"
                placeholder="Enter principal's full name"
                required 
              />
            </div>
            <div className="form_row" style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: '1rem' }}>
              <div>
                <Label className="form_label" style={{ color: '#374151' }}>Principal Email</Label>
                <Input 
                  type="email" 
                  value={form.principal_email} 
                  onChange={(e) => setForm({ ...form, principal_email: e.target.value })} 
                  className="form_input"
                  placeholder="principal@school.edu"
                  required 
                />
              </div>
              <div>
                <Label className="form_label" style={{ color: '#374151' }}>Principal Phone</Label>
                <Input 
                  value={form.principal_phone} 
                  onChange={(e) => setForm({ ...form, principal_phone: e.target.value })} 
                  className="form_input"
                  placeholder="+91 98765 43210"
                />
              </div>
            </div>
            <Button type="submit" className="btn_primary">🏗️ Create School</Button>
          </form>
          {message && (
            <div className={message.includes('✅') ? 'success_message' : 'error_text'} style={{ marginTop: '1rem' }}>
              {message}
            </div>
          )}
        </div>
      );
    } else if (currentSection === 'manage-schools') {
      return (
        <div className="card wide animate-slide-in">
          <h3 className="card_title" style={{ color: '#1f2937' }}>🏫 All Schools Management</h3>
          <div className="table_wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ color: '#374151' }}>School Name</th>
                  <th style={{ color: '#374151' }}>City</th>
                  <th style={{ color: '#374151' }}>Principal</th>
                  <th style={{ color: '#374151' }}>Email</th>
                  <th style={{ color: '#374151' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {schools.map((s) => (
                  <tr key={s.id}>
                    <td>
                      {editingId === s.id ? 
                        <Input value={editDraft.name} onChange={(e)=>setEditDraft({...editDraft, name: e.target.value})} className="form_input" /> 
                        : <span className="font-semibold" style={{ color: '#1f2937' }}>{s.name}</span>
                      }
                    </td>
                    <td style={{ color: '#4b5563' }}>
                      {editingId === s.id ? 
                        <Input value={editDraft.city || ''} onChange={(e)=>setEditDraft({...editDraft, city: e.target.value})} className="form_input" /> 
                        : (s.city || <span style={{ color: '#9ca3af' }}>-</span>)
                      }
                    </td>
                    <td style={{ color: '#4b5563' }}>
                      {editingId === s.id ? 
                        <Input value={editDraft.principal_name || ''} onChange={(e)=>setEditDraft({...editDraft, principal_name: e.target.value})} className="form_input" /> 
                        : (s.principal_name || <span style={{ color: '#9ca3af' }}>-</span>)
                      }
                    </td>
                    <td style={{ color: '#4b5563' }}>
                      {editingId === s.id ? 
                        <Input value={editDraft.principal_email || ''} onChange={(e)=>setEditDraft({...editDraft, principal_email: e.target.value})} className="form_input" /> 
                        : (s.principal_email || <span style={{ color: '#9ca3af' }}>-</span>)
                      }
                    </td>
                    <td style={{display:'flex',gap:'0.5rem', alignItems: 'center'}}>
                      <Button 
                        className="btn_secondary" 
                        onClick={() => resend(s.principal_email)} 
                        disabled={!s.principal_email}
                        title="Resend login credentials"
                      >
                        📧 Resend
                      </Button>
                      {editingId === s.id ? (
                        <>
                          <Button className="btn_success" onClick={saveEdit}>✅ Save</Button>
                          <Button className="btn_secondary" onClick={cancelEdit}>❌ Cancel</Button>
                        </>
                      ) : (
                        <>
                          <Button className="btn_secondary" onClick={() => startEdit(s)}>✏️ Edit</Button>
                          <Button className="btn_danger" onClick={() => removeSchool(s.id)}>🗑️ Delete</Button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    } else if (currentSection === 'analytics') {
      return <AnalyticsGov />;
    } else {
      return (
        <>
          <HeroSection 
            title="Government Education Dashboard"
            subtitle="Manage schools, monitor attendance, and oversee educational infrastructure"
            backgroundImage="https://images.unsplash.com/photo-1519389950473-47ba0277781c"
          />
          <StatsCard title="Total Schools" value={stats.totalSchools} gradient="linear-gradient(135deg, #667eea 0%, #764ba2 100%)" trend={8} />
          <StatsCard title="Total Students" value={stats.totalStudents.toLocaleString()} gradient="linear-gradient(135deg, #f093fb 0%, #f5576c 100%)" trend={12} />
          <StatsCard title="Total Teachers" value={stats.totalTeachers.toLocaleString()} gradient="linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)" trend={5} />
        </>
      );
    }
  };

  return (
    <div className="dash_grid">
      {renderContent()}
    </div>
  );
}

function SchoolAdminLike({ me, currentSection, onSectionChange }) {
  const school = useMySchool(!!me);
  const [sections, setSections] = useState([]);
  const [students, setStudents] = useState([]);

  const [secName, setSecName] = useState("");
  const [secGrade, setSecGrade] = useState("");
  const [editingSection, setEditingSection] = useState(null);
  const [sectionDraft, setSectionDraft] = useState({});

  const [stuName, setStuName] = useState("");
  const [rollNo, setRollNo] = useState("");
  const [parentMobile, setParentMobile] = useState("");
  const [selectedSec, setSelectedSec] = useState("");

  const [roleType, setRoleType] = useState("TEACHER");
  const [tName, setTName] = useState("");
  const [tEmail, setTEmail] = useState("");
  const [tPhone, setTPhone] = useState("");
  const [subject, setSubject] = useState("Math");
  const [teacherSection, setTeacherSection] = useState("");

  const [teachers, setTeachers] = useState([]);
  const [coadmins, setCoadmins] = useState([]);

  const createCredential = async (e) => {
    e.preventDefault();
    try {
      if (roleType === 'TEACHER') {
        const payload = { full_name: tName, email: tEmail, phone: tPhone || undefined, subject };
        if (teacherSection === 'ALL') {
          payload.all_sections = true;
        } else if (Array.isArray(teacherSection) && teacherSection.length > 0) {
          payload.section_ids = teacherSection;
        }
        await api.post('/users/teachers', payload);
        alert('✅ Teacher created. Credentials emailed.');
      } else if (roleType === 'CO_ADMIN') {
        await api.post('/users/coadmins', { full_name: tName, email: tEmail, phone: tPhone || undefined });
        alert('✅ Co-Admin created. Credentials emailed.');
      } else {
        alert('⚠️ Students can only be added via Face Enrollment.');
      }
      setTName(''); setTEmail(''); setTPhone(''); setTeacherSection('');
      loadStaff();
    } catch (err) {
      alert(err?.response?.data?.detail || '❌ Failed to create credentials');
    }
  };

  const loadSections = async () => {
    const sec = await api.get("/sections");
    setSections(sec.data);
  };
  const loadStaff = async () => {
    const t = await api.get("/users", { params: { role: "TEACHER" } });
    const c = await api.get("/users", { params: { role: "CO_ADMIN" } });
    setTeachers(t.data.users || []);
    setCoadmins(c.data.users || []);
  };
  useEffect(() => { loadSections(); loadStaff(); }, []);

  const addSection = async (e) => {
    e.preventDefault();
    await api.post("/sections", { school_id: me.school_id, name: secName, grade: secGrade || undefined });
    setSecName(""); setSecGrade(""); loadSections();
  };

  const editSection = (s) => { setEditingSection(s.id); setSectionDraft({ name: s.name, grade: s.grade || '' }); };
  const saveSection = async () => {
    await api.put(`/sections/${editingSection}`, { ...sectionDraft, grade: sectionDraft.grade || undefined });
    setEditingSection(null); setSectionDraft({}); loadSections();
  };
  const deleteSection = async (id) => {
    if (!confirm("⚠️ Delete this section? All students in it will be removed.")) return;
    await api.delete(`/sections/${id}`); if (selectedSec === id) setSelectedSec(""); loadSections(); setStudents([]);
  };

  const addStudent = async (e) => {
    e.preventDefault();
    await api.post("/students/create", { name: stuName, roll_no: rollNo, section_id: selectedSec, parent_mobile: parentMobile || undefined });
    setStuName(""); setRollNo(""); setParentMobile("");
    if (selectedSec) { const list = await api.get(`/students?section_id=${selectedSec}`); setStudents(list.data); }
  };
  const editStudent = async (st, updates) => {
    await api.put(`/students/${st.id}`, updates);
    if (selectedSec) { const list = await api.get(`/students?section_id=${selectedSec}`); setStudents(list.data); }
  };
  const deleteStudent = async (id) => {
    if (!confirm("⚠️ Delete this student?")) return;
    await api.delete(`/students/${id}`);
    if (selectedSec) { const list = await api.get(`/students?section_id=${selectedSec}`); setStudents(list.data); }
  };

  const resendUser = async (email) => {
    try { await api.post('/users/resend-credentials', { email }); alert('✅ Credentials resent'); }
    catch { alert('❌ Failed to resend'); }
  };

  const updateTeacher = async (userId, updates) => {
    await api.put(`/users/${userId}`, updates);
    loadStaff();
  };
  const deleteTeacher = async (userId) => {
    if (!confirm('⚠️ Delete this teacher?')) return;
    await api.delete(`/users/${userId}`);
    loadStaff();
  };

  const loadStudents = async (secId) => {
    setSelectedSec(secId);
    if (!secId) { setStudents([]); return; }
    try {
      const list = await api.get(`/students?section_id=${secId}&enrolled_only=false`);
      setStudents(Array.isArray(list.data) ? list.data : []);
    } catch (e) {
      setStudents([]);
    }
  };

  const isSchoolAdmin = me?.role === 'SCHOOL_ADMIN';

  const renderContent = () => {
    if (currentSection === 'enrollment') {
      return <EnrollmentWithFace sections={sections} onEnrolled={async (enrolled) => {
        try {
          setSelectedSec(enrolled.section_id);
          const list = await api.get(`/students?section_id=${enrolled.section_id}&enrolled_only=false`);
          setStudents(list.data || []);
        } catch (e) {}
      }} />;
    } else if (currentSection === 'sections') {
      return (
        <div className="card wide animate-slide-in">
          <h3 className="card_title" style={{ color: '#1f2937' }}>📚 Manage Sections</h3>
          <form onSubmit={addSection}>
            <div className="form_row">
              <Label className="form_label" style={{ color: '#374151' }}>Section Name</Label>
              <Input 
                value={secName} 
                onChange={(e) => setSecName(e.target.value)} 
                className="form_input"
                placeholder="e.g., 8-A, Grade 5"
                required 
              />
            </div>
            <div className="form_row">
              <Label className="form_label" style={{ color: '#374151' }}>Grade Level</Label>
              <Input 
                value={secGrade} 
                onChange={(e) => setSecGrade(e.target.value)} 
                className="form_input"
                placeholder="e.g., 8, 10, 12"
              />
            </div>
            <Button className="btn_primary" type="submit">➕ Add Section</Button>
          </form>

          {sections.length > 0 && (
            <div className="table_wrap" style={{marginTop: '1rem'}}>
              <table>
                <thead>
                  <tr>
                    <th style={{ color: '#374151' }}>Section Name</th>
                    <th style={{ color: '#374151' }}>Grade</th>
                    {isSchoolAdmin && <th style={{ color: '#374151' }}>Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {sections.map((s) => (
                    <tr key={s.id}>
                      <td>
                        {editingSection === s.id ? 
                          <Input value={sectionDraft.name} onChange={(e)=>setSectionDraft({...sectionDraft, name:e.target.value})} className="form_input" /> 
                          : <span className="font-semibold" style={{ color: '#1f2937' }}>{s.name}</span>
                        }
                      </td>
                      <td style={{ color: '#4b5563' }}>
                        {editingSection === s.id ? 
                          <Input value={sectionDraft.grade || ''} onChange={(e)=>setSectionDraft({...sectionDraft, grade:e.target.value})} className="form_input" /> 
                          : (s.grade || <span style={{ color: '#9ca3af' }}>-</span>)
                        }
                      </td>
                      {isSchoolAdmin && (
                        <td style={{display:'flex',gap:'0.5rem'}}>
                          {editingSection === s.id ? (
                            <>
                              <Button className="btn_success" onClick={saveSection}>✅ Save</Button>
                              <Button className="btn_secondary" onClick={()=>{setEditingSection(null); setSectionDraft({});}}>❌ Cancel</Button>
                            </>
                          ) : (
                            <>
                              <Button className="btn_secondary" onClick={()=>editSection(s)}>✏️ Edit</Button>
                              <Button className="btn_danger" onClick={()=>deleteSection(s.id)}>🗑️ Delete</Button>
                            </>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      );
    } else if (currentSection === 'teachers') {
      return (
        <div className="card wide animate-slide-in">
          <h3 className="card_title" style={{ color: '#1f2937' }}>👨‍🏫 Teachers</h3>
          <div className="table_wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ color: '#374151' }}>Name</th>
                  <th style={{ color: '#374151' }}>Email</th>
                  <th style={{ color: '#374151' }}>Phone</th>
                  <th style={{ color: '#374151' }}>Subject</th>
                  <th style={{ color: '#374151' }}>Section</th>
                  <th style={{ color: '#374151' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {teachers.map((t) => (
                  <tr key={t.id}>
                    <td>
                      <Input defaultValue={t.full_name} onBlur={(e)=> updateTeacher(t.id, { full_name: e.target.value })} className="form_input" />
                    </td>
                    <td style={{ color: '#4b5563' }}>{t.email}</td>
                    <td>
                      <Input defaultValue={t.phone || ''} onBlur={(e)=> updateTeacher(t.id, { phone: e.target.value || undefined })} className="form_input" />
                    </td>
                    <td>
                      <select className="select" defaultValue={t.subject || 'Other'} onChange={(e)=> updateTeacher(t.id, { subject: e.target.value })}>
                        {['Math','Science','English','Social','Telugu','Hindi','Other'].map((s)=> <option key={s} value={s}>{s}</option>)}
                      </select>
                    </td>
                    <td>
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-xs text-gray-600">
                          <input type="checkbox" defaultChecked={!!t.all_sections} onChange={async (e)=>{
                            await updateTeacher(t.id, { all_sections: e.target.checked, section_ids: e.target.checked ? [] : (t.section_ids || []) , section_id: e.target.checked ? null : (t.section_ids?.[0] || null) });
                            loadStaff();
                          }} /> All
                        </label>
                        <select className="select" multiple defaultValue={t.section_ids || (t.section_id ? [t.section_id] : [])} onChange={async (e)=>{
                          const vals = Array.from(e.target.selectedOptions).map(o=>o.value);
                          await updateTeacher(t.id, { section_ids: vals, all_sections: false, section_id: vals[0] || null });
                          loadStaff();
                        }} disabled={t.all_sections}>
                          {sections.map((s)=> <option key={s.id} value={s.id}>{s.name}{s.grade ? ` (Grade ${s.grade})` : ''}</option>)}
                        </select>
                      </div>
                    </td>
                    <td style={{display:'flex',gap:'0.5rem'}}>
                      <Button className="btn_secondary" onClick={()=> resendUser(t.email)}>📧 Resend</Button>
                      <Button className="btn_danger" onClick={()=> deleteTeacher(t.id)}>🗑️ Delete</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    } else if (currentSection === 'students') {
      return (
        <div className="card wide animate-slide-in">
          <h3 className="card_title" style={{ color: '#1f2937' }}>👨‍🎓 Student Management</h3>
          <div className="form_row">
            <Label className="form_label" style={{ color: '#374151' }}>Select Section</Label>
            <select className="select" value={selectedSec} onChange={(e) => loadStudents(e.target.value)}>
              <option value="">— Choose a Section —</option>
              {sections.map((s) => (<option key={s.id} value={s.id}>{s.name}{s.grade ? ` (Grade ${s.grade})` : ''}</option>))}
            </select>
          </div>
          {selectedSec && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mt-4">
              <div className="text-blue-800 text-sm">
                ⚠️ Students can only be added via the Face Enrollment flow. Use the "Face Enrollment" section to enroll students; they will appear here automatically after a successful enrollment.
              </div>
              <div className="mt-2">
                <Button className="btn_secondary" onClick={() => onSectionChange('enrollment')}>🎭 Go to Face Enrollment</Button>
              </div>
            </div>
          )}
          {selectedSec && (
            <div className="table_wrap" style={{marginTop: '1rem'}}>
              <table>
                <thead>
                  <tr>
                    <th style={{ color: '#374151' }}>ID</th>
                    <th style={{ color: '#374151' }}>Name</th>
                    <th style={{ color: '#374151' }}>Parent Mobile</th>
                    <th style={{ color: '#374151' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((st) => (
                    <tr key={st.id}>
                      <td style={{ width: '90px' }}>
                        <div className="form_input" style={{ background: '#f9fafb', border: '1px solid #e5e7eb' }}>{st.roll_no || st.student_code}</div>
                      </td>
                      <td>
                        <Input defaultValue={st.name} onBlur={(e)=> editStudent(st, { name: e.target.value })} className="form_input" />
                      </td>
                      <td>
                        <Input defaultValue={st.parent_mobile || ''} onBlur={(e)=> editStudent(st, { parent_mobile: e.target.value || undefined })} className="form_input" />
                      </td>
                      <td style={{display:'flex',gap:'0.5rem'}}>
                        <Button className="btn_danger" onClick={()=> deleteStudent(st.id)}>🗑️ Delete</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      );
    } else if (currentSection === 'create-staff') {
      return (
        <div className="card wide animate-slide-in">
          <h3 className="card_title" style={{ color: '#1f2937' }}>👥 Create Staff Credentials</h3>
          <div className="form_row">
            <Label className="form_label" style={{ color: '#374151' }}>Staff Role</Label>
            <Select value={roleType} onValueChange={setRoleType}>
              <SelectTrigger><SelectValue placeholder="Select role" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="TEACHER">👨‍🏫 Teacher</SelectItem>
                <SelectItem value="CO_ADMIN">👨‍💼 Co-Admin</SelectItem>
                <SelectItem value="STUDENT">👨‍🎓 Student (use form below)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <form onSubmit={createCredential}>
            <div className="form_row">
              <Label className="form_label" style={{ color: '#374151' }}>Full Name</Label>
              <Input 
                value={tName} 
                onChange={(e) => setTName(e.target.value)} 
                className="form_input"
                placeholder="Enter full name"
                required 
              />
            </div>
            <div className="form_row">
              <Label className="form_label" style={{ color: '#374151' }}>Email Address</Label>
              <Input 
                type="email" 
                value={tEmail} 
                onChange={(e) => setTEmail(e.target.value)} 
                className="form_input"
                placeholder="email@example.com"
                required 
              />
            </div>
            <div className="form_row">
              <Label className="form_label" style={{ color: '#374151' }}>Phone Number</Label>
              <Input 
                value={tPhone} 
                onChange={(e) => setTPhone(e.target.value)} 
                className="form_input"
                placeholder="+91 98765 43210"
              />
            </div>
            {roleType === 'TEACHER' && (
              <>
                <div className="form_row">
                  <Label className="form_label" style={{ color: '#374151' }}>Teaching Subject</Label>
                  <Select value={subject} onValueChange={setSubject}>
                    <SelectTrigger><SelectValue placeholder="Select subject" /></SelectTrigger>
                    <SelectContent>
                      {['Math','Science','English','Social','Telugu','Hindi','Other'].map((s) => (
                        <SelectItem key={s} value={s}>{s}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="form_row">
                  <Label className="form_label" style={{ color: '#374151' }}>Assign Sections</Label>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm text-gray-700">
                      <input type="checkbox" onChange={(e)=> setTeacherSection(e.target.checked ? 'ALL' : '')} checked={teacherSection==='ALL'} />
                      All sections in school
                    </label>
                    <select className="select" multiple value={Array.isArray(teacherSection)? teacherSection : []} onChange={(e)=>{
                      const vals = Array.from(e.target.selectedOptions).map(o=>o.value);
                      setTeacherSection(vals);
                    }} disabled={teacherSection==='ALL'}>
                      {sections.map((s) => (<option key={s.id} value={s.id}>{s.name}{s.grade ? ` (Grade ${s.grade})` : ''}</option>))}
                    </select>
                    <div className="text-xs text-gray-500">Hold Ctrl/Command to select multiple.</div>
                  </div>
                </div>
              </>
            )}
            <Button className="btn_primary" type="submit">✨ Create Account</Button>
          </form>
        </div>
      );
    } else if (currentSection === 'school-stats') {
      return <AnalyticsSchool />;
    } else {
      return (
        <>
          <HeroSection 
            title={school ? `${school.name}` : "School Dashboard"}
            subtitle={`${me?.role.replace('_', ' ')} Portal • ${me?.full_name}`}
            backgroundImage="https://images.unsplash.com/photo-1580582932707-520aed937b7b"
          />
          <div className="grid" style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))', gap:'1rem'}}>
            <div onClick={()=>onSectionChange('school-stats')} style={{cursor:'pointer'}}>
              <StatsCard title="Analytics" value="View" />
            </div>
          </div>
          <div className="card wide animate-slide-in" style={{marginTop:'1rem'}}>
            <div style={{display:'flex', gap:'0.75rem', flexWrap:'wrap'}}>
              <Button className="btn_primary" onClick={()=>onSectionChange('sections')}>📚 Go to Sections</Button>
              <Button className="btn_primary" onClick={()=>onSectionChange('students')}>👨‍🎓 Go to Students</Button>
              <Button className="btn_primary" onClick={()=>onSectionChange('teachers')}>👨‍🏫 Go to Teachers</Button>
              <Button className="btn_secondary" onClick={()=>onSectionChange('enrollment')}>🎭 Face Enrollment</Button>
            </div>
          </div>
        </>
      );
    }
  };

  return (
    <div className="dash_grid">
      {renderContent()}
    </div>
  );
}

function TeacherView({ me, currentSection, onSectionChange }) {
  const school = useMySchool(!!me);
  const renderContent = () => {
    if (currentSection === 'scan-attendance') {
      return <TeacherAttendanceFlow me={me} />;
    } else {
      return (
        <>
          <HeroSection 
            title={school ? `${school.name}` : "Teacher Dashboard"}
            subtitle={`Attendance Management Portal • ${me.full_name}`}
            backgroundImage="https://images.unsplash.com/photo-1677442135703-1787eea5ce01"
          />
          <TeacherAttendanceFlow me={me} />
        </>
      );
    }
  };
  return (
    <div className="dash_grid">
      {renderContent()}
    </div>
  );
}

function App() {
  const { token, setToken, me } = useAuth();
  const [currentSection, setCurrentSection] = useState('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem('sidebar_collapsed') === 'true');

  const content = useMemo(() => {
    if (!token || !me) return <Login onLoggedIn={setToken} />;
    if (me.role === 'GOV_ADMIN') return <GovAdmin me={me} currentSection={currentSection} onSectionChange={setCurrentSection} />;
    if (me.role === 'SCHOOL_ADMIN' || me.role === 'CO_ADMIN') return <SchoolAdminLike me={me} currentSection={currentSection} onSectionChange={setCurrentSection} />;
    return <TeacherView me={me} currentSection={currentSection} onSectionChange={setCurrentSection} />;
  }, [token, me, currentSection]);

  const showSidebar = token && me;

  return (
    <div>
      <header className="topbar">
        <div className="brand">SmartAttend AI</div>
        {me && (
          <div className="user_box">
            <div className="user_info">
              <div className="user_email" style={{ color: '#374151' }}>{me.email}</div>
              <div className="user_role" style={{ color: '#1e40af', backgroundColor: '#eff6ff' }}>{me.role.replace('_', ' ')}</div>
            </div>
            <Button className="btn_secondary" onClick={() => setToken("")}> 
              🚪 Logout
            </Button>
          </div>
        )}
      </header>
      <div style={{ display: 'flex', minHeight: 'calc(100vh - 70px)' }}>
        {showSidebar && (
          <Sidebar 
            me={me} 
            currentSection={currentSection} 
            onSectionChange={setCurrentSection}
            onToggle={(collapsed) => setSidebarCollapsed(collapsed)}
          />
        )}
        <main style={{ 
          flex: 1, 
          marginLeft: showSidebar ? (sidebarCollapsed ? '0' : '288px') : '0',
          transition: 'margin-left 0.3s ease',
          minHeight: 'calc(100vh - 70px)'
        }}>
          {content}
        </main>
      </div>
    </div>
  );
}

export default App;