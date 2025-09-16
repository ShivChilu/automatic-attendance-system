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

// Modern Statistics Card Component
function StatsCard({ title, value, icon, gradient, trend }) {
  return (
    <div className="card narrow animate-scale-in">
      <div className="stats_card" style={{ background: gradient }}>
        <div className="stats_number">{value}</div>
        <div className="stats_label">{title}</div>
        {trend && (
          <div className="text-xs text-gray-600 mt-2">
            {trend > 0 ? '↗️' : '↘️'} {Math.abs(trend)}% from last month
          </div>
        )}
      </div>
    </div>
  );
}

// Hero Section Component
function HeroSection({ title, subtitle, backgroundImage }) {
  return (
    <div className="card wide animate-fade-in" style={{ 
      backgroundImage: `linear-gradient(rgba(102, 126, 234, 0.8), rgba(118, 75, 162, 0.8)), url(${backgroundImage})`,
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      color: 'white',
      minHeight: '200px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      textAlign: 'center'
    }}>
      <h1 className="text-4xl font-extrabold mb-4">{title}</h1>
      <p className="text-xl font-medium opacity-90">{subtitle}</p>
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
            <Label htmlFor="email" className="form_label">Email Address</Label>
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
            <Label htmlFor="password" className="form_label">Password</Label>
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

function GovAdmin({ me }) {
  const [form, setForm] = useState({ name: "", address_line1: "", city: "", state: "", pincode: "", principal_name: "", principal_email: "", principal_phone: "" });
  const [message, setMessage] = useState("");
  const [schools, setSchools] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState({});
  const [stats, setStats] = useState({ totalSchools: 0, totalStudents: 0, totalTeachers: 0 });

  const loadSchools = async () => {
    const res = await api.get("/schools");
    setSchools(res.data);
    // Calculate stats
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

  return (
    <div className="dash_grid">
      <HeroSection 
        title="Government Education Dashboard"
        subtitle="Manage schools, monitor attendance, and oversee educational infrastructure"
        backgroundImage="https://images.unsplash.com/photo-1519389950473-47ba0277781c"
      />
      
      {/* Statistics Overview */}
      <StatsCard title="Total Schools" value={stats.totalSchools} gradient="linear-gradient(135deg, #667eea 0%, #764ba2 100%)" trend={8} />
      <StatsCard title="Total Students" value={stats.totalStudents.toLocaleString()} gradient="linear-gradient(135deg, #f093fb 0%, #f5576c 100%)" trend={12} />
      <StatsCard title="Total Teachers" value={stats.totalTeachers.toLocaleString()} gradient="linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)" trend={5} />

      <div className="card wide animate-slide-in">
        <h3 className="card_title">🏫 Create New School</h3>
        <form onSubmit={createSchool}>
          <div className="form_row">
            <Label className="form_label">School Name</Label>
            <Input 
              value={form.name} 
              onChange={(e) => setForm({ ...form, name: e.target.value })} 
              className="form_input"
              placeholder="Enter school name"
              required 
            />
          </div>
          <div className="form_row">
            <Label className="form_label">Address</Label>
            <Input 
              value={form.address_line1} 
              onChange={(e) => setForm({ ...form, address_line1: e.target.value })} 
              className="form_input"
              placeholder="Enter school address"
            />
          </div>
          <div className="form_row" style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '1rem' }}>
            <div>
              <Label className="form_label">City</Label>
              <Input 
                value={form.city} 
                onChange={(e) => setForm({ ...form, city: e.target.value })} 
                className="form_input"
                placeholder="City"
              />
            </div>
            <div>
              <Label className="form_label">State</Label>
              <Input 
                value={form.state} 
                onChange={(e) => setForm({ ...form, state: e.target.value })} 
                className="form_input"
                placeholder="State"
              />
            </div>
            <div>
              <Label className="form_label">Pincode</Label>
              <Input 
                value={form.pincode} 
                onChange={(e) => setForm({ ...form, pincode: e.target.value })} 
                className="form_input"
                placeholder="Pincode"
              />
            </div>
          </div>
          <div className="form_row">
            <Label className="form_label">Principal Name</Label>
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
              <Label className="form_label">Principal Email</Label>
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
              <Label className="form_label">Principal Phone</Label>
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

      <div className="card wide animate-slide-in">
        <h3 className="card_title">🏫 All Schools Management</h3>
        <div className="table_wrap">
          <table>
            <thead>
              <tr>
                <th>School Name</th>
                <th>City</th>
                <th>Principal</th>
                <th>Email</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {schools.map((s) => (
                <tr key={s.id}>
                  <td>
                    {editingId === s.id ? 
                      <Input value={editDraft.name} onChange={(e)=>setEditDraft({...editDraft, name: e.target.value})} className="form_input" /> 
                      : <span className="font-semibold text-gray-800">{s.name}</span>
                    }
                  </td>
                  <td>
                    {editingId === s.id ? 
                      <Input value={editDraft.city || ''} onChange={(e)=>setEditDraft({...editDraft, city: e.target.value})} className="form_input" /> 
                      : (s.city || <span className="text-gray-400">-</span>)
                    }
                  </td>
                  <td>
                    {editingId === s.id ? 
                      <Input value={editDraft.principal_name || ''} onChange={(e)=>setEditDraft({...editDraft, principal_name: e.target.value})} className="form_input" /> 
                      : (s.principal_name || <span className="text-gray-400">-</span>)
                    }
                  </td>
                  <td>
                    {editingId === s.id ? 
                      <Input value={editDraft.principal_email || ''} onChange={(e)=>setEditDraft({...editDraft, principal_email: e.target.value})} className="form_input" /> 
                      : (s.principal_email || <span className="text-gray-400">-</span>)
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
    if (!confirm("⚠️ Delete this section? All students in it will be removed.")) return;
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
    if (!confirm("⚠️ Delete this student?")) return;
    await api.delete(`/students/${id}`);
    if (selectedSec) { const list = await api.get(`/students?section_id=${selectedSec}`); setStudents(list.data); }
  };

  const createCredential = async (e) => {
    e.preventDefault();
    try {
      if (roleType === 'TEACHER') {
        await api.post("/users/teachers", { full_name: tName, email: tEmail, role: "TEACHER", phone: tPhone, subject, section_id: teacherSection || undefined });
        alert("✅ Teacher created successfully! Credentials have been emailed.");
      } else if (roleType === 'CO_ADMIN') {
        await api.post("/users/coadmins", { full_name: tName, email: tEmail, role: "CO_ADMIN", phone: tPhone });
        alert("✅ Co-Admin created successfully! Credentials have been emailed.");
      } else {
        alert("💡 Use the Add Student form for students.");
      }
      setTName(""); setTEmail(""); setTPhone(""); setSubject("Math"); setTeacherSection("");
      loadStaff();
    } catch (err) {
      alert(`❌ ${err?.response?.data?.detail || "Failed to create credentials"}`);
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
      <HeroSection 
        title={school ? `${school.name}` : "School Dashboard"}
        subtitle={`${me?.role.replace('_', ' ')} Portal • ${me?.full_name}`}
        backgroundImage="https://images.unsplash.com/photo-1580582932707-520aed937b7b"
      />

      {/* Quick Stats */}
      <StatsCard title="Sections" value={sections.length} gradient="linear-gradient(135deg, #667eea 0%, #764ba2 100%)" />
      <StatsCard title="Students" value={students.length} gradient="linear-gradient(135deg, #f093fb 0%, #f5576c 100%)" />
      <StatsCard title="Teachers" value={teachers.length} gradient="linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)" />

      <div className="card medium animate-slide-in">
        <h3 className="card_title">📚 Add Section</h3>
        <form onSubmit={addSection}>
          <div className="form_row">
            <Label className="form_label">Section Name</Label>
            <Input 
              value={secName} 
              onChange={(e) => setSecName(e.target.value)} 
              className="form_input"
              placeholder="e.g., 8-A, Grade 5"
              required 
            />
          </div>
          <div className="form_row">
            <Label className="form_label">Grade Level</Label>
            <Input 
              value={secGrade} 
              onChange={(e) => setSecGrade(e.target.value)} 
              className="form_input"
              placeholder="e.g., 8, 10, 12"
            />
          </div>
          <Button className="btn_primary" type="submit">➕ Add Section</Button>
        </form>

        {/* Section list with edit/delete */}
        {sections.length > 0 && (
          <div className="table_wrap" style={{marginTop: '1rem'}}>
            <table>
              <thead>
                <tr>
                  <th>Section Name</th>
                  <th>Grade</th>
                  {isSchoolAdmin && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {sections.map((s) => (
                  <tr key={s.id}>
                    <td>
                      {editingSection === s.id ? 
                        <Input value={sectionDraft.name} onChange={(e)=>setSectionDraft({...sectionDraft, name:e.target.value})} className="form_input" /> 
                        : <span className="font-semibold">{s.name}</span>
                      }
                    </td>
                    <td>
                      {editingSection === s.id ? 
                        <Input value={sectionDraft.grade || ''} onChange={(e)=>setSectionDraft({...sectionDraft, grade:e.target.value})} className="form_input" /> 
                        : (s.grade || <span className="text-gray-400">-</span>)
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

      <div className="card medium animate-slide-in">
        <h3 className="card_title">👥 Create Staff Credentials</h3>
        <div className="form_row">
          <Label className="form_label">Staff Role</Label>
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
            <Label className="form_label">Full Name</Label>
            <Input 
              value={tName} 
              onChange={(e) => setTName(e.target.value)} 
              className="form_input"
              placeholder="Enter full name"
              required 
            />
          </div>
          <div className="form_row">
            <Label className="form_label">Email Address</Label>
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
            <Label className="form_label">Phone Number</Label>
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
                <Label className="form_label">Teaching Subject</Label>
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
                <Label className="form_label">Assign to Section</Label>
                <select className="select" value={teacherSection} onChange={(e) => setTeacherSection(e.target.value)}>
                  <option value="">No specific section</option>
                  {sections.map((s) => (<option key={s.id} value={s.id}>{s.name} {s.grade ? `(Grade ${s.grade})` : ''}</option>))}
                </select>
              </div>
            </>
          )}
          <Button className="btn_primary" type="submit">✨ Create Account</Button>
        </form>
      </div>

      <div className="card medium animate-slide-in">
        <h3 className="card_title">🎓 Add Student</h3>
        <form onSubmit={addStudent}>
          <div className="form_row">
            <Label className="form_label">Select Section</Label>
            <select className="select" value={selectedSec} onChange={(e) => loadStudents(e.target.value)} required>
              <option value="">Choose section</option>
              {sections.map((s) => (<option key={s.id} value={s.id}>{s.name} {s.grade ? `(Grade ${s.grade})` : ""}</option>))}
            </select>
          </div>
          <div className="form_row">
            <Label className="form_label">Student Name</Label>
            <Input 
              value={stuName} 
              onChange={(e) => setStuName(e.target.value)} 
              className="form_input"
              placeholder="Enter student's full name"
              required 
            />
          </div>
          <div className="form_row">
            <Label className="form_label">Roll Number</Label>
            <Input 
              value={rollNo} 
              onChange={(e) => setRollNo(e.target.value)} 
              className="form_input"
              placeholder="e.g., 001, A-23"
              required 
            />
          </div>
          <div className="form_row">
            <Label className="form_label">Parent's Mobile</Label>
            <Input 
              value={parentMobile} 
              onChange={(e) => setParentMobile(e.target.value)} 
              className="form_input"
              placeholder="+91 98765 43210"
            />
          </div>
          <Button className="btn_primary" type="submit">➕ Add Student</Button>
        </form>
      </div>

      <EnrollmentWithFace sections={sections} />

      <div className="card wide animate-slide-in">
        <h3 className="card_title">👨‍🎓 Students in Selected Section</h3>
        {selectedSec ? (
          <div className="table_wrap">
            <table>
              <thead>
                <tr>
                  <th>Student Name</th>
                  <th>Roll No.</th>
                  <th>Student Code</th>
                  <th>Parent Mobile</th>
                  {isSchoolAdmin && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {students.map((st) => (
                  <tr key={st.id}>
                    <td><span className="font-semibold text-gray-800">{st.name}</span></td>
                    <td><span className="font-medium text-primary">{st.roll_no || '-'}</span></td>
                    <td><code className="bg-gray-100 px-2 py-1 rounded text-xs">{st.student_code}</code></td>
                    <td>{st.parent_mobile || <span className="text-gray-400">-</span>}</td>
                    {isSchoolAdmin && (
                      <td style={{display:'flex',gap:'0.5rem'}}>
                        <Button className="btn_secondary" onClick={() => {
                          const newName = prompt('Update name:', st.name) || st.name;
                          const newRoll = prompt('Update roll number:', st.roll_no || '') || st.roll_no;
                          const newParent = prompt('Update parent mobile:', st.parent_mobile || '') || st.parent_mobile;
                          editStudent(st, { name: newName, roll_no: newRoll, parent_mobile: newParent });
                        }}>✏️ Edit</Button>
                        <Button className="btn_danger" onClick={() => deleteStudent(st.id)}>🗑️ Delete</Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-4">📚</div>
            <p>Select a section above to view students</p>
          </div>
        )}
      </div>

      <div className="card wide animate-slide-in">
        <h3 className="card_title">👨‍🏫 Staff Management</h3>
        
        <h4 className="text-lg font-semibold mb-4 text-gray-700">Teachers</h4>
        <div className="table_wrap" style={{marginBottom: '2rem'}}>
          <table>
            <thead>
              <tr>
                <th>Teacher Name</th>
                <th>Email</th>
                <th>Subject</th>
                <th>Assigned Section</th>
                {isSchoolAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {teachers.map((t) => (
                <tr key={t.id}>
                  <td><span className="font-semibold text-gray-800">{t.full_name}</span></td>
                  <td>{t.email}</td>
                  <td><span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium">{t.subject || '-'}</span></td>
                  <td>{(sections.find(s => s.id === t.section_id)?.name) || <span className="text-gray-400">-</span>}</td>
                  {isSchoolAdmin && (
                    <td style={{display:'flex',gap:'0.5rem'}}>
                      <Button className="btn_secondary" onClick={async ()=>{
                        const newName = prompt('Name:', t.full_name) || t.full_name;
                        const newPhone = prompt('Phone:', t.phone || '') || t.phone;
                        const newSubject = prompt('Subject (Math/Science/English/Social/Telugu/Hindi/Other):', t.subject || '');
                        try { await api.put(`/users/${t.id}`, { full_name: newName, phone: newPhone, subject: newSubject || undefined }); loadStaff(); } catch(err){ alert(err?.response?.data?.detail || 'Update failed'); }
                      }}>✏️ Edit</Button>
                      <Button className="btn_danger" onClick={async ()=>{ if(confirm('⚠️ Delete this teacher?')) { await api.delete(`/users/${t.id}`); loadStaff(); } }}>🗑️ Delete</Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h4 className="text-lg font-semibold mb-4 text-gray-700">Co-Administrators</h4>
        <div className="table_wrap">
          <table>
            <thead>
              <tr>
                <th>Co-Admin Name</th>
                <th>Email</th>
                <th>Phone</th>
                {isSchoolAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {coadmins.map((c) => (
                <tr key={c.id}>
                  <td><span className="font-semibold text-gray-800">{c.full_name}</span></td>
                  <td>{c.email}</td>
                  <td>{c.phone || <span className="text-gray-400">-</span>}</td>
                  {isSchoolAdmin && (
                    <td style={{display:'flex',gap:'0.5rem'}}>
                      <Button className="btn_secondary" onClick={async ()=>{
                        const newName = prompt('Name:', c.full_name) || c.full_name;
                        const newPhone = prompt('Phone:', c.phone || '') || c.phone;
                        try { await api.put(`/users/${c.id}`, { full_name: newName, phone: newPhone }); loadStaff(); } catch(err){ alert(err?.response?.data?.detail || 'Update failed'); }
                      }}>✏️ Edit</Button>
                      <Button className="btn_danger" onClick={async ()=>{ if(confirm('⚠️ Delete this co-admin?')) { await api.delete(`/users/${c.id}`); loadStaff(); } }}>🗑️ Delete</Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function TeacherView({ me }) {
  const school = useMySchool(!!me);
  return (
    <div className="dash_grid">
      <HeroSection 
        title={school ? `${school.name}` : "Teacher Dashboard"}
        subtitle={`Attendance Management Portal • ${me.full_name}`}
        backgroundImage="https://images.unsplash.com/photo-1677442135703-1787eea5ce01"
      />
      <TeacherScan me={me} />
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
        <div className="brand">SmartAttend AI</div>
        {me && (
          <div className="user_box">
            <div className="user_info">
              <div className="user_email">{me.email}</div>
              <div className="user_role">{me.role.replace('_', ' ')}</div>
            </div>
            <Button className="btn_secondary" onClick={() => setToken("")}>
              🚪 Logout
            </Button>
          </div>
        )}
      </header>
      {content}
    </div>
  );
}

export default App;