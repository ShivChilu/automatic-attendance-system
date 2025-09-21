import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

export default function AdminMessages({ me }) {
  const [messages, setMessages] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showMessageModal, setShowMessageModal] = useState(false);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [createForm, setCreateForm] = useState({
    recipient_id: '',
    subject: '',
    content: ''
  });

  const loadMessages = async () => {
    try {
      setLoading(true);
      const res = await api.get("/messages/my");
      setMessages(res.data || []);
    } catch (e) {
      console.error("Failed to load messages:", e);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  };

  const loadTeachers = async () => {
    try {
      const res = await api.get("/users", { params: { role: "TEACHER" } });
      setTeachers(res.data.users || []);
    } catch (e) {
      console.error("Failed to load teachers:", e);
      setTeachers([]);
    }
  };

  const createMessage = async (e) => {
    e.preventDefault();
    if (!createForm.recipient_id || !createForm.subject.trim() || !createForm.content.trim()) {
      alert('Please fill in all fields');
      return;
    }

    try {
      await api.post("/messages", {
        recipient_id: createForm.recipient_id,
        subject: createForm.subject,
        content: createForm.content,
        is_announcement: false
      });
      alert('Message sent successfully!');
      setCreateForm({ recipient_id: '', subject: '', content: '' });
      setShowCreateModal(false);
      loadMessages();
    } catch (e) {
      alert('Failed to send message: ' + (e?.response?.data?.detail || 'Unknown error'));
    }
  };

  const openMessage = (message) => {
    setSelectedMessage(message);
    setShowMessageModal(true);
  };

  useEffect(() => {
    loadMessages();
    loadTeachers();
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
                  Messages
                </h1>
                <p className="mt-1 text-xs sm:text-sm text-gray-600">
                  Send personal messages to teachers
                </p>
              </div>
              <div className="mt-4 sm:mt-0">
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 flex items-center space-x-2"
                >
                  <span>📩</span>
                  <span>Send Message</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Messages List */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Sent Messages</h3>
            <p className="text-sm text-gray-600 mt-1">
              {messages.length} message{messages.length !== 1 ? 's' : ''} sent
            </p>
          </div>
          <div className="divide-y divide-gray-200">
            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading messages...</p>
              </div>
            ) : messages.length === 0 ? (
              <div className="p-8 text-center">
                <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-4xl">📩</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No Messages</h3>
                <p className="text-gray-600 mb-6 max-w-md mx-auto">
                  Send your first personal message to a teacher
                </p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition-colors duration-200 inline-flex items-center space-x-2"
                >
                  <span className="text-xl">📩</span>
                  <span>Send First Message</span>
                </button>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  onClick={() => openMessage(message)}
                  className="p-6 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <h4 className="text-sm font-semibold text-gray-900 truncate">
                          {message.subject}
                        </h4>
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          Personal
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                        {message.content}
                      </p>
                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span>To: {message.recipient_name}</span>
                        <span>•</span>
                        <span>Sent: {formatDate(message.created_at)}</span>
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

        {/* Create Message Modal */}
        <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2">
                <span>📩</span>
                <span>Send Personal Message</span>
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={createMessage}>
              <div className="py-4 space-y-4">
                <div>
                  <Label htmlFor="recipient" className="text-sm font-medium text-gray-700">
                    Send To *
                  </Label>
                  <select
                    id="recipient"
                    value={createForm.recipient_id}
                    onChange={(e) => setCreateForm({ ...createForm, recipient_id: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  >
                    <option value="">Select a teacher</option>
                    {teachers.map(teacher => (
                      <option key={teacher.id} value={teacher.id}>
                        {teacher.full_name} ({teacher.email})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label htmlFor="subject" className="text-sm font-medium text-gray-700">
                    Subject *
                  </Label>
                  <Input
                    id="subject"
                    value={createForm.subject}
                    onChange={(e) => setCreateForm({ ...createForm, subject: e.target.value })}
                    placeholder="Enter message subject"
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
                    placeholder="Enter your message..."
                    rows={6}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
                <div className="p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-700">
                    <strong>Note:</strong> This message will be sent directly to the selected teacher.
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
                  Send Message
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        {/* Message Detail Modal */}
        <Dialog open={showMessageModal} onOpenChange={setShowMessageModal}>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2">
                <span>📩</span>
                <span>{selectedMessage?.subject}</span>
              </DialogTitle>
            </DialogHeader>
            {selectedMessage && (
              <div className="py-4">
                <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex items-center justify-between text-sm text-blue-700 mb-2">
                    <span>To: {selectedMessage.recipient_name}</span>
                    <span>Sent: {formatDate(selectedMessage.created_at)}</span>
                  </div>
                  <div className="text-xs text-blue-600 font-medium">
                    Personal Message
                  </div>
                </div>
                <div className="prose max-w-none">
                  <p className="text-gray-900 whitespace-pre-wrap">
                    {selectedMessage.content}
                  </p>
                </div>
              </div>
            )}
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowMessageModal(false)}
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
