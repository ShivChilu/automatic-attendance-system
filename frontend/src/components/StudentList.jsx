import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";
import { Button } from "./ui/button";

export default function StudentList({ me }) {
  const [sections, setSections] = useState([]);
  const [selectedSection, setSelectedSection] = useState('');
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showDownloadModal, setShowDownloadModal] = useState(false);
  const [selectedColumns, setSelectedColumns] = useState({
    rollNo: true,
    name: true,
    parentMobile: true,
    enrollmentStatus: true
  });

  const loadSections = async () => {
    try {
      const res = await api.get("/sections");
      setSections(res.data || []);
      if (res.data && res.data.length > 0) {
        setSelectedSection(res.data[0].id);
      }
    } catch (e) {
      console.error("Failed to load sections:", e);
    }
  };

  const loadStudents = async (sectionId) => {
    if (!sectionId) return;
    
    setLoading(true);
    try {
      const res = await api.get("/students", {
        params: { section_id: sectionId, enrolled_only: false }
      });
      setStudents(res.data || []);
    } catch (e) {
      console.error("Failed to load students:", e);
      setStudents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSections();
  }, []);

  useEffect(() => {
    if (selectedSection) {
      loadStudents(selectedSection);
    }
  }, [selectedSection]);

  const selectedSectionData = sections.find(s => s.id === selectedSection);

  const downloadCSV = () => {
    if (students.length === 0) {
      alert('No students to download');
      return;
    }

    // Prepare CSV headers based on selected columns
    const headers = [];
    if (selectedColumns.rollNo) headers.push('Roll No');
    if (selectedColumns.name) headers.push('Student Name');
    if (selectedColumns.parentMobile) headers.push('Parent Mobile');
    if (selectedColumns.enrollmentStatus) headers.push('Enrollment Status');

    // Prepare CSV data
    const csvData = students
      .sort((a, b) => {
        const aRoll = a.roll_no || a.name;
        const bRoll = b.roll_no || b.name;
        return aRoll.localeCompare(bRoll, undefined, { numeric: true });
      })
      .map(student => {
        const row = [];
        if (selectedColumns.rollNo) row.push(student.roll_no || '');
        if (selectedColumns.name) row.push(student.name);
        if (selectedColumns.parentMobile) row.push(student.parent_mobile || '');
        if (selectedColumns.enrollmentStatus) row.push(student.enrolled ? 'Enrolled' : 'Not Enrolled');
        return row;
      });

    // Create CSV content
    const csvContent = [
      headers.join(','),
      ...csvData.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    
    const sectionName = selectedSectionData?.name || 'students';
    const fileName = `${sectionName}_student_list_${new Date().toISOString().slice(0, 10)}.csv`;
    link.setAttribute('download', fileName);
    
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    setShowDownloadModal(false);
  };

  const toggleColumn = (column) => {
    setSelectedColumns(prev => ({
      ...prev,
      [column]: !prev[column]
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 sm:py-6">
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900">
              Student List
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-gray-600">
              View and manage students by section
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Section Selector */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Select Section</h3>
          </div>
          <div className="p-6">
            <div className="max-w-md">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Choose Section
              </label>
              <select
                value={selectedSection}
                onChange={(e) => setSelectedSection(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select Section</option>
                {sections.map(section => (
                  <option key={section.id} value={section.id}>
                    {section.name} {section.grade ? `(Grade ${section.grade})` : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Section Info */}
        {selectedSectionData && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 mb-8">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Section Information</h3>
                {students.length > 0 && (
                  <button
                    onClick={() => setShowDownloadModal(true)}
                    className="mt-3 sm:mt-0 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 flex items-center space-x-2"
                  >
                    <span>📥</span>
                    <span>Download CSV</span>
                  </button>
                )}
              </div>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">{selectedSectionData.name}</div>
                  <div className="text-sm text-gray-600">Section Name</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{selectedSectionData.grade || 'N/A'}</div>
                  <div className="text-sm text-gray-600">Grade Level</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{students.length}</div>
                  <div className="text-sm text-gray-600">Total Students</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Student List */}
        {selectedSection && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Student Details</h3>
              <p className="text-sm text-gray-600 mt-1">
                Complete list of students sorted by roll number
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Roll No
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Student Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Parent Mobile
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Enrollment Status
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {students
                    .sort((a, b) => {
                      // Sort by roll number if available, otherwise by name
                      const aRoll = a.roll_no || a.name;
                      const bRoll = b.roll_no || b.name;
                      return aRoll.localeCompare(bRoll, undefined, { numeric: true });
                    })
                    .map((student) => (
                    <tr key={student.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {student.roll_no || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {student.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {student.parent_mobile || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          student.enrolled 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {student.enrolled ? 'Enrolled' : 'Not Enrolled'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* No Students Message */}
        {selectedSection && !loading && students.length === 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="text-center py-12 px-6">
              <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-4xl">👨‍🎓</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">No Students Found</h3>
              <p className="text-gray-600 mb-6 max-w-md mx-auto">
                No students are enrolled in the selected section
              </p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="text-center py-12 px-6">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading students...</p>
            </div>
          </div>
        )}

        {/* No Section Selected */}
        {!selectedSection && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="text-center py-12 px-6">
              <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-4xl">📚</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Select a Section</h3>
              <p className="text-gray-600 mb-6 max-w-md mx-auto">
                Choose a section from the dropdown above to view the student list
              </p>
            </div>
          </div>
        )}

        {/* Column Selection Modal */}
        <Dialog open={showDownloadModal} onOpenChange={setShowDownloadModal}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Select Columns for Download</DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <p className="text-sm text-gray-600 mb-4">
                Choose which columns you want to include in the CSV file:
              </p>
              <div className="space-y-3">
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={selectedColumns.rollNo}
                    onChange={() => toggleColumn('rollNo')}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm font-medium text-gray-700">Roll Number</span>
                </label>
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={selectedColumns.name}
                    onChange={() => toggleColumn('name')}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm font-medium text-gray-700">Student Name</span>
                </label>
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={selectedColumns.parentMobile}
                    onChange={() => toggleColumn('parentMobile')}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm font-medium text-gray-700">Parent Mobile</span>
                </label>
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={selectedColumns.enrollmentStatus}
                    onChange={() => toggleColumn('enrollmentStatus')}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span className="text-sm font-medium text-gray-700">Enrollment Status</span>
                </label>
              </div>
              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-xs text-blue-700">
                  <strong>Preview:</strong> {Object.values(selectedColumns).filter(Boolean).length} column(s) will be exported
                </p>
              </div>
            </div>
            <DialogFooter className="flex flex-col sm:flex-row gap-2">
              <Button
                variant="outline"
                onClick={() => setShowDownloadModal(false)}
                className="w-full sm:w-auto"
              >
                Cancel
              </Button>
              <Button
                onClick={downloadCSV}
                disabled={Object.values(selectedColumns).every(col => !col)}
                className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700"
              >
                Download CSV
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
