import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

export default function AdminAnnouncements({ me }) {
  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAnnouncementModal, setShowAnnouncementModal] = useState(false);
  const [selectedAnnouncement, setSelectedAnnouncement] = useState(null);
  const [createForm, setCreateForm] = useState({
    subject: '',
    content: ''
  });

  const loadAnnouncements = async () => {
    try {
      setLoading(true);
      const res = await api.get("/messages/announcements");
      setAnnouncements(res.data || []);
    } catch (e) {
      console.error("Failed to load announcements:", e);
      setAnnouncements([]);
    } finally {
      setLoading(false);
    }
  };

  const createAnnouncement = async (e) => {
    e.preventDefault();
    if (!createForm.subject.trim() || !createForm.content.trim()) {
      alert('Please fill in both subject and content');
      return;
    }

    try {
      await api.post("/messages", {
        subject: createForm.subject,
        content: createForm.content,
        is_announcement: true
      });
      alert('Announcement sent successfully to all teachers!');
      setCreateForm({ subject: '', content: '' });
      setShowCreateModal(false);
      loadAnnouncements();
    } catch (e) {
      alert('Failed to send announcement: ' + (e?.response?.data?.detail || 'Unknown error'));
    }
  };

  const openAnnouncement = (announcement) => {
    setSelectedAnnouncement(announcement);
    setShowAnnouncementModal(true);
  };

  useEffect(() => {
    loadAnnouncements();
  }, []);

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 sm:py-6">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900">
                  Announcements
                </h1>
                <p className="mt-1 text-xs sm:text-sm text-gray-600">
                  Send important messages to all teachers
                </p>
              </div>
              <div className="mt-4 sm:mt-0">
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 flex items-center space-x-2"
                >
                  <span>📢</span>
                  <span>Create Announcement</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Announcements List */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">School Announcements</h3>
            <p className="text-sm text-gray-600 mt-1">
              {announcements.length} announcement{announcements.length !== 1 ? 's' : ''} sent
            </p>
          </div>
          <div className="divide-y divide-gray-200">
            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading announcements...</p>
              </div>
            ) : announcements.length === 0 ? (
              <div className="p-8 text-center">
                <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-4xl">📢</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No Announcements</h3>
                <p className="text-gray-600 mb-6 max-w-md mx-auto">
                  Create your first announcement to communicate with all teachers
                </p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors duration-200 inline-flex items-center space-x-2"
                >
                  <span className="text-xl">📢</span>
                  <span>Create First Announcement</span>
                </button>
              </div>
            ) : (
              announcements.map((announcement) => (
                <div
                  key={announcement.id}
                  onClick={() => openAnnouncement(announcement)}
                  className="p-6 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <h4 className="text-sm font-semibold text-gray-900 truncate">
                          {announcement.subject}
                        </h4>
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                          Announcement
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                        {announcement.content}
                      </p>
                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span>Sent: {formatDate(announcement.created_at)}</span>
                        <span>•</span>
                        <span>To: All Teachers</span>
                      </div>
                    </div>
                    <div className="ml-4 flex-shrink-0">
                      <span className="text-gray-400">→</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Create Announcement Modal */}
        <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2">
                <span>📢</span>
                <span>Create New Announcement</span>
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={createAnnouncement}>
              <div className="py-4 space-y-4">
                <div>
                  <Label htmlFor="subject" className="text-sm font-medium text-gray-700">
                    Subject *
                  </Label>
                  <Input
                    id="subject"
                    value={createForm.subject}
                    onChange={(e) => setCreateForm({ ...createForm, subject: e.target.value })}
                    placeholder="Enter announcement subject"
                    className="mt-1"
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="content" className="text-sm font-medium text-gray-700">
                    Message Content *
                  </Label>
                  <textarea
                    id="content"
                    value={createForm.content}
                    onChange={(e) => setCreateForm({ ...createForm, content: e.target.value })}
                    placeholder="Enter your announcement message..."
                    rows={6}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
                <div className="p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-700">
                    <strong>Note:</strong> This announcement will be sent to all teachers in your school.
                  </p>
                </div>
              </div>
              <DialogFooter className="flex flex-col sm:flex-row gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreateModal(false)}
                  className="w-full sm:w-auto"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700"
                >
                  Send Announcement
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Announcement Detail Modal */}
        <Dialog open={showAnnouncementModal} onOpenChange={setShowAnnouncementModal}>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2">
                <span>📢</span>
                <span>{selectedAnnouncement?.subject}</span>
              </DialogTitle>
            </DialogHeader>
            {selectedAnnouncement && (
              <div className="py-4">
                <div className="mb-4 p-4 bg-orange-50 rounded-lg border border-orange-200">
                  <div className="flex items-center justify-between text-sm text-orange-700 mb-2">
                    <span>Sent: {formatDate(selectedAnnouncement.created_at)}</span>
                    <span>To: All Teachers</span>
                  </div>
                  <div className="text-xs text-orange-600 font-medium">
                    School Announcement
                  </div>
                </div>
                <div className="prose max-w-none">
                  <p className="text-gray-900 whitespace-pre-wrap">
                    {selectedAnnouncement.content}
                  </p>
                </div>
              </div>
            )}
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowAnnouncementModal(false)}
              >
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
