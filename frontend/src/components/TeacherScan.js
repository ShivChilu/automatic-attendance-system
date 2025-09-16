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
  const [scanHistory, setScanHistory] = useState([]);
  const [isScanning, setIsScanning] = useState(false);

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
    if (!section) { 
      setStatus("⚠️ Please select a section first"); 
      return; 
    }
    
    setIsScanning(true);
    setStatus("🔍 Analyzing face...");
    
    try {
      const fd = new FormData();
      fd.append("image", blob, "scan.jpg");
      if (section?.id) fd.append("section_id", section.id);
      
      const res = await api.post("/attendance/mark", fd, { 
        headers: { "Content-Type": "multipart/form-data" } 
      });
      
      const result = res.data.status || "";
      setStatus(result);
      
      // Add to scan history
      const timestamp = new Date().toLocaleTimeString();
      setScanHistory(prev => [
        { timestamp, result, success: result.includes('marked') },
        ...prev.slice(0, 9) // Keep last 10 scans
      ]);
      
      await loadSummary(section.id);
    } catch (err) {
      const errorMsg = err?.response?.data?.detail || "Scan failed";
      setStatus(`❌ ${errorMsg}`);
      
      // Add error to history
      const timestamp = new Date().toLocaleTimeString();
      setScanHistory(prev => [
        { timestamp, result: errorMsg, success: false },
        ...prev.slice(0, 9)
      ]);
    } finally {
      setIsScanning(false);
    }
  };

  const addSampleAndScan = async () => {
    try {
      setStatus("📥 Loading sample image...");
      const resp = await fetch(sampleUrl);
      const blob = await resp.blob();
      await onCapture(blob);
    } catch (e) {
      setStatus("❌ Failed to load sample image URL");
    }
  };

  const loadSummary = async (sectionId) => {
    try {
      const today = new Date().toISOString().slice(0,10);
      const res = await api.get("/attendance/summary", { 
        params: { section_id: sectionId, date: today } 
      });
      setSummary(res.data);
    } catch (e) {
      // ignore for now
    }
  };

  useEffect(() => {
    if (section) loadSummary(section.id);
  }, [section]);

  const attendancePercentage = summary ? Math.round((summary.present_count / summary.total) * 100) : 0;

  return (
    <div className="card wide animate-slide-in" style={{ 
      background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%)',
      border: '2px solid rgba(16, 185, 129, 0.2)'
    }}>
      <h3 className="card_title" style={{ color: '#047857', marginBottom: '1.5rem' }}>
        📸 Smart Attendance Scanner
      </h3>
      
      <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white font-bold text-sm">AI</div>
          <h4 className="font-semibold text-green-800">Real-time Face Recognition</h4>
        </div>
        <p className="text-green-700 text-sm">
          Point the camera at a student's face to instantly mark their attendance. 
          Our AI system will match faces with enrolled students in your section.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scanner Section */}
        <div className="lg:col-span-2">
          <div className="form_row">
            <Label className="form_label">📚 Select Section to Scan</Label>
            <select 
              className="select" 
              value={section?.id || ''} 
              onChange={(e) => {
                const s = sections.find((x) => x.id === e.target.value);
                setSection(s || null);
              }}
              style={{ 
                border: '2px solid #d1fae5',
                borderRadius: '12px',
                padding: '12px',
                background: 'white'
              }}
            >
              <option value="">Choose section to scan</option>
              {sections.map((s) => (
                <option key={s.id} value={s.id}>{s.name}{s.grade ? ` (Grade ${s.grade})` : ''}</option>
              ))}
            </select>
          </div>

          <div className="bg-gradient-to-br from-green-50 to-blue-50 border-2 border-green-200 rounded-xl p-6 mt-4">
            <CameraCapture 
              facingMode={facingMode} 
              onToggleFacing={()=>setFacingMode(facingMode === 'user' ? 'environment' : 'user')} 
              onCapture={(blob)=>onCapture(blob)} 
              captureLabel={isScanning ? "🔍 Scanning..." : "📸 Scan Student Face"} 
            />
            
            <div className="mt-4 p-4 bg-white bg-opacity-70 rounded-lg">
              <div className="flex gap-3 items-center">
                <input 
                  className="form_input flex-1" 
                  value={sampleUrl} 
                  onChange={(e)=>setSampleUrl(e.target.value)} 
                  placeholder="Or use sample image URL for testing"
                  style={{ fontSize: '14px' }}
                />
                <Button 
                  type="button" 
                  className="btn_secondary" 
                  onClick={addSampleAndScan}
                  disabled={isScanning}
                >
                  🖼️ Test Sample
                </Button>
              </div>
            </div>
          </div>

          {status && (
            <div className={`mt-4 p-4 rounded-xl border-2 animate-fade-in ${
              status.includes('✅') || status.includes('marked') 
                ? 'bg-green-50 border-green-200 text-green-800' 
                : status.includes('❌') || status.includes('failed')
                ? 'bg-red-50 border-red-200 text-red-800'
                : 'bg-blue-50 border-blue-200 text-blue-800'
            }`}>
              <div className="font-semibold text-center">{status}</div>
            </div>
          )}
        </div>

        {/* Stats & History Sidebar */}
        <div className="space-y-6">
          {/* Today's Stats */}
          {summary && (
            <div className="bg-white rounded-xl border-2 border-gray-200 p-4">
              <h4 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                📊 Today's Attendance
              </h4>
              <div className="text-center mb-4">
                <div className="text-3xl font-bold text-green-600 mb-1">
                  {attendancePercentage}%
                </div>
                <div className="text-sm text-gray-600">
                  {summary.present_count} of {summary.total} present
                </div>
              </div>
              
              <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
                <div 
                  className="bg-gradient-to-r from-green-400 to-green-600 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${attendancePercentage}%` }}
                ></div>
              </div>
            </div>
          )}

          {/* Scan History */}
          {scanHistory.length > 0 && (
            <div className="bg-white rounded-xl border-2 border-gray-200 p-4">
              <h4 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                🕒 Recent Scans
              </h4>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {scanHistory.map((scan, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-xs p-2 rounded bg-gray-50">
                    <span className={scan.success ? 'text-green-600' : 'text-red-600'}>
                      {scan.success ? '✅' : '❌'}
                    </span>
                    <span className="text-gray-500">{scan.timestamp}</span>
                    <span className="flex-1 truncate">{scan.result}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Detailed Attendance Table */}
      {summary && (
        <div className="mt-8">
          <h4 className="text-lg font-semibold mb-4 text-gray-700 flex items-center gap-2">
            👥 Student Attendance Details
          </h4>
          <div className="table_wrap">
            <table>
              <thead>
                <tr>
                  <th>Student Name</th>
                  <th>Status</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {summary.items.map((it) => (
                  <tr key={it.student_id}>
                    <td>
                      <span className="font-semibold text-gray-800">{it.name}</span>
                    </td>
                    <td>
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        it.present 
                          ? 'bg-green-100 text-green-800 border border-green-200' 
                          : 'bg-gray-100 text-gray-600 border border-gray-200'
                      }`}>
                        {it.present ? '✅ Present' : '⭕ Absent'}
                      </span>
                    </td>
                    <td>
                      <span className="text-sm text-gray-500">
                        {it.present ? (it.marked_at || 'Today') : '-'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="mt-4 p-4 bg-gray-50 rounded-lg text-center">
            <div className="text-sm text-gray-600">
              📈 <strong>Attendance Summary:</strong> {summary.present_count} students present out of {summary.total} total
              {attendancePercentage >= 90 && <span className="text-green-600 ml-2">🎉 Excellent attendance!</span>}
              {attendancePercentage >= 75 && attendancePercentage < 90 && <span className="text-blue-600 ml-2">👍 Good attendance</span>}
              {attendancePercentage < 75 && <span className="text-orange-600 ml-2">⚠️ Low attendance</span>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}