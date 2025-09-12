import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import "./App.css";
// shadcn ui components
import { Button } from "./src/components/ui/button";
import { Card } from "./src/components/ui/card";
import { Input } from "./src/components/ui/input";
import { Label } from "./src/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./src/components/ui/tabs";

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
        <p className="note">Tip: We'll seed your accounts automatically. Use the credentials sent to your email.</p>
      </div>
    </div>
  );
}

function GovAdmin({ me }) {
  const [schoolName, setSchoolName] = useState("");
  const [message, setMessage] = useState("");

  const createSchool = async (e) => {
    e.preventDefault();
    setMessage("");
    try {
      const res = await api.post("/schools", { name: schoolName });
      setMessage(`Created school: ${res.data.name}`);
      setSchoolName("");
    } catch (err) {
      setMessage(err?.response?.data?.detail || "Failed to create school");
    }
  };

  return (
    <div className="dash_grid">
      <Card className="card">
        <h3>Create School</h3>
        <form onSubmit={createSchool}>
          <div className="form_row"><Label>School name</Label><Input value={schoolName} onChange={(e) => setSchoolName(e.target.value)} required /></div>
          <Button type="submit" className="btn_primary">Create</Button>
        </form>
        {message && <div className="muted mt">{message}</div>}
      </Card>
    </div>
  );
}

function SchoolAdmin({ me }) {
  const [sections, setSections] = useState([]);
  const [students, setStudents] = useState([]);

  const [secName, setSecName] = useState("");
  const [secGrade, setSecGrade] = useState("");
  const [stuName, setStuName] = useState("");
  const [stuCode, setStuCode] = useState("");
  const [parentMobile, setParentMobile] = useState("");
  const [selectedSec, setSelectedSec] = useState("");

  const [tName, setTName] = useState("");
  const [tEmail, setTEmail] = useState("");
  const [tPhone, setTPhone] = useState("");

  const reload = async () => {
    const sec = await api.get("/sections");
    setSections(sec.data);
  };

  useEffect(() => { reload(); }, []);

  const addSection = async (e) => {
    e.preventDefault();
    await api.post("/sections", { school_id: me.school_id, name: secName, grade: secGrade || undefined });
    setSecName(""); setSecGrade(""); reload();
  };
  const addStudent = async (e) => {
    e.preventDefault();
    await api.post("/students", { name: stuName, student_code: stuCode, section_id: selectedSec, parent_mobile: parentMobile || undefined });
    setStuName(""); setStuCode(""); setParentMobile("");
    if (selectedSec) {
      const list = await api.get(`/students?section_id=${selectedSec}`);
      setStudents(list.data);
    }
  };
  const addTeacher = async (e) => {
    e.preventDefault();
    await api.post("/users/teachers", { full_name: tName, email: tEmail, role: "TEACHER", phone: tPhone });
    setTName(""); setTEmail(""); setTPhone("");
    alert("Teacher created. Credentials emailed (if Brevo configured).");
  };

  const loadStudents = async (secId) => {
    setSelectedSec(secId);
    if (!secId) { setStudents([]); return; }
    const list = await api.get(`/students?section_id=${secId}`);
    setStudents(list.data);
  };

  return (
    <div className="dash_grid">
      <Card className="card">
        <h3>Add Section</h3>
        <form onSubmit={addSection}>
          <div className="form_row"><Label>Name</Label><Input value={secName} onChange={(e) => setSecName(e.target.value)} required /></div>
          <div className="form_row"><Label>Grade</Label><Input value={secGrade} onChange={(e) => setSecGrade(e.target.value)} placeholder="e.g., 8" /></div>
          <Button className="btn_primary" type="submit">Add</Button>
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
          <div className="form_row"><Label>Student code</Label><Input value={stuCode} onChange={(e) => setStuCode(e.target.value)} required /></div>
          <div className="form_row"><Label>Parent mobile</Label><Input value={parentMobile} onChange={(e) => setParentMobile(e.target.value)} /></div>
          <Button className="btn_primary" type="submit">Add</Button>
        </form>
      </Card>

      <Card className="card">
        <h3>Add Teacher</h3>
        <form onSubmit={addTeacher}>
          <div className="form_row"><Label>Full name</Label><Input value={tName} onChange={(e) => setTName(e.target.value)} required /></div>
          <div className="form_row"><Label>Email</Label><Input type="email" value={tEmail} onChange={(e) => setTEmail(e.target.value)} required /></div>
          <div className="form_row"><Label>Phone</Label><Input value={tPhone} onChange={(e) => setTPhone(e.target.value)} /></div>
          <Button className="btn_primary" type="submit">Create</Button>
        </form>
      </Card>

      <Card className="card wide">
        <h3>Students in selected section</h3>
        {selectedSec ? (
          <div className="table_wrap">
            <table>
              <thead><tr><th>Name</th><th>Code</th><th>Parent</th></tr></thead>
              <tbody>
                {students.map((st) => (
                  <tr key={st.id}><td>{st.name}</td><td>{st.student_code}</td><td>{st.parent_mobile || '-'}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <div className="muted">Select a section to view students</div>}
      </Card>
    </div>
  );
}

function Teacher() {
  return (
    <div className="dash_grid">
      <Card className="card">
        <h3>Welcome</h3>
        <p className="muted">Your dashboard will show timetable and attendance actions in next phases.</p>
      </Card>
    </div>
  );
}

function App() {
  const { token, setToken, me } = useAuth();

  const content = useMemo(() => {
    if (!token || !me) return <Login onLoggedIn={setToken} />;
    if (me.role === 'GOV_ADMIN') return <GovAdmin me={me} />;
    if (me.role === 'SCHOOL_ADMIN') return <SchoolAdmin me={me} />;
    return <Teacher me={me} />;
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