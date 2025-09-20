import React, { useEffect, useMemo, useState } from "react";
import CameraCapture from "./CameraCapture";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

export default function EnrollmentWithFace({ sections = [], onEnrolled }) {
  const [selectedSec, setSelectedSec] = useState("");
  const [name, setName] = useState("");
  const [parentMobile, setParentMobile] = useState("");
  const [gender, setGender] = useState("");
  const [hasTwin, setHasTwin] = useState(false);
  const [twinGroupId, setTwinGroupId] = useState("");
  const [twinOf, setTwinOf] = useState("");
  const [facingMode, setFacingMode] = useState("user");
  const [shots, setShots] = useState([]); // { blob, url }
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [sampleUrl, setSampleUrl] = useState("https://images.pexels.com/photos/2379004/pexels-photo-2379004.jpeg?auto=compress&cs=tinysrgb&dpr=1&w=256");

  // Twin search state
  const [twinSearch, setTwinSearch] = useState("");
  const [twinResults, setTwinResults] = useState([]);
  const [twinSearching, setTwinSearching] = useState(false);
  const [selectedTwin, setSelectedTwin] = useState(null);

  // Debounced search for twins within the same section
  useEffect(() => {
    let t = null;
    if (!hasTwin) { setTwinResults([]); setTwinSearch(""); setSelectedTwin(null); return; }
    if (!selectedSec) return;
    if ((twinSearch || "").trim().length < 2) { setTwinResults([]); return; }
    setTwinSearching(true);
    t = setTimeout(async () => {
      try {
        const res = await api.get('/students/search', { params: { query: twinSearch.trim(), section_id: selectedSec } });
        setTwinResults(res.data.items || []);
      } catch (e) {
        setTwinResults([]);
      } finally {
        setTwinSearching(false);
      }
    }, 300);
    return () => t && clearTimeout(t);
  }, [twinSearch, hasTwin, selectedSec]);

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
      setMessage("❌ Failed to load sample image URL");
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true); 
    setMessage("");
    try {
      const fd = new FormData();
      fd.append("name", name);
      fd.append("section_id", selectedSec);
      if (parentMobile) fd.append("parent_mobile", parentMobile);
      if (gender) fd.append("gender", gender);
      fd.append("has_twin", hasTwin ? "true" : "false");
      if (twinGroupId) fd.append("twin_group_id", twinGroupId);
      if (hasTwin && twinOf) fd.append("twin_of", twinOf);
      shots.forEach((s, i) => fd.append("images", s.blob, `shot_${i+1}.jpg`));
      const res = await api.post("/enrollment/students", fd);
      setMessage(`✅ Successfully enrolled ${res.data.name}! Face embeddings created: ${res.data.embeddings_count}`);
      // Bubble up to parent so it can refresh the section-wise list
      if (onEnrolled) {
        try { onEnrolled(res.data); } catch (e) {}
      }
      // Reset fields but keep section selected
      setName(""); setParentMobile(""); setHasTwin(false); setTwinGroupId(""); setTwinOf(""); setTwinSearch(""); setTwinResults([]); setSelectedTwin(null); setShots([]);
    } catch (err) {
      const errorMsg = err?.response?.data?.detail || "Enrollment failed";
      setMessage(`❌ ${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card wide animate-slide-in" style={{ 
      background: 'linear-gradient(135deg, rgba(79, 172, 254, 0.1) 0%, rgba(0, 242, 254, 0.1) 100%)',
      border: '2px solid rgba(79, 172, 254, 0.2)'
    }}>
      <h3 className="card_title" style={{ color: '#1e40af', marginBottom: '1.5rem' }}>
        🎭 Student Face Enrollment System
      </h3>
      
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white font-bold text-sm">AI</div>
          <h4 className="font-semibold text-blue-800">Advanced Face Recognition System</h4>
        </div>
        <p className="text-blue-700 text-sm">
          Our system uses <strong>MediaPipe Face Mesh + MobileFaceNet</strong> technology for accurate face detection and recognition. 
          Capture 3-5 high-quality photos from different angles for optimal enrollment.
        </p>
      </div>

      <form onSubmit={submit}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div className="form_row">
            <Label className="form_label">📚 Select Section</Label>
            <select 
              className="select" 
              value={selectedSec} 
              onChange={(e) => setSelectedSec(e.target.value)} 
              required
              style={{ 
                border: '2px solid #dbeafe',
                borderRadius: '12px',
                padding: '12px',
                background: 'white'
              }}
            >
              <option value="">Choose a section</option>
              {sections.map((s) => (
                <option key={s.id} value={s.id}>{s.name}{s.grade ? ` (Grade ${s.grade})` : ''}</option>
              ))}
            </select>
          </div>

          <div className="form_row">
            <Label className="form_label">👤 Student Name</Label>
            <Input 
              value={name} 
              onChange={(e) => setName(e.target.value)} 
              className="form_input"
              placeholder="Enter student's full name"
              required 
              style={{ 
                border: '2px solid #dbeafe',
                borderRadius: '12px',
                padding: '12px'
              }}
            />
          </div>

          <div className="form_row">
            <Label className="form_label">📱 Parent's Mobile</Label>
            <Input 
              value={parentMobile} 
              onChange={(e) => setParentMobile(e.target.value)} 
              className="form_input"
              placeholder="e.g., +91 98765 43210"
              style={{ 
                border: '2px solid #dbeafe',
                borderRadius: '12px',
                padding: '12px'
              }}
            />
          </div>

          <div className="form_row">
            <Label className="form_label">👯 Twin Settings</Label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <label style={{ display:'flex', alignItems:'center', gap:'8px', padding: '12px', background: '#f0f9ff', borderRadius: '12px', border: '2px solid #dbeafe' }}>
                <input 
                  type="checkbox" 
                  checked={hasTwin} 
                  onChange={(e)=>setHasTwin(e.target.checked)}
                  style={{ width: '18px', height: '18px' }}
                /> 
                <span className="text-sm font-medium">Is Twin?</span>
              </label>
              <div>
                <Input 
                  value={twinOf} 
                  onChange={(e)=>{ setTwinOf(e.target.value); setSelectedTwin(null); }} 
                  placeholder="Twin sibling Student ID"
                  disabled={!hasTwin}
                  style={{ 
                    border: '2px solid #dbeafe',
                    borderRadius: '12px',
                    padding: '12px',
                    opacity: hasTwin ? 1 : 0.5,
                    marginBottom: '8px'
                  }}
                />
                {hasTwin && (
                  <div className="mt-2">
                    <Input
                      value={twinSearch}
                      onChange={(e)=> setTwinSearch(e.target.value)}
                      placeholder="Search twin by name / roll / code"
                      disabled={!selectedSec}
                      className="form_input"
                    />
                    {/* Results dropdown */}
                    {twinSearching && <div className="text-xs text-gray-500 mt-1">Searching...</div>}
                    {!twinSearching && twinResults.length > 0 && (
                      <div className="mt-2 border rounded-lg bg-white shadow-sm max-h-40 overflow-auto">
                        {twinResults.map((it) => (
                          <button
                            type="button"
                            key={it.id}
                            className="w-full text-left px-3 py-2 hover:bg-blue-50"
                            onClick={() => {
                              setTwinOf(it.id);
                              setSelectedTwin(it);
                              setTwinSearch(it.name);
                            }}
                          >
                            <div className="text-sm font-medium text-gray-800">{it.name}</div>
                            <div className="text-xs text-gray-500">ID: {it.id}{it.roll_no ? ` • Roll: ${it.roll_no}` : ''}{it.student_code ? ` • Code: ${it.student_code}` : ''}</div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
              <Input 
                value={twinGroupId} 
                onChange={(e)=>setTwinGroupId(e.target.value)} 
                placeholder="Twin group ID (optional)"
                disabled={!hasTwin}
                style={{ 
                  border: '2px solid #dbeafe',
                  borderRadius: '12px',
                  padding: '12px',
                  opacity: hasTwin ? 1 : 0.5
                }}
              />
            </div>
          </div>
        </div>

        <div className="form_row">
          <Label className="form_label">📸 Face Capture System</Label>
          <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border-2 border-indigo-200 rounded-xl p-6">
            <CameraCapture 
              facingMode={facingMode} 
              onToggleFacing={()=>setFacingMode(facingMode === 'user' ? 'environment' : 'user')} 
              onCapture={onCapture} 
              captureLabel="📷 Capture Face Image" 
            />
            
            <div className="mt-4 p-4 bg-white bg-opacity-70 rounded-lg">
              <div className="text-sm text-gray-600 mb-4">
                💡 <strong>Pro Tips:</strong> Capture 3–5 shots from different angles (front, left profile, right profile). 
                Good lighting and clear face visibility are essential for accurate recognition.
              </div>
              
              <div className="flex gap-3 items-center">
                <Input 
                  value={sampleUrl} 
                  onChange={(e)=>setSampleUrl(e.target.value)} 
                  placeholder="Or paste sample image URL for testing"
                  className="form_input flex-1"
                  style={{ fontSize: '14px' }}
                />
                <Button 
                  type="button" 
                  className="btn_secondary" 
                  onClick={addSample}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  🖼️ Add Sample
                </Button>
              </div>
            </div>
          </div>
        </div>

        {shots.length > 0 && (
          <div className="form_row">
            <Label className="form_label">📋 Captured Images ({shots.length}/5)</Label>
            <div className="bg-white rounded-xl border-2 border-gray-200 p-4">
              <div className="thumbs">
                {shots.map((s, i) => (
                  <div key={i} className="thumb group">
                    <img src={s.url} alt={`shot_${i+1}`} style={{ borderRadius: '8px' }} />
                    <button 
                      type="button" 
                      className="thumb-remove"
                      onClick={()=>removeShot(i)}
                      title="Remove this image"
                    >
                      ❌
                    </button>
                    <div className="absolute bottom-1 left-1 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded">
                      #{i+1}
                    </div>
                  </div>
                ))}
              </div>
              <div className="text-center mt-4 text-sm text-gray-600">
                {shots.length < 3 && <span className="text-orange-600">⚠️ Recommend at least 3 images for better accuracy</span>}
                {shots.length >= 3 && <span className="text-green-600">✅ Good! You have enough images for enrollment</span>}
              </div>
            </div>
          </div>
        )}

        {message && (
          <div className={`${message.includes('✅') ? 'success_message' : 'error_text'} animate-fade-in`} style={{ margin: '1rem 0' }}>
            {message}
          </div>
        )}

        <div className="flex justify-center pt-6">
          <Button 
            type="submit" 
            className={`${canSubmit && !loading ? 'btn_success' : 'btn_secondary'} px-8 py-3 text-lg font-semibold`}
            disabled={!canSubmit || loading}
            style={{ 
              minWidth: '200px',
              background: canSubmit && !loading ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : undefined,
              transform: loading ? 'scale(0.98)' : 'scale(1)',
              transition: 'all 0.2s ease-in-out'
            }}
          >
            {loading ? (
              <>
                <span className="animate-spin mr-2">⏳</span>
                Enrolling Student...
              </>
            ) : (
              <>
                🎭 Enroll Student with Face ID
              </>
            )}
          </Button>
        </div>
      </form>

      {/* Additional CSS for thumbs styling */}
      <style jsx>{`
        .thumbs {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
          gap: 1rem;
        }
        .thumb {
          position: relative;
          border-radius: 12px;
          overflow: hidden;
          background: white;
          border: 2px solid #e5e7eb;
          transition: all 0.3s ease;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .thumb:hover {
          transform: scale(1.05);
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
          border-color: #3b82f6;
        }
        .thumb img {
          width: 100%;
          height: 100px;
          object-fit: cover;
          display: block;
        }
        .thumb-remove {
          position: absolute;
          top: 4px;
          right: 4px;
          background: rgba(239, 68, 68, 0.9);
          color: white;
          border: none;
          border-radius: 50%;
          width: 24px;
          height: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 10px;
          cursor: pointer;
          transition: all 0.2s ease;
          opacity: 0;
        }
        .thumb:hover .thumb-remove {
          opacity: 1;
        }
        .thumb-remove:hover {
          background: #dc2626;
          transform: scale(1.1);
        }
      `}</style>
    </div>
  );
}
