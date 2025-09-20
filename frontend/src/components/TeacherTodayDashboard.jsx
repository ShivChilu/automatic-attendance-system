import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

function StatCard({ title, value, subtitle, accent = "#1e40af" }) {
  return (
    <div className="card narrow animate-scale-in">
      <div className="stats_card" style={{ background: 'white', color: '#1f2937' }}>
        <div className="stats_number" style={{ color: accent }}>{value}</div>
        <div className="stats_label" style={{ color: '#6b7280' }}>{title}</div>
        {subtitle && <div className="text-xs mt-2" style={{ color: '#6b7280' }}>{subtitle}</div>}
      </div>
    </div>
  );
}

function LiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => { 
    const t = setInterval(() => setNow(new Date()), 1000); 
    return () => clearInterval(t); 
  }, []);
  return (
    <div className="text-sm text-gray-700 font-mono">
      {now.toLocaleTimeString('en-US', { 
        hour12: true, 
        hour: 'numeric', 
        minute: '2-digit', 
        second: '2-digit' 
      })}
    </div>
  );
}

export default function TeacherTodayDashboard({ me, onSectionChange }) {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const loadTodayOverview = async () => {
    try {
      setLoading(true);
      const res = await api.get("/attendance/teacher/today");
      setOverview(res.data);
      setLastUpdated(new Date());
    } catch (e) {
      console.error("Failed to load today's overview:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTodayOverview();
    // Refresh every 30 seconds
    const interval = setInterval(loadTodayOverview, 30000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (timestamp) => {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleTimeString('en-US', { 
      hour12: true, 
      hour: 'numeric', 
      minute: '2-digit' 
    });
  };

  if (loading && !overview) {
    return (
      <div className="card wide animate-slide-in">
        <div className="flex items-center justify-center p-8">
          <div className="text-gray-500">Loading today's attendance data...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with live clock */}
      <div className="card wide animate-slide-in">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-gray-800">📊 Today's Attendance Overview</h3>
            <p className="text-sm text-gray-600 mt-1">
              {overview?.date ? new Date(overview.date).toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              }) : 'Loading...'}
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">Current Time</div>
            <LiveClock />
            <div className="text-xs text-gray-400 mt-1">
              Last updated: {lastUpdated.toLocaleTimeString('en-US', { 
                hour12: true, 
                hour: 'numeric', 
                minute: '2-digit' 
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard 
          title="Sessions Today" 
          value={overview?.total_sessions || 0} 
          subtitle="Attendance sessions created"
          accent="#3b82f6"
        />
        <StatCard 
          title="Students Marked" 
          value={overview?.total_students_marked || 0} 
          subtitle="Total attendance marked"
          accent="#10b981"
        />
        <StatCard 
          title="Sections Active" 
          value={overview?.sections?.length || 0} 
          subtitle="Sections with students"
          accent="#f59e0b"
        />
      </div>

      {/* Sections Overview */}
      {overview?.sections && overview.sections.length > 0 && (
        <div className="card wide animate-slide-in">
          <h4 className="text-lg font-semibold mb-4 text-gray-800">📚 Section-wise Attendance</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {overview.sections.map((section) => (
              <div key={section.section_id} className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h5 className="font-semibold text-gray-800">{section.section_name}</h5>
                  {section.grade && (
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      Grade {section.grade}
                    </span>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Present:</span>
                    <span className="font-semibold text-green-600">{section.present_today}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Total:</span>
                    <span className="font-semibold text-gray-800">{section.total_students}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-gradient-to-r from-green-400 to-green-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${section.attendance_percentage}%` }}
                    ></div>
                  </div>
                  <div className="text-center text-sm font-semibold text-gray-700">
                    {section.attendance_percentage}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {overview?.recent_activity && overview.recent_activity.length > 0 && (
        <div className="card wide animate-slide-in">
          <h4 className="text-lg font-semibold mb-4 text-gray-800">🕒 Recent Activity</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {overview.recent_activity.map((activity, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                    <span className="text-green-600 text-sm">✓</span>
                  </div>
                  <div>
                    <div className="font-medium text-gray-800">{activity.student_name}</div>
                    <div className="text-sm text-gray-600">{activity.section_name}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium text-gray-800">
                    {formatTime(activity.marked_at)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {activity.status}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="card wide animate-slide-in">
        <h4 className="text-lg font-semibold mb-4 text-gray-800">⚡ Quick Actions</h4>
        <div className="flex flex-wrap gap-3">
          <Button 
            className="btn_primary" 
            onClick={() => onSectionChange('scan-attendance')}
          >
            📸 Mark Attendance
          </Button>
          <Button 
            className="btn_secondary" 
            onClick={loadTodayOverview}
          >
            🔄 Refresh Data
          </Button>
        </div>
      </div>

      {/* No data message */}
      {overview && overview.total_sessions === 0 && overview.total_students_marked === 0 && (
        <div className="card wide animate-slide-in">
          <div className="text-center py-8">
            <div className="text-6xl mb-4">📝</div>
            <h4 className="text-lg font-semibold text-gray-800 mb-2">No Attendance Marked Today</h4>
            <p className="text-gray-600 mb-4">Start marking attendance for your sections</p>
            <Button 
              className="btn_primary" 
              onClick={() => onSectionChange('scan-attendance')}
            >
              Start Attendance Session
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
