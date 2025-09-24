import React, { useEffect, useState } from 'react';

const Sidebar = ({ me, currentSection, onSectionChange, onToggle, onLogout }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('sidebar_collapsed');
    if (saved === 'true') setIsCollapsed(true);
  }, []);

  const toggle = () => {
    const next = !isCollapsed;
    setIsCollapsed(next);
    localStorage.setItem('sidebar_collapsed', String(next));
    if (onToggle) onToggle(next);
  };

  const getMenuItems = () => {
    if (me?.role === 'GOV_ADMIN') {
      return [
        {
          section: 'overview',
          title: 'Overview',
          icon: '📊',
          items: [
            { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
            { id: 'analytics', label: 'Analytics', icon: '📈' }
          ]
        },
        {
          section: 'schools',
          title: 'School Management',
          icon: '🏫',
          items: [
            { id: 'create-school', label: 'Create School', icon: '➕' },
            { id: 'manage-schools', label: 'Manage Schools', icon: '⚙️' },
            { id: 'school-reports', label: 'School Reports', icon: '📋' }
          ]
        },
        {
          section: 'system',
          title: 'System',
          icon: '🔧',
          items: [
            { id: 'settings', label: 'Settings', icon: '⚙️' },
            { id: 'users', label: 'System Users', icon: '👥' }
          ]
        }
      ];
    } else if (me?.role === 'SCHOOL_ADMIN' || me?.role === 'CO_ADMIN') {
      return [
        {
          section: 'overview',
          title: 'Overview',
          icon: '📊',
          items: [
            { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
            { id: 'school-stats', label: 'School Stats', icon: '📈' }
          ]
        },
        {
          section: 'academic',
          title: 'Academic Management',
          icon: '📚',
          items: [
            { id: 'sections', label: 'Manage Sections', icon: '📝' },
            { id: 'students', label: 'Student Management', icon: '👨‍🎓' },
            { id: 'enrollment', label: 'Face Enrollment', icon: '🎭' }
          ]
        },
        {
          section: 'communication',
          title: 'Communication',
          icon: '💬',
          items: [
            { id: 'announcements', label: 'Announcements', icon: '📢' },
            { id: 'messages', label: 'Messages', icon: '📩' }
          ]
        },
        {
          section: 'staff',
          title: 'Staff Management',
          icon: '👥',
          items: [
            { id: 'teachers', label: 'Teachers', icon: '👨‍🏫' },
            { id: 'co-admins', label: 'Co-Admins', icon: '👨‍💼' },
            { id: 'create-staff', label: 'Create Staff', icon: '➕' }
          ]
        },
        {
          section: 'attendance',
          title: 'Attendance',
          icon: '📅',
          items: [
            { id: 'attendance-reports', label: 'Reports', icon: '📊' },
            { id: 'attendance-summary', label: 'Summary', icon: '📋' }
          ]
        }
      ];
    } else if (me?.role === 'TEACHER') {
      return [
        {
          section: 'overview',
          title: 'Overview',
          icon: '📊',
          items: [
            { id: 'dashboard', label: 'Dashboard', icon: '🏠' }
          ]
        },
        {
          section: 'attendance',
          title: 'Attendance',
          icon: '📸',
          items: [
            { id: 'scan-attendance', label: 'Scan Attendance', icon: '📷' },
            { id: 'attendance-history', label: 'History', icon: '📅' }
          ]
        },
        {
          section: 'students',
          title: 'Students',
          icon: '👨‍🎓',
          items: [
            { id: 'student-list', label: 'Student List', icon: '📝' }
          ]
        },
        {
          section: 'communication',
          title: 'Communication',
          icon: '💬',
          items: [
            { id: 'my-messages', label: 'My Messages', icon: '📩' },
            { id: 'announcements', label: 'Announcements', icon: '📢' }
          ]
        }
      ];
    }
    return [];
  };

  const menuItems = getMenuItems();

  return (
    <>
      {/* Overlay when open on small screens */}
      {!isCollapsed && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={toggle}
        />
      )}
      
      {/* Mobile Menu Toggle Button - Only for SCHOOL_ADMIN/CO_ADMIN on mobile */}
      {(me?.role === 'SCHOOL_ADMIN' || me?.role === 'CO_ADMIN') && (
        <button
          onClick={toggle}
          className="fixed top-20 left-4 z-50 lg:hidden p-3 bg-white bg-opacity-90 backdrop-filter backdrop-blur-sm rounded-xl shadow-lg border border-white border-opacity-30 hover:bg-opacity-100 transition-all duration-200"
          title={isCollapsed ? 'Open menu' : 'Close menu'}
        >
          <span className="text-lg font-bold text-gray-700">
            {isCollapsed ? '☰' : '✕'}
          </span>
        </button>
      )}
      
      {/* Sidebar - Now visible on mobile when opened */}
      <div className={`fixed left-0 top-0 h-full bg-white bg-opacity-95 backdrop-filter backdrop-blur-xl border-r border-white border-opacity-20 z-50 transition-all duration-300 ${
        isCollapsed ? '-translate-x-full' : 'w-80 lg:w-72'
      }`}>
        
        {/* Header */}
        <div className="p-6 border-b border-white border-opacity-20">
          <div className="flex items-center justify-between">
            {!isCollapsed && (
              <div>
                <h2 className="text-xl font-bold text-gray-900">Navigation</h2>
                <p className="text-sm text-gray-600 mt-1">{me?.role?.replace('_', ' ')}</p>
              </div>
            )}
            <button
              onClick={toggle}
              className="p-2 rounded-lg bg-white bg-opacity-50 hover:bg-opacity-70 transition-all duration-200 text-gray-700 hover:text-gray-900"
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? '→' : '←'}
            </button>
          </div>
        </div>

        {/* Navigation Menu */}
        <div className="flex-1 overflow-y-auto p-4">
          {menuItems.map((section) => (
            <div key={section.section} className="mb-8">
              {!isCollapsed && (
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 px-3">
                  {section.icon} {section.title}
                </h3>
              )}
              <div className="space-y-1">
                {section.items.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onSectionChange(item.id)}
                    className={`w-full flex items-center px-3 py-3 rounded-xl transition-all duration-200 text-left group ${
                      currentSection === item.id
                        ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white shadow-lg transform scale-105'
                        : 'text-gray-700 hover:bg-white hover:bg-opacity-50 hover:text-gray-900 hover:shadow-md'
                    }`}
                  >
                    <span className="text-lg mr-3">{item.icon}</span>
                    {!isCollapsed && (
                      <span className="font-medium">{item.label}</span>
                    )}
                    {!isCollapsed && (
                      <span className={`ml-auto transition-all duration-200 ${
                        currentSection === item.id 
                          ? 'text-white' 
                          : 'text-gray-400 group-hover:text-gray-600'
                      }`}>
                        →
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-white border-opacity-20">
          {!isCollapsed && (
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-4 border border-white border-opacity-30">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                  {me?.full_name?.charAt(0) || '👤'}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-gray-900">{me?.full_name}</p>
                  <p className="text-xs text-gray-600">{me?.email}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Toggle handle visible when collapsed on desktop */}
      {isCollapsed && (
        <button
          onClick={toggle}
          className="fixed top-1/2 -translate-y-1/2 left-2 z-40 hidden lg:block p-2 bg-white bg-opacity-90 backdrop-filter backdrop-blur-sm rounded-xl shadow-lg border border-white border-opacity-30"
          title="Expand sidebar"
        >
          →
        </button>
      )}

      {/* Mobile Bottom Navigation - Only for Teachers */}
      {me?.role === 'TEACHER' && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50 lg:hidden">
        <div className="grid grid-cols-5 h-16">
          {[
            { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
            { id: 'scan-attendance', label: 'Scan', icon: '📷' },
            { id: 'my-messages', label: 'Messages', icon: '📩' },
            { id: 'attendance-history', label: 'History', icon: '📅' },
            { id: 'profile', label: 'Profile', icon: '👤' }
          ].map((item, index) => (
            <button
              key={item.id}
              onClick={() => {
                if (item.id === 'profile') {
                  // Show profile dropdown or handle logout
                  if (confirm('Do you want to logout?')) {
                    if (onLogout) {
                      onLogout();
                    }
                  }
                } else {
                  onSectionChange(item.id);
                }
              }}
              className={`flex flex-col items-center justify-center space-y-1 transition-colors duration-200 ${
                currentSection === item.id
                  ? 'text-blue-600 bg-blue-50'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              <span className="text-xs font-medium">{item.label}</span>
            </button>
          ))}
        </div>
        </div>
      )}
    </>
  );
};

export default Sidebar;
