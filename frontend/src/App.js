import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import "./App.css";
// shadcn ui components
import { Button } from "./components/ui/button";
import { Card } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";

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
      <div className="auth_box">
        <h2 className="heading">Sign in</h2>
        <form onSubmit={submit}>
          <div className="form_row">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="form_row">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {error && <div className="error_text">{error}</div>}
          <Button disabled={loading} className="btn_primary" type="submit">{loading ? "Signing in..." : "Sign in"}</Button>
        </form>
        <p className="note">Tip: Your credentials are emailed when your account is created.</p>
      </div>
    </div>
  );
}

function GovAdmin({ me }) {
  const [form, setForm] = useState({ name: "", address_line1: "", city: "", state: "", pincode: "", principal_name: "", principal_email: "", principal_phone: "" });
  const [message, setMessage] = useState("");
  const [schools, setSchools] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState({});

  const loadSchools = async () => {
    const res = await api.get("/schools");
    setSchools(res.data);
  };
  useEffect(() => { loadSchools(); }, []);

  const createSchool = async (e) => {
    e.preventDefault();
    setMessage("");
    try {
      const res = await api.post("/schools", form);
      setMessage(`Created school: ${res.data.name}`);
      setForm({ name: "", address_line1: "", city: "", state: "", pincode: "", principal_name: "", principal_email: "", principal_phone: "" });
      loadSchools();
    } catch (err) {
      setMessage(err?.response?.data?.detail || "Failed to create school");
    }
  };

  const resend = async (email) => {
    try { await api.post("/users/resend-credentials", { email }); alert("Credentials resent"); } catch (e) { alert("Failed to resend"); }
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
    if (!confirm("Are you sure you want to delete this school? All its sections, students, and users will be removed.")) return;
    await api.delete(`/schools/${id}`); loadSchools();
  };

  return (
    <div className="dash_grid">
      <Card className="card wide">
        <h3>Create School</h3>
        <form onSubmit={createSchool}>
          <div className="form_row"><Label>School name</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div>
          <div className="form_row"><Label>Address</Label><Input value={form.address_line1} onChange={(e) => setForm({ ...form, address_line1: e.target.value })} /></div>
          <div className="form_row" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
            <div><Label>City</Label><Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
            <div><Label>State</Label><Input value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} /></div>
            <div><Label>Pincode</Label><Input value={form.pincode} onChange={(e) => setForm({ ...form, pincode: e.target.value })} /></div>
          </div>
          <div className="form_row"><Label>Principal name</Label><Input value={form.principal_name} onChange={(e) => setForm({ ...form, principal_name: e.target.value })} required /></div>
          <div className="form_row" style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 8 }}>
            <div><Label>Principal email</Label><Input type="email" value={form.principal_email} onChange={(e) => setForm({ ...form, principal_email: e.target.value })} required /></div>
            <div><Label>Principal phone</Label><Input value={form.principal_phone} onChange={(e) => setForm({ ...form, principal_phone: e.target.value })} /></div>
          </div>
          <Button type="submit" className="btn_primary">Create</Button>
        </form>
        {message && <div className="muted mt">{message}</div>}
      </Card>

      <Card className="card wide">
        <h3>All Schools</h3>
        <div className="table_wrap">
          <table>
            <thead><tr><th>Name</th><th>City</th><th>Principal</th><th>Email</th><th>Actions</th></tr></thead>
            <tbody>
              {schools.map((s) => (
                <tr key={s.id}>
                  <td>{editingId === s.id ? <Input value={editDraft.name} onChange={(e)=>setEditDraft({...editDraft, name: e.target.value})} /> : s.name}</td>
                  <td>{editingId === s.id ? <Input value={editDraft.city || ''} onChange={(e)=>setEditDraft({...editDraft, city: e.target.value})} /> : (s.city || '-')}</td>
                  <td>{editingId === s.id ? <Input value={editDraft.principal_name || ''} onChange={(e)=>setEditDraft({...editDraft, principal_name: e.target.value})} /> : (s.principal_name || '-')}</td>
                  <td>{editingId === s.id ? <Input value={editDraft.principal_email || ''} onChange={(e)=>setEditDraft({...editDraft, principal_email: e.target.value})} /> : (s.principal_email || '-')}</td>
                  <td style={{display:'flex',gap:8}}>
                    <Button className="btn_secondary" onClick={() => resend(s.principal_email)} disabled={!s.principal_email}>Resend</Button>
                    {editingId === s.id ? (
                      <>
                        <Button className="btn_primary" onClick={saveEdit}>Save</Button>
                        <Button className="btn_secondary" onClick={cancelEdit}>Cancel</Button>
                      </>
                    ) : (
                      <>
                        <Button className="btn_secondary" onClick={() => startEdit(s)}>Edit</Button>
                        <Button className="btn_secondary" onClick={() => removeSchool(s.id)}>Delete</Button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function SchoolAdminLike({ me }) {
  const school = useMySchool(!!me);
  const [sections, setSections] = useState([]);
  const [students, setStudents] = useState([]);

  // Add Section
  const [secName, setSecName] = useState("");
  const [secGrade, setSecGrade] = useState("");

  // Section manage edit
  const [editingSection, setEditingSection] = useState(null);
  const [sectionDraft, setSectionDraft] = useState({});

  // Student
  const [stuName, setStuName] = useState("");
  const [rollNo, setRollNo] = useState("");
  const [parentMobile, setParentMobile] = useState("");
  const [selectedSec, setSelectedSec] = useState("");

  // Create Credentials
  const [roleType, setRoleType] = useState("TEACHER");
  const [tName, setTName] = useState("");
  const [tEmail, setTEmail] = useState("");
  const [tPhone, setTPhone] = useState("");
  const [subject, setSubject] = useState("Math");
  const [teacherSection, setTeacherSection] = useState("");

  // Staff tables
  const [teachers, setTeachers] = useState([]);
  const [coadmins, setCoadmins] = useState([]);

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
    if (!confirm("Delete this section? All students in it will be removed.")) return;
    await api.delete(`/sections/${id}`); if (selectedSec === id) setSelectedSec(""); loadSections(); setStudents([]);
  };

  const addStudent = async (e) => {
    e.preventDefault();
    await api.post("/students", { name: stuName, roll_no: rollNo, section_id: selectedSec, parent_mobile: parentMobile || undefined });
    setStuName(""); setRollNo(""); setParentMobile("");
    if (selectedSec) { const list = await api.get(`/students?section_id=${selectedSec}`); setStudents(list.data); }
  };
  const editStudent = async (st, updates) => {
    await api.put(`/students/${st.id}`, updates);
    if (selectedSec) { const list = await api.get(`/students?section_id=${selectedSec}`); setStudents(list.data); }
  };
  const deleteStudent = async (id) => {
    if (!confirm("Delete this student?")) return;
    await api.delete(`/students/${id}`);
    if (selectedSec) { const list = await api.get(`/students?section_id=${selectedSec}`); setStudents(list.data); }
  };

  const createCredential = async (e) => {
    e.preventDefault();
    try {
      if (roleType === 'TEACHER') {
        await api.post("/users/teachers", { full_name: tName, email: tEmail, role: "TEACHER", phone: tPhone, subject, section_id: teacherSection || undefined });
        alert("Teacher created. Credentials emailed.");
      } else if (roleType === 'CO_ADMIN') {
        await api.post("/users/coadmins", { full_name: tName, email: tEmail, role: "CO_ADMIN", phone: tPhone });
        alert("Co-Admin created. Credentials emailed.");
      } else {
        alert("Use Add Student form for students.");
      }
      setTName(""); setTEmail(""); setTPhone(""); setSubject("Math"); setTeacherSection("");
      loadStaff();
    } catch (err) {
      alert(err?.response?.data?.detail || "Failed to create credentials");
    }
  };

  const loadStudents = async (secId) => {
    setSelectedSec(secId);
    if (!secId) { setStudents([]); return; }
    const list = await api.get(`/students?section_id=${secId}`);
    setStudents(list.data);
  };

  const isSchoolAdmin = me?.role === 'SCHOOL_ADMIN';

  return (
    <div className="dash_grid">
      <Card className="card wide">
        <h3>{school ? `${school.name}` : "My School"} {me ? `• ${me.full_name}` : ""}</h3>
      </Card>

      <Card className="card">
        <h3>Add Section</h3>
        <form onSubmit={addSection}>
          <div className="form_row"><Label>Name</Label><Input value={secName} onChange={(e) => setSecName(e.target.value)} required /></div>
          <div className="form_row"><Label>Grade</Label><Input value={secGrade} onChange={(e) => setSecGrade(e.target.value)} placeholder="e.g., 8" /></div>
          <Button className="btn_primary" type="submit">Add</Button>
        </form>

        {/* Section list with edit/delete (hidden for CO_ADMIN) */}
        {sections.length > 0 && (
          <div className="table_wrap" style={{marginTop:12}}>
            <table>
              <thead><tr><th>Name</th><th>Grade</th>{isSchoolAdmin && <th>Actions</th>}</tr></thead>
              <tbody>
                {sections.map((s) => (
                  <tr key={s.id}>
                    <td>{editingSection === s.id ? <Input value={sectionDraft.name} onChange={(e)=>setSectionDraft({...sectionDraft, name:e.target.value})}/> : s.name}</td>
                    <td>{editingSection === s.id ? <Input value={sectionDraft.grade || ''} onChange={(e)=>setSectionDraft({...sectionDraft, grade:e.target.value})}/> : (s.grade || '-')}</td>
                    {isSchoolAdmin && (
                      <td style={{display:'flex',gap:8}}>
                        {editingSection === s.id ? (
                          <>
                            <Button className="btn_primary" onClick={saveSection}>Save</Button>
                            <Button className="btn_secondary" onClick={()=>{setEditingSection(null); setSectionDraft({});}}>Cancel</Button>
                          </>
                        ) : (
                          <>
                            <Button className="btn_secondary" onClick={()=>editSection(s)}>Edit</Button>
                            <Button className="btn_secondary" onClick={()=>deleteSection(s.id)}>Delete</Button>
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
      </Card>

      <Card className="card">
        <h3>Create Credentials</h3>
        <div className="form_row">
          <Label>Role</Label>
          <Select value={roleType} onValueChange={setRoleType}>
            <SelectTrigger><SelectValue placeholder="Select role" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="TEACHER">Teacher</SelectItem>
              <SelectItem value="CO_ADMIN">Co-Admin</SelectItem>
              <SelectItem value="STUDENT">Student (use below form)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <form onSubmit={createCredential}>
          <div className="form_row"><Label>Full name</Label><Input value={tName} onChange={(e) => setTName(e.target.value)} required /></div>
          <div className="form_row"><Label>Email</Label><Input type="email" value={tEmail} onChange={(e) => setTEmail(e.target.value)} required /></div>
          <div className="form_row"><Label>Phone</Label><Input value={tPhone} onChange={(e) => setTPhone(e.target.value)} /></div>
          {roleType === 'TEACHER' && (
            <>
              <div className="form_row">
                <Label>Subject</Label>
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
                <Label>Assign Section</Label>
                <select className="select" value={teacherSection} onChange={(e) => setTeacherSection(e.target.value)}>
                  <option value="">None</option>
                  {sections.map((s) => (<option key={s.id} value={s.id}>{s.name} {s.grade ? `(Grade ${s.grade})` : ''}</option>))}
                </select>
              </div>
            </>
          )}
          <Button className="btn_primary" type="submit">Create</Button>
        </form>
      </Card>

      <Card className="card">
        <h3>Add Student</h3>
        <form onSubmit={addStudent}>
          <div className="form_row"><Label>Section</Label>
            <select className="select" value={selectedSec} onChange={(e) => loadStudents(e.target.value)} required>
              <option value="">Select section</option>
              {sections.map((s) => (<option key={s.id} value={s.id}>{s.name} {s.grade ? `(Grade ${s.grade})` : ""}</option>))}
            </select>
          </div>
          <div className="form_row"><Label>Student name</Label><Input value={stuName} onChange={(e) => setStuName(e.target.value)} required /></div>
          <div className="form_row"><Label>Roll No</Label><Input value={rollNo} onChange={(e) => setRollNo(e.target.value)} required /></div>
          <div className="form_row"><Label>Parent mobile</Label><Input value={parentMobile} onChange={(e) => setParentMobile(e.target.value)} /></div>
          <Button className="btn_primary" type="submit">Add</Button>
        </form>
      </Card>

      <Card className="card wide">
        <h3>Students in selected section</h3>
        {selectedSec ? (
          <div className="table_wrap">
            <table>
              <thead><tr><th>Name</th><th>Roll</th><th>Code</th><th>Parent</th>{isSchoolAdmin && <th>Actions</th>}</tr></thead>
              <tbody>
                {students.map((st) => (
                  <tr key={st.id}>
                    <td>{st.name}</td>
                    <td>{st.roll_no || '-'}</td>
                    <td>{st.student_code}</td>
                    <td>{st.parent_mobile || '-'}</td>
                    {isSchoolAdmin && (
                      <td style={{display:'flex',gap:8}}>
                        <Button className="btn_secondary" onClick={() => {
                          const newName = prompt('Update name', st.name) || st.name;
                          const newRoll = prompt('Update roll', st.roll_no || '') || st.roll_no;
                          const newParent = prompt('Update parent mobile', st.parent_mobile || '') || st.parent_mobile;
                          editStudent(st, { name: newName, roll_no: newRoll, parent_mobile: newParent });
                        }}>Edit</Button>
                        <Button className="btn_secondary" onClick={() => deleteStudent(st.id)}>Delete</Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <div className="muted">Select a section to view students</div>}
      </Card>

      <Card className="card wide">
        <h3>Manage Staff</h3>
        <div className="table_wrap" style={{marginBottom:12}}>
          <table>
            <thead><tr><th>Teacher</th><th>Email</th><th>Subject</th><th>Section</th>{isSchoolAdmin && <th>Actions</th>}</tr></thead>
            <tbody>
              {teachers.map((t) => (
                <tr key={t.id}>
                  <td>{t.full_name}</td>
                  <td>{t.email}</td>
                  <td>{t.subject || '-'}</td>
                  <td>{(sections.find(s => s.id === t.section_id)?.name) || '-'}</td>
                  {isSchoolAdmin && (
                    <td style={{display:'flex',gap:8}}>
                      <Button className="btn_secondary" onClick={async ()=>{
                        const newName = prompt('Name', t.full_name) || t.full_name;
                        const newPhone = prompt('Phone', t.phone || '') || t.phone;
                        const newSubject = prompt('Subject (Math/Science/English/Social/Telugu/Hindi/Other)', t.subject || '');
                        try { await api.put(`/users/${t.id}`, { full_name: newName, phone: newPhone, subject: newSubject || undefined }); loadStaff(); } catch(err){ alert(err?.response?.data?.detail || 'Update failed'); }
                      }}>Edit</Button>
                      <Button className="btn_secondary" onClick={async ()=>{ if(confirm('Delete this teacher?')) { await api.delete(`/users/${t.id}`); loadStaff(); } }}>Delete</Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="table_wrap">
          <table>
            <thead><tr><th>Co-Admin</th><th>Email</th><th>Phone</th>{isSchoolAdmin && <th>Actions</th>}</tr></thead>
            <tbody>
              {coadmins.map((c) => (
                <tr key={c.id}>
                  <td>{c.full_name}</td>
                  <td>{c.email}</td>
                  <td>{c.phone || '-'}</td>
                  {isSchoolAdmin && (
                    <td style={{display:'flex',gap:8}}>
                      <Button className="btn_secondary" onClick={async ()=>{
                        const newName = prompt('Name', c.full_name) || c.full_name;
                        const newPhone = prompt('Phone', c.phone || '') || c.phone;
                        try { await api.put(`/users/${c.id}`, { full_name: newName, phone: newPhone }); loadStaff(); } catch(err){ alert(err?.response?.data?.detail || 'Update failed'); }
                      }}>Edit</Button>
                      <Button className="btn_secondary" onClick={async ()=>{ if(confirm('Delete this co-admin?')) { await api.delete(`/users/${c.id}`); loadStaff(); } }}>Delete</Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function TeacherView({ me }) {
  const school = useMySchool(!!me);
  const [section, setSection] = useState(null);
  useEffect(() => {
    if (me?.section_id) {
      api.get("/sections").then((res) => {
        const s = res.data.find((x) => x.id === me.section_id);
        setSection(s || null);
      });
    }
  }, [me]);
  return (
    <div className="dash_grid">
      <Card className="card wide">
        <h3>{school ? school.name : "My School"} • {me.full_name} {section ? `• ${section.name}${section.grade ? ` (Grade ${section.grade})` : ''}` : ''}</h3>
        <p className="muted">Attendance marking and history will appear here in Phase 2.</p>
      </Card>
    </div>
  );
}

function App() {
  const { token, setToken, me } = useAuth();

  const content = useMemo(() => {
    if (!token || !me) return <Login onLoggedIn={setToken} />;
    if (me.role === 'GOV_ADMIN') return <GovAdmin me={me} />;
    if (me.role === 'SCHOOL_ADMIN' || me.role === 'CO_ADMIN') return <SchoolAdminLike me={me} />;
    return <TeacherView me={me} />;
  }, [token, me]);

  return (
    <div>
      <header className="topbar">
        <div className="brand">Automated Attendance</div>
        {me && (
          <div className="user_box">
            <span className="muted small">{me.email} • {me.role}</span>
            <Button className="btn_secondary" onClick={() => setToken("")}>Logout</Button>
          </div>
        )}
      </header>
      {content}
    </div>
  );
}

export default App;