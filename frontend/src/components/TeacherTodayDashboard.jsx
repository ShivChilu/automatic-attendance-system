import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Card } from "./ui/card";

function StatCard({ title, value, subtitle, icon, accent = "#3b82f6", trend }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all duration-200">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 mb-1">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mb-1" style={{ color: accent }}>{value}</p>
          {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
          {trend && (
            <div className="flex items-center mt-2">
              <span className={`text-xs font-medium ${trend.positive ? 'text-green-600' : 'text-red-600'}`}>
                {trend.positive ? '↗' : '↘'} {trend.value}
              </span>
            </div>
          )}
        </div>
        <div className="w-12 h-12 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${accent}15` }}>
          <span className="text-2xl">{icon}</span>
        </div>
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
    <div className="text-right">
      <div className="text-sm text-gray-500 mb-1">Current Time</div>
      <div className="text-lg font-mono font-semibold text-gray-800">
        {now.toLocaleTimeString('en-US', { 
          hour12: true, 
          hour: 'numeric', 
          minute: '2-digit', 
          second: '2-digit' 
        })}
      </div>
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
    <div className="min-h-screen bg-gray-50">
      {/* Header Section */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between py-6">
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">
                Teacher Dashboard
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                {overview?.date ? new Date(overview.date).toLocaleDateString('en-US', { 
                  weekday: 'long', 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                }) : 'Loading...'}
              </p>
            </div>
            <div className="mt-4 sm:mt-0">
              <LiveClock />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Statistics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard 
            title="Sessions Today" 
            value={overview?.total_sessions || 0} 
            subtitle="Attendance sessions created"
            icon="📊"
            accent="#3b82f6"
          />
          <StatCard 
            title="Students Marked" 
            value={overview?.total_students_marked || 0} 
            subtitle="Total attendance marked"
            icon="👥"
            accent="#10b981"
          />
          <StatCard 
            title="Sections Active" 
            value={overview?.sections?.length || 0} 
            subtitle="Sections with students"
            icon="📚"
            accent="#f59e0b"
          />
          <StatCard 
            title="Attendance Rate" 
            value={overview?.sections?.length > 0 ? 
              Math.round(overview.sections.reduce((acc, s) => acc + s.attendance_percentage, 0) / overview.sections.length) : 0} 
            subtitle="Average across sections"
            icon="📈"
            accent="#8b5cf6"
          />
        </div>

        {/* Sections Overview */}
        {overview?.sections && overview.sections.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Section-wise Attendance</h3>
              <p className="text-sm text-gray-600 mt-1">Real-time attendance data for your assigned sections</p>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {overview.sections.map((section) => (
                  <div key={section.section_id} className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-semibold text-gray-900">{section.section_name}</h4>
                      {section.grade && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          Grade {section.grade}
                        </span>
                      )}
                    </div>
                    
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Present</span>
                        <span className="text-lg font-semibold text-green-600">{section.present_today}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Total</span>
                        <span className="text-lg font-semibold text-gray-900">{section.total_students}</span>
                      </div>
                      
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Attendance</span>
                          <span className="font-medium text-gray-900">{section.attendance_percentage}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-gradient-to-r from-green-400 to-green-600 h-2 rounded-full transition-all duration-700"
                            style={{ width: `${Math.min(section.attendance_percentage, 100)}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Recent Activity */}
        {overview?.recent_activity && overview.recent_activity.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Recent Activity</h3>
              <p className="text-sm text-gray-600 mt-1">Latest attendance marks and updates</p>
            </div>
            <div className="p-6">
              <div className="space-y-3 max-h-80 overflow-y-auto">
                {overview.recent_activity.map((activity, index) => (
                  <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                    <div className="flex items-center space-x-4">
                      <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                        <span className="text-green-600 text-lg">✓</span>
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">{activity.student_name}</div>
                        <div className="text-sm text-gray-600">{activity.section_name}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900">
                        {formatTime(activity.marked_at)}
                      </div>
                      <div className="text-xs text-gray-500 capitalize">
                        {activity.status}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Quick Actions</h3>
            <p className="text-sm text-gray-600 mt-1">Common tasks and shortcuts</p>
          </div>
          <div className="p-6">
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                onClick={() => onSectionChange('scan-attendance')}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors duration-200 flex items-center justify-center space-x-2"
              >
                <span className="text-xl">📸</span>
                <span>Mark Attendance</span>
              </button>
              <button
                onClick={loadTodayOverview}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-3 px-6 rounded-lg transition-colors duration-200 flex items-center justify-center space-x-2"
              >
                <span className="text-xl">🔄</span>
                <span>Refresh Data</span>
              </button>
            </div>
          </div>
        </div>

        {/* No data message */}
        {overview && overview.total_sessions === 0 && overview.total_students_marked === 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="text-center py-12 px-6">
              <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-4xl">📝</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">No Attendance Marked Today</h3>
              <p className="text-gray-600 mb-6 max-w-md mx-auto">
                Start marking attendance for your assigned sections to track student presence
              </p>
              <button
                onClick={() => onSectionChange('scan-attendance')}
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-8 rounded-lg transition-colors duration-200 inline-flex items-center space-x-2"
              >
                <span className="text-xl">📸</span>
                <span>Start Attendance Session</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
