import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

function StatCard({ title, value, subtitle, accent = "#1e40af" }) {
  return (
    <div className="bg-white bg-opacity-95 backdrop-filter backdrop-blur-xl border border-white border-opacity-20 rounded-2xl p-6 shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300 animate-scale-in">
      <div className="stats_card" style={{ background: 'transparent', color: '#1f2937' }}>
        <div className="stats_number text-3xl font-bold mb-2" style={{ color: accent }}>{value}</div>
        <div className="stats_label text-sm font-medium" style={{ color: '#6b7280' }}>{title}</div>
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

export default function PrincipalTodayDashboard({ me }) {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const loadTodayOverview = async () => {
    try {
      setLoading(true);
      const res = await api.get("/attendance/principal/today");
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

  if (loading && !overview) {
    return (
      <div className="card wide animate-slide-in">
        <div className="flex items-center justify-center p-8">
          <div className="text-gray-500">Loading today's school data...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-none mx-0 px-4 lg:px-6 space-y-6">
      {/* Header with live clock */}
      <div className="bg-white bg-opacity-95 backdrop-filter backdrop-blur-xl border border-white border-opacity-20 rounded-2xl p-6 shadow-lg animate-slide-in">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-bold text-gray-800">🏫 School Overview - Today</h3>
            <p className="text-sm text-gray-600 mt-1">
              {overview?.school_name || 'Loading...'} • {overview?.date ? new Date(overview.date).toLocaleDateString('en-US', { 
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

      {/* Main Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        <StatCard 
          title="Total Students" 
          value={overview?.total_students || 0} 
          subtitle="Enrolled students"
          accent="#3b82f6"
        />
        <StatCard 
          title="Present Today" 
          value={overview?.total_present || 0} 
          subtitle="Students marked present"
          accent="#10b981"
        />
        <StatCard 
          title="Attendance Rate" 
          value={`${overview?.attendance_percentage || 0}%`} 
          subtitle="Overall attendance"
          accent="#f59e0b"
        />
        <StatCard 
          title="Active Sections" 
          value={overview?.total_sections || 0} 
          subtitle="Sections with students"
          accent="#8b5cf6"
        />
      </div>

      {/* Attendance Progress Bar */}
      {overview && (
        <div className="bg-white bg-opacity-95 backdrop-filter backdrop-blur-xl border border-white border-opacity-20 rounded-2xl p-6 shadow-lg animate-slide-in">
          <h4 className="text-lg font-semibold mb-4 text-gray-800">📊 Overall Attendance Progress</h4>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700">Attendance Rate</span>
              <span className="text-sm font-bold text-gray-900">{overview.attendance_percentage}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4">
              <div 
                className="bg-gradient-to-r from-green-400 to-green-600 h-4 rounded-full transition-all duration-1000 flex items-center justify-end pr-2"
                style={{ width: `${Math.min(overview.attendance_percentage, 100)}%` }}
              >
                <span className="text-xs font-semibold text-white">
                  {overview.attendance_percentage}%
                </span>
              </div>
            </div>
            <div className="flex justify-between text-sm text-gray-600">
              <span>{overview.total_present} present</span>
              <span>{overview.total_students - overview.total_present} absent</span>
            </div>
          </div>
        </div>
      )}

      {/* Section-wise Breakdown */}
      {overview?.sections && overview.sections.length > 0 && (
        <div className="bg-white bg-opacity-95 backdrop-filter backdrop-blur-xl border border-white border-opacity-20 rounded-2xl p-6 shadow-lg animate-slide-in">
          <h4 className="text-lg font-semibold mb-4 text-gray-800">📚 Section-wise Attendance</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {overview.sections.map((section) => (
              <div key={section.section_id} className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-3">
                  <h5 className="font-semibold text-gray-800">{section.section_name}</h5>
                  {section.grade && (
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      Grade {section.grade}
                    </span>
                  )}
                </div>
                <div className="space-y-3">
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
                  <div className="text-center">
                    <span className="text-sm font-semibold text-gray-700">
                      {section.attendance_percentage}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Teachers Activity */}
      {overview?.teachers_activity && overview.teachers_activity.length > 0 && (
        <div className="bg-white bg-opacity-95 backdrop-filter backdrop-blur-xl border border-white border-opacity-20 rounded-2xl p-6 shadow-lg animate-slide-in">
          <h4 className="text-lg font-semibold mb-4 text-gray-800">👨‍🏫 Teachers Activity Today</h4>
          <div className="space-y-3">
            {overview.teachers_activity.map((teacher, index) => (
              <div key={teacher.teacher_id || index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-blue-600 font-semibold">
                      {teacher.teacher_name?.charAt(0) || '👨‍🏫'}
                    </span>
                  </div>
                  <div>
                    <div className="font-medium text-gray-800">{teacher.teacher_name}</div>
                    <div className="text-sm text-gray-600">{teacher.subject}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-green-600">{teacher.students_marked}</div>
                  <div className="text-xs text-gray-500">students marked</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="bg-white bg-opacity-95 backdrop-filter backdrop-blur-xl border border-white border-opacity-20 rounded-2xl p-6 shadow-lg animate-slide-in">
        <h4 className="text-lg font-semibold mb-4 text-gray-800">⚡ Quick Actions</h4>
        <div className="flex flex-wrap gap-3">
          <Button 
            className="btn_primary" 
            onClick={() => window.location.href = '#attendance-reports'}
          >
            📊 View Reports
          </Button>
          <Button 
            className="btn_secondary" 
            onClick={loadTodayOverview}
          >
            🔄 Refresh Data
          </Button>
          <Button 
            className="btn_outline" 
            onClick={() => window.location.href = '#sections'}
          >
            📚 Manage Sections
          </Button>
        </div>
      </div>

      {/* No data message */}
      {overview && overview.total_present === 0 && (
        <div className="card wide animate-slide-in">
          <div className="text-center py-8">
            <div className="text-6xl mb-4">📝</div>
            <h4 className="text-lg font-semibold text-gray-800 mb-2">No Attendance Marked Today</h4>
            <p className="text-gray-600 mb-4">Teachers haven't started marking attendance yet</p>
            <Button 
              className="btn_primary" 
              onClick={() => window.location.href = '#teachers'}
            >
              Check Teacher Status
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
